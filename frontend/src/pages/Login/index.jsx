import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { Form, Button, Toast, Typography } from '@douyinfe/semi-ui'
import { login } from '../../api/auth'
import { useAuth } from '../../context/AuthContext'

const { Title, Text } = Typography

export default function Login() {
  const { user, login: setAuth, loading } = useAuth()
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)

  if (!loading && user) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (values) => {
    setSubmitting(true)
    try {
      const data = await login(values)
      await setAuth(data.user)
      Toast.success('登录成功')
      navigate('/')
    } catch (err) {
      Toast.error(err?.message || '用户名或密码错误')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: 'var(--semi-color-bg-1)',
      }}
    >
      <div
        style={{
          width: 380,
          padding: 40,
          borderRadius: 12,
          background: 'var(--semi-color-bg-0)',
          boxShadow: 'var(--semi-shadow-elevated)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title heading={3} style={{ margin: 0 }}>AuraStack</Title>
          <Text type="tertiary">管理后台</Text>
        </div>

        <Form onSubmit={handleSubmit} autoComplete="off">
          <Form.Input
            field="username"
            label="用户名"
            placeholder="请输入用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
            size="large"
          />
          <Form.Input
            field="password"
            label="密码"
            type="password"
            placeholder="请输入密码"
            rules={[{ required: true, message: '请输入密码' }]}
            size="large"
          />
          <Button
            htmlType="submit"
            type="primary"
            size="large"
            block
            loading={submitting}
            style={{ marginTop: 8 }}
          >
            登录
          </Button>
        </Form>
      </div>
    </div>
  )
}
