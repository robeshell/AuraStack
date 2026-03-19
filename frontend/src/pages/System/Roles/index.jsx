import { useState, useEffect, useRef } from 'react'
import {
  Table, Button, Modal, Form, Toast,
  Popconfirm, Tag, Space, Typography, Tree,
} from '@douyinfe/semi-ui'
import { IconPlus } from '@douyinfe/semi-icons'
import { getRoles, createRole, updateRole, deleteRole } from '../../../api/roles'
import { getMenus } from '../../../api/menus'

// 将后端菜单树转成 Semi Tree 需要的格式
const convertToTreeData = (menus = []) =>
  menus.map((m) => ({
    label: m.name,
    value: m.id,
    key: String(m.id),
    children: m.children?.length ? convertToTreeData(m.children) : undefined,
  }))

export default function Roles() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editRecord, setEditRecord] = useState(null)
  const [menuTree, setMenuTree] = useState([])
  const [checkedMenus, setCheckedMenus] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const formApiRef = useRef()

  const fetchData = () => {
    setLoading(true)
    getRoles()
      .then((res) => setData(Array.isArray(res) ? res : []))
      .catch(() => Toast.error('加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchData()
    getMenus({ format: 'tree' }).then((res) =>
      setMenuTree(convertToTreeData(Array.isArray(res) ? res : []))
    )
  }, [])

  const openCreate = () => {
    setEditRecord(null)
    setCheckedMenus([])
    setModalVisible(true)
  }

  const openEdit = (record) => {
    setEditRecord(record)
    setCheckedMenus(Array.isArray(record.menu_ids) ? record.menu_ids : (record.menus?.map((m) => m.id) || []))
    setModalVisible(true)
  }

  const normalizeCheckedMenuIds = (vals) => {
    const raw = Array.isArray(vals) ? vals : (vals === undefined || vals === null ? [] : [vals])
    return raw
      .map((v) => (typeof v === 'object' && v !== null ? v.value : v))
      .map((v) => Number(v))
      .filter((v) => Number.isInteger(v))
  }

  const handleSubmit = () => {
    formApiRef.current.validate().then((values) => {
      setSubmitting(true)
      const payload = { ...values, menu_ids: checkedMenus }
      const fn = editRecord ? updateRole(editRecord.id, payload) : createRole(payload)
      fn.then(() => {
        Toast.success(editRecord ? '修改成功' : '创建成功')
        setModalVisible(false)
        fetchData()
      })
        .catch((err) => Toast.error(err?.error || '操作失败'))
        .finally(() => setSubmitting(false))
    })
  }

  const handleDelete = (id) => {
    deleteRole(id)
      .then(() => { Toast.success('删除成功'); fetchData() })
      .catch((err) => Toast.error(err?.error || '删除失败'))
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '角色名称', dataIndex: 'name' },
    {
      title: '角色编码',
      dataIndex: 'code',
      render: (v) => <Tag color="cyan">{v}</Tag>,
    },
    { title: '描述', dataIndex: 'description' },
    {
      title: '菜单权限',
      dataIndex: 'menus',
      render: (menus) => <Tag color="green">{menus?.length || 0} 个</Tag>,
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
            title="确认删除该角色？"
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
    ? { name: editRecord.name, code: editRecord.code, description: editRecord.description }
    : {}

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title heading={5} style={{ margin: 0 }}>
          角色管理
        </Typography.Title>
        <Button icon={<IconPlus />} theme="solid" type="primary" onClick={openCreate}>
          新建角色
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        pagination={false}
      />

      <Modal
        title={editRecord ? '编辑角色' : '新建角色'}
        visible={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        okButtonProps={{ loading: submitting }}
        width={560}
        afterClose={() => formApiRef.current?.reset()}
      >
        <Form getFormApi={api => formApiRef.current = api} initValues={initValues} labelPosition="left" labelWidth={90}>
          <Form.Input
            field="name"
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
          />
          <Form.Input
            field="code"
            label="角色编码"
            rules={[{ required: true, message: '请输入角色编码' }]}
            disabled={!!editRecord}
          />
          <Form.Input field="description" label="描述" />
        </Form>

        <div style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 8, fontSize: 14, fontWeight: 500, color: 'var(--semi-color-text-0)' }}>
            菜单权限
          </div>
          <div
            style={{
              border: '1px solid var(--semi-color-border)',
              borderRadius: 6,
              padding: '8px 12px',
              maxHeight: 280,
              overflow: 'auto',
            }}
          >
            {menuTree.length > 0 ? (
              <Tree
                treeData={menuTree}
                multiple
                expandAll
                autoMergeValue={false}
                value={checkedMenus}
                onChange={(vals) => setCheckedMenus(normalizeCheckedMenuIds(vals))}
                style={{ width: '100%' }}
              />
            ) : (
              <div style={{ color: 'var(--semi-color-text-2)', fontSize: 13 }}>暂无菜单数据</div>
            )}
          </div>
        </div>
      </Modal>
    </div>
  )
}
