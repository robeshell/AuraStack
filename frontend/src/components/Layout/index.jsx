import { useMemo, useState, useRef, useEffect } from 'react'
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
  IconMenu,
  IconBranch,
  IconCode,
  IconHistogram,
  IconDesktop,
  IconPieChartStroked,
  IconBox,
  IconActivity,
  IconSend,
  IconEdit2,
  IconLayers,
  IconKanban,
} from '@douyinfe/semi-icons'
import { useAuth } from '../../context/AuthContext'
import { changePassword } from '../../modules/admin/api/auth'
import './layout.css'

const { Text } = Typography
const MOBILE_BREAKPOINT = 992

const MENU_ICON_MAP = {
  dashboard:    <IconHome />,
  system:       <IconGridSquare />,
  system_users: <IconUser />,
  system_roles: <IconList />,
  system_menus: <IconArticle />,
  system_dicts: <IconList />,
  system_logs:  <IconArticle />,
}

const MENU_ICON_NAME_MAP = {
  IconHome:            <IconHome />,
  IconUser:            <IconUser />,
  IconList:            <IconList />,
  IconArticle:         <IconArticle />,
  IconGridSquare:      <IconGridSquare />,
  IconSetting:         <IconSetting />,
  IconApps:            <IconApps />,
  IconIdCard:          <IconIdCard />,
  IconFile:            <IconFile />,
  IconBranch:          <IconBranch />,
  IconCode:            <IconCode />,
  IconHistogram:       <IconHistogram />,
  // 组件示例中心分类图标
  IconDesktop:         <IconDesktop />,         // 管理系统
  IconPieChartStroked: <IconPieChartStroked />, // 数据可视化
  IconBox:             <IconBox />,             // 3D / 创意
  IconActivity:        <IconActivity />,        // 交互体验
  IconSend:            <IconSend />,            // AI 应用
  IconEdit2:           <IconEdit2 />,           // 编辑器 / 低代码
  IconLayers:          <IconLayers />,          // 工程 / 工具类
  IconKanban:          <IconKanban />,          // 看板页
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
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth <= MOBILE_BREAKPOINT : false
  )
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [pwdVisible, setPwdVisible] = useState(false)
  const [pwdSubmitting, setPwdSubmitting] = useState(false)
  const pwdFormApi = useRef()

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT)
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    if (!isMobile) {
      setMobileMenuOpen(false)
    }
  }, [isMobile])

  useEffect(() => {
    if (isMobile) {
      setMobileMenuOpen(false)
    }
  }, [isMobile, location.pathname])

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

  // code → parent code 映射，用于向上追溯祖先
  const codeParentMap = useMemo(() => {
    const idToCode = {}
    flatMenus.forEach((m) => { idToCode[m.id] = m.code })
    const map = {}
    flatMenus.forEach((m) => {
      if (m.parent_id && idToCode[m.parent_id]) {
        map[m.code] = idToCode[m.parent_id]
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

  // 当前选中菜单的所有祖先 code（用于自动展开侧边栏分组）
  const ancestorKeys = useMemo(() => {
    if (!currentKey) return []
    const keys = []
    let key = currentKey
    while (codeParentMap[key]) {
      key = codeParentMap[key]
      keys.push(key)
    }
    return keys
  }, [currentKey, codeParentMap])

  // 受控的展开 key 列表：路由切换时合并新祖先，不折叠已手动展开的分组
  const [openKeys, setOpenKeys] = useState([])
  useEffect(() => {
    if (ancestorKeys.length === 0) return
    setOpenKeys((prev) => {
      const merged = new Set([...prev, ...ancestorKeys])
      return Array.from(merged)
    })
  }, [ancestorKeys])

  const navItems = buildNavItems(menus)

  const handleSelect = ({ itemKey }) => {
    const path = menuPathMap[itemKey]
    if (path) {
      navigate(path)
      if (isMobile) {
        setMobileMenuOpen(false)
      }
    }
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
      {isMobile && mobileMenuOpen ? (
        <div className="as-sider-mask" onClick={() => setMobileMenuOpen(false)} aria-hidden="true" />
      ) : null}
      {/* 深色侧边栏 */}
      <div className={`as-sider ${isMobile ? 'as-sider-mobile' : ''} ${mobileMenuOpen ? 'as-sider-open' : ''}`}>
        <Nav
          style={{ height: '100%', width: '100%', background: 'transparent' }}
          isCollapsed={isMobile ? false : collapsed}
          onCollapseChange={(next) => {
            if (!isMobile) {
              setCollapsed(next)
            }
          }}
          limitIndent={false}
          items={navItems}
          selectedKeys={currentKey ? [currentKey] : []}
          openKeys={openKeys}
          onOpenChange={({ openKeys: next }) => setOpenKeys(next)}
          onSelect={handleSelect}
          header={{
            logo: (
              <img
                src="/logo.svg"
                style={{ width: 44, height: 44, flexShrink: 0 }}
                alt="logo"
              />
            ),
            text: (
              <span className="as-brand-text">AuraStack</span>
            ),
          }}
          footer={isMobile ? undefined : { collapseButton: true }}
        />
      </div>

      {/* 右侧主区域 */}
      <div className="as-main">
        {/* Header */}
        <header className="as-header">
          <div className="as-header-left">
            {isMobile ? (
              <button
                type="button"
                className="as-menu-trigger"
                onClick={() => setMobileMenuOpen((open) => !open)}
                aria-label="打开菜单"
              >
                <IconMenu />
              </button>
            ) : null}
          </div>
          <div className="as-header-right">
            <Dropdown render={dropdownMenu} trigger="click" position="bottomRight">
              <div className="as-user-info">
                <Avatar size="small" color="blue" style={{ background: 'linear-gradient(135deg,#2563eb,#06b6d4)' }}>
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
