import { useState, useEffect, useRef } from 'react'
import {
  Table, Button, Modal, Form, Toast,
  Popconfirm, Tag, Space, Typography,
} from '@douyinfe/semi-ui'
import { IconPlus } from '@douyinfe/semi-icons'
import { getMenus, createMenu, updateMenu, deleteMenu } from '../../../api/menus'

const MENU_TYPE_OPTIONS = [
  { label: '目录', value: 'directory' },
  { label: '菜单', value: 'menu' },
  { label: '按钮', value: 'button' },
]

const MENU_TYPE_COLOR = { directory: 'violet', menu: 'blue', button: 'orange' }

// 递归压平树，用于父菜单选择器
const flattenTree = (menus, depth = 0) =>
  menus.flatMap((m) => [
    { label: '\u00a0\u00a0'.repeat(depth) + m.name, value: m.id },
    ...(m.children?.length ? flattenTree(m.children, depth + 1) : []),
  ])

export default function Menus() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editRecord, setEditRecord] = useState(null)
  const [parentOptions, setParentOptions] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const formRef = useRef()

  const fetchData = () => {
    setLoading(true)
    getMenus({ format: 'tree' })
      .then((res) => {
        const list = Array.isArray(res) ? res : []
        setData(list)
        setParentOptions([
          { label: '无（顶级菜单）', value: null },
          ...flattenTree(list),
        ])
      })
      .catch(() => Toast.error('加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  const openCreate = (parentId = null) => {
    setEditRecord(parentId !== null ? { parent_id: parentId } : null)
    setModalVisible(true)
  }

  const openEdit = (record) => {
    setEditRecord(record)
    setModalVisible(true)
  }

  const handleSubmit = () => {
    formRef.current.validate().then((values) => {
      setSubmitting(true)
      const fn = editRecord?.id
        ? updateMenu(editRecord.id, values)
        : createMenu(values)
      fn.then(() => {
        Toast.success(editRecord?.id ? '修改成功' : '创建成功')
        setModalVisible(false)
        fetchData()
      })
        .catch((err) => Toast.error(err?.error || '操作失败'))
        .finally(() => setSubmitting(false))
    })
  }

  const handleDelete = (id) => {
    deleteMenu(id)
      .then(() => { Toast.success('删除成功'); fetchData() })
      .catch((err) => Toast.error(err?.error || '删除失败'))
  }

  const columns = [
    {
      title: '菜单名称',
      dataIndex: 'name',
      width: 180,
    },
    {
      title: '编码',
      dataIndex: 'code',
      render: (v) => <Tag>{v}</Tag>,
    },
    {
      title: '类型',
      dataIndex: 'menu_type',
      width: 70,
      render: (v) => (
        <Tag color={MENU_TYPE_COLOR[v] || 'grey'}>
          {MENU_TYPE_OPTIONS.find((t) => t.value === v)?.label || v}
        </Tag>
      ),
    },
    { title: '路径', dataIndex: 'path' },
    { title: '图标', dataIndex: 'icon', width: 90 },
    { title: '排序', dataIndex: 'sort_order', width: 60 },
    {
      title: '显示',
      dataIndex: 'is_visible',
      width: 60,
      render: (v) => <Tag color={v ? 'green' : 'grey'}>{v ? '是' : '否'}</Tag>,
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 60,
      render: (v) => <Tag color={v ? 'green' : 'grey'}>{v ? '是' : '否'}</Tag>,
    },
    {
      title: '操作',
      width: 220,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openCreate(record.id)}>
            添加子项
          </Button>
          <Button size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该菜单？"
            content="有子菜单时无法删除"
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

  const initValues = editRecord || { menu_type: 'menu', sort_order: 0, is_visible: true, is_active: true }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title heading={5} style={{ margin: 0 }}>
          菜单管理
        </Typography.Title>
        <Button icon={<IconPlus />} theme="solid" type="primary" onClick={() => openCreate()}>
          新建菜单
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        pagination={false}
        expandAllRows
        childrenRecordName="children"
      />

      <Modal
        title={editRecord?.id ? '编辑菜单' : '新建菜单'}
        visible={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        okButtonProps={{ loading: submitting }}
        width={560}
        afterClose={() => formRef.current?.setValues({})}
      >
        <Form
          ref={formRef}
          initValues={initValues}
          labelPosition="left"
          labelWidth={80}
        >
          <Form.Input
            field="name"
            label="名称"
            rules={[{ required: true, message: '请输入菜单名称' }]}
          />
          <Form.Input
            field="code"
            label="编码"
            rules={[{ required: true, message: '请输入菜单编码' }]}
          />
          <Form.Select
            field="menu_type"
            label="类型"
            optionList={MENU_TYPE_OPTIONS}
            style={{ width: '100%' }}
          />
          <Form.Select
            field="parent_id"
            label="父菜单"
            optionList={parentOptions}
            style={{ width: '100%' }}
            showClear
          />
          <Form.Input field="path" label="路径" placeholder="/example" />
          <Form.Input field="icon" label="图标" placeholder="图标名称" />
          <Form.InputNumber field="sort_order" label="排序" min={0} />
          <Form.Switch field="is_visible" label="显示" />
          <Form.Switch field="is_active" label="启用" />
        </Form>
      </Modal>
    </div>
  )
}
