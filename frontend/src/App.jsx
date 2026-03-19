import { useMemo } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Empty, Typography } from '@douyinfe/semi-ui'
import { AuthProvider } from './context/AuthContext'
import { useAuth } from './context/AuthContext'
import PrivateRoute from './components/Layout/PrivateRoute'
import Layout from './components/Layout'
import Login from './pages/Login'

const PAGE_MODULES = import.meta.glob('./pages/**/index.jsx', { eager: true })

function resolvePageComponent(componentName) {
  if (!componentName || typeof componentName !== 'string') {
    return null
  }
  const componentPathSuffix = `/${componentName}/index.jsx`
  const matchedEntry = Object.entries(PAGE_MODULES).find(([modulePath]) =>
    modulePath.endsWith(componentPathSuffix)
  )
  return matchedEntry?.[1]?.default || null
}

function collectRouteMenus(menus = []) {
  const result = []
  const walk = (nodes = []) => {
    nodes.forEach((menu) => {
      if (!menu?.is_active || !menu?.is_visible) {
        return
      }
      if (menu.menu_type === 'menu' && menu.path?.startsWith('/')) {
        result.push(menu)
      }
      if (Array.isArray(menu.children) && menu.children.length > 0) {
        walk(menu.children)
      }
    })
  }
  walk(menus)
  return result
}

function normalizeRoutePath(pathname = '') {
  return pathname.replace(/^\/+/, '')
}

function NoPermissionPage() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 360 }}>
      <Empty
        title="暂无可访问页面"
        description="当前账号没有分配可见菜单，请联系管理员分配权限。"
      />
    </div>
  )
}

function RouteNotConfigured({ path, component }) {
  return (
    <div style={{ padding: 24 }}>
      <Typography.Title heading={5}>页面未配置</Typography.Title>
      <Typography.Paragraph>
        菜单路径 <Typography.Text code>{path}</Typography.Text> 对应的组件
        <Typography.Text code style={{ marginLeft: 6 }}>{component || '(空)'}</Typography.Text>
        暂未在前端注册。
      </Typography.Paragraph>
    </div>
  )
}

function AppRoutes() {
  const { menus } = useAuth()

  const routeMenus = useMemo(() => {
    const all = collectRouteMenus(menus)
    const dedup = new Map()
    all.forEach((menu) => {
      if (!dedup.has(menu.path)) {
        dedup.set(menu.path, menu)
      }
    })
    return Array.from(dedup.values())
  }, [menus])

  const defaultPath = useMemo(() => {
    if (routeMenus.length === 0) {
      return null
    }
    const dashboardMenu = routeMenus.find((menu) => menu.path === '/dashboard')
    return (dashboardMenu || routeMenus[0]).path
  }, [routeMenus])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={defaultPath ? <Navigate to={defaultPath} replace /> : <NoPermissionPage />} />
        {routeMenus.map((menu) => {
          const Component = resolvePageComponent(menu.component)
          return (
            <Route
              key={menu.path}
              path={normalizeRoutePath(menu.path)}
              element={Component ? <Component /> : <RouteNotConfigured path={menu.path} component={menu.component} />}
            />
          )
        })}
        <Route path="*" element={<Navigate to={defaultPath || '/'} replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
