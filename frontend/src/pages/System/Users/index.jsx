import { useState, useEffect, useRef } from 'react'
import {
  Table, Button, Modal, Form, Toast,
  Popconfirm, Tag, Input, Space, Typography,
} from '@douyinfe/semi-ui'
import { IconPlus, IconSearch } from '@douyinfe/semi-icons'
import { getUsers, createUser, updateUser, deleteUser } from '../../../api/users'
import { getRoles } from '../../../api/roles'

export default function Users() {
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalVisible, setModalVisible] = useState(false)
  const [editRecord, setEditRecord] = useState(null)
  const [roles, setRoles] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const formApiRef = useRef()

  const fetchData = (p = 1, s = search) => {
    setLoading(true)
    getUsers({ page: p, per_page: 20, search: s })
      .then((res) => {
        setData(res.items || [])
        setTotal(res.total || 0)
      })
      .catch(() => Toast.error('加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchData()
    getRoles().then((res) => setRoles(Array.isArray(res) ? res : []))
  }, [])

  const openCreate = () => {
    setEditRecord(null)
    setModalVisible(true)
  }

  const openEdit = (record) => {
    setEditRecord(record)
    setModalVisible(true)
  }

  const handleSubmit = () => {
    formApiRef.current.validate().then((values) => {
      setSubmitting(true)
      const fn = editRecord
        ? updateUser(editRecord.id, values)
        : createUser(values)
      fn.then(() => {
        Toast.success(editRecord ? '修改成功' : '创建成功')
        setModalVisible(false)
        fetchData(page)
      })
        .catch((err) => Toast.error(err?.error || '操作失败'))
        .finally(() => setSubmitting(false))
    })
  }

  const handleDelete = (id) => {
    deleteUser(id)
      .then(() => { Toast.success('删除成功'); fetchData(page) })
      .catch((err) => Toast.error(err?.error || '删除失败'))
  }

  const handleSearch = () => {
    setPage(1)
    fetchData(1, search)
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '用户名', dataIndex: 'username' },
    {
      title: '角色',
      dataIndex: 'roles',
      render: (r) =>
        r?.map((role) => (
          <Tag key={role.id} color="blue" style={{ marginRight: 4 }}>
            {role.name}
          </Tag>
        )),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      render: (v) => v?.slice(0, 19).replace('T', ' '),
    },
    {
      title: '操作',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该用户？"
            content="删除后不可恢复"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button size="small" type="danger">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const initValues = editRecord
    ? { role_ids: editRecord.roles?.map((r) => r.id) }
    : {}

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title heading={5} style={{ margin: 0 }}>
          用户管理
        </Typography.Title>
        <Space>
          <Input
            prefix={<IconSearch />}
            placeholder="搜索用户名"
            value={search}
            onChange={(v) => setSearch(v)}
            onEnterPress={handleSearch}
            style={{ width: 200 }}
          />
          <Button onClick={handleSearch}>搜索</Button>
          <Button icon={<IconPlus />} theme="solid" type="primary" onClick={openCreate}>
            新建用户
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        pagination={{
          total,
          currentPage: page,
          pageSize: 20,
          onPageChange: (p) => { setPage(p); fetchData(p, search) },
        }}
      />

      <Modal
        title={editRecord ? '编辑用户' : '新建用户'}
        visible={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        okButtonProps={{ loading: submitting }}
        afterClose={() => formApiRef.current?.reset()}
        width={480}
      >
        <Form getFormApi={api => formApiRef.current = api} initValues={initValues} labelPosition="left" labelWidth={100}>
          {!editRecord && (
            <Form.Input
              field="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            />
          )}
          <Form.Input
            field="password"
            label={editRecord ? '新密码' : '密码'}
            type="password"
            placeholder={editRecord ? '留空则不修改' : '请输入密码'}
            rules={editRecord ? [] : [{ required: true, message: '请输入密码' }]}
          />
          <Form.Select
            field="role_ids"
            label="角色"
            multiple
            optionList={roles.map((r) => ({ label: r.name, value: r.id }))}
            style={{ width: '100%' }}
            placeholder="请选择角色"
          />
        </Form>
      </Modal>
    </div>
  )
}
