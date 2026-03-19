import { Typography } from '@douyinfe/semi-ui'
import { useAuth } from '../../context/AuthContext'

const { Title, Text } = Typography

export default function Dashboard() {
  const { user } = useAuth()

  return (
    <div>
      <Title heading={4}>欢迎回来，{user?.username} 👋</Title>
      <Text type="tertiary">这是 AuraStack 管理后台首页</Text>
    </div>
  )
}
