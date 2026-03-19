import { useMemo, useState, useRef } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Nav, Avatar, Dropdown, Typography, Modal, Form, Toast } from '@douyinfe/semi-ui'
import {
  IconHome,
  IconUser,
  IconList,
  IconArticle,
  IconChevronDown,
  IconGridSquare,
  IconSetting,
  IconApps,
  IconIdCard,
  IconFile,
} from '@douyinfe/semi-icons'
import { useAuth } from '../../context/AuthContext'
import { changePassword } from '../../api/auth'
import './layout.css'

const { Text } = Typography

const MENU_ICON_MAP = {
  dashboard:    <IconHome />,
  system:       <IconGridSquare />,
  system_users: <IconUser />,
  system_roles: <IconList />,
  system_menus: <IconArticle />,
  system_logs:  <IconArticle />,
}

const MENU_ICON_NAME_MAP = {
  IconHome: <IconHome />,
  IconUser: <IconUser />,
  IconList: <IconList />,
  IconArticle: <IconArticle />,
  IconGridSquare: <IconGridSquare />,
  IconSetting: <IconSetting />,
  IconApps: <IconApps />,
  IconIdCard: <IconIdCard />,
  IconFile: <IconFile />,
}

function buildNavItems(menus) {
  return menus
    .filter((m) => m.is_active && m.is_visible && m.menu_type !== 'button')
    .map((m) => ({
      itemKey: m.code,
      text: m.name,
      icon: MENU_ICON_NAME_MAP[m.icon] || MENU_ICON_MAP[m.code] || <IconList />,
      ...(m.children?.length ? { items: buildNavItems(m.children) } : {}),
    }))
}

function flattenMenus(menus = []) {
  const result = []
  const walk = (nodes = []) => {
    nodes.forEach((node) => {
      if (node?.is_active && node?.is_visible && node.menu_type !== 'button') {
        result.push(node)
      }
      if (Array.isArray(node?.children) && node.children.length > 0) {
        walk(node.children)
      }
    })
  }
  walk(menus)
  return result
}

export default function Layout() {
  const { user, menus, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [pwdVisible, setPwdVisible] = useState(false)
  const [pwdSubmitting, setPwdSubmitting] = useState(false)
  const pwdFormApi = useRef()

  const flatMenus = useMemo(() => flattenMenus(menus), [menus])
  const menuPathMap = useMemo(() => {
    const map = {}
    flatMenus.forEach((menu) => {
      if (menu.path) {
        map[menu.code] = menu.path
      }
    })
    return map
  }, [flatMenus])

  const currentKey = useMemo(() => {
    const matched = flatMenus
      .filter((menu) => typeof menu.path === 'string' && menu.path.length > 0)
      .sort((a, b) => b.path.length - a.path.length)
      .find((menu) => location.pathname === menu.path || location.pathname.startsWith(`${menu.path}/`))
    return matched?.code
  }, [flatMenus, location.pathname])

  const navItems = buildNavItems(menus)

  const handleSelect = ({ itemKey }) => {
    const path = menuPathMap[itemKey]
    if (path) navigate(path)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const handleChangePwd = () => {
    pwdFormApi.current.validate().then((values) => {
      if (values.new_password !== values.confirm_password) {
        Toast.error('两次输入的新密码不一致')
        return
      }
      setPwdSubmitting(true)
      changePassword({ old_password: values.old_password, new_password: values.new_password })
        .then(async () => {
          Toast.success('密码修改成功，请重新登录')
          setPwdVisible(false)
          await logout()
          navigate('/login', { replace: true })
        })
        .catch((err) => Toast.error(err?.error || '修改失败'))
        .finally(() => setPwdSubmitting(false))
    })
  }

  const dropdownMenu = (
    <Dropdown.Menu>
      <Dropdown.Item onClick={() => setPwdVisible(true)}>修改密码</Dropdown.Item>
      <Dropdown.Divider />
      <Dropdown.Item type="danger" onClick={handleLogout}>
        退出登录
      </Dropdown.Item>
    </Dropdown.Menu>
  )

  return (
    <div className="as-layout">
      {/* 深色侧边栏 */}
      <div className="as-sider">
        <Nav
          style={{ height: '100%', background: 'transparent' }}
          isCollapsed={collapsed}
          onCollapseChange={setCollapsed}
          items={navItems}
          selectedKeys={currentKey ? [currentKey] : []}
          onSelect={handleSelect}
          header={{
            logo: (
              <img
                src="/logo.svg"
                style={{ width: 28, height: 28, flexShrink: 0 }}
                alt="logo"
              />
            ),
            text: (
              <span className="as-brand-text">AuraStack</span>
            ),
          }}
          footer={{ collapseButton: true }}
        />
      </div>

      {/* 右侧主区域 */}
      <div className="as-main">
        {/* Header */}
        <header className="as-header">
          <div className="as-header-right">
            <Dropdown render={dropdownMenu} trigger="click" position="bottomRight">
              <div className="as-user-info">
                <Avatar size="small" color="indigo" style={{ background: 'linear-gradient(135deg,#6366f1,#a855f7)' }}>
                  {user?.username?.[0]?.toUpperCase()}
                </Avatar>
                <Text className="as-username">{user?.username}</Text>
                <IconChevronDown size="small" style={{ color: 'var(--semi-color-text-2)' }} />
              </div>
            </Dropdown>
          </div>
        </header>

        {/* 内容区 */}
        <main className="as-content">
          <Outlet />
        </main>
      </div>
      <Modal
        title="修改密码"
        visible={pwdVisible}
        onOk={handleChangePwd}
        onCancel={() => setPwdVisible(false)}
        okButtonProps={{ loading: pwdSubmitting }}
        afterClose={() => pwdFormApi.current?.reset()}
        width={420}
      >
        <Form getFormApi={api => pwdFormApi.current = api} labelPosition="left" labelWidth={100}>
          <Form.Input
            field="old_password"
            label="当前密码"
            type="password"
            placeholder="请输入当前登录密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          />
          <div
            style={{
              margin: '-8px 0 8px 100px',
              color: 'var(--semi-color-text-2)',
              fontSize: 12,
              lineHeight: '18px',
            }}
          >
            旧密码必须填写当前登录密码
          </div>
          <Form.Input
            field="new_password"
            label="新密码"
            type="password"
            rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '至少6位' }]}
          />
          <Form.Input
            field="confirm_password"
            label="确认新密码"
            type="password"
            rules={[{ required: true, message: '请再次输入新密码' }]}
          />
        </Form>
      </Modal>
    </div>
  )
}
