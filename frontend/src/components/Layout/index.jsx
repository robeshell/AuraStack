import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Nav, Avatar, Dropdown, Typography, Badge } from '@douyinfe/semi-ui'
import {
  IconHome,
  IconUser,
  IconSetting,
  IconList,
  IconArticle,
  IconChevronDown,
  IconGridSquare,
} from '@douyinfe/semi-icons'
import { useAuth } from '../../context/AuthContext'
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

const MENU_PATH_MAP = {
  dashboard:    '/dashboard',
  system_users: '/system/users',
  system_roles: '/system/roles',
  system_menus: '/system/menus',
  system_logs:  '/system/logs',
}

function buildNavItems(menus) {
  return menus
    .filter((m) => m.is_active && m.is_visible)
    .map((m) => ({
      itemKey: m.code,
      text: m.name,
      icon: MENU_ICON_MAP[m.code] || <IconList />,
      ...(m.children?.length ? { items: buildNavItems(m.children) } : {}),
    }))
}

export default function Layout() {
  const { user, menus, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const currentKey = Object.entries(MENU_PATH_MAP).find(
    ([, path]) => location.pathname === path
  )?.[0]

  const navItems = buildNavItems(menus)

  const handleSelect = ({ itemKey }) => {
    const path = MENU_PATH_MAP[itemKey]
    if (path) navigate(path)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const dropdownMenu = (
    <Dropdown.Menu>
      <Dropdown.Item onClick={() => {}}>个人设置</Dropdown.Item>
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
    </div>
  )
}
