import { useState, useEffect, useRef } from 'react'
import {
  Table, Button, Modal, Form, Toast,
  Popconfirm, Input, Space, Typography, Tag,
} from '@douyinfe/semi-ui'
import { IconPlus, IconSearch, IconRefresh } from '@douyinfe/semi-icons'
import {
  getDictTypes,
  createDictType,
  updateDictType,
  deleteDictType,
  getDictItems,
  createDictItem,
  updateDictItem,
  deleteDictItem,
} from '../../../api/dicts'

const formatDateTime = (value) => (value ? value.slice(0, 19).replace('T', ' ') : '-')

export default function Dicts() {
  const [typeData, setTypeData] = useState([])
  const [typeTotal, setTypeTotal] = useState(0)
  const [typeLoading, setTypeLoading] = useState(false)
  const [typePage, setTypePage] = useState(1)
  const [typeSearch, setTypeSearch] = useState('')
  const [selectedType, setSelectedType] = useState(null)

  const [itemData, setItemData] = useState([])
  const [itemLoading, setItemLoading] = useState(false)
  const [itemSearch, setItemSearch] = useState('')

  const [typeModalVisible, setTypeModalVisible] = useState(false)
  const [typeEditRecord, setTypeEditRecord] = useState(null)
  const [typeSubmitting, setTypeSubmitting] = useState(false)
  const typeFormApiRef = useRef()

  const [itemModalVisible, setItemModalVisible] = useState(false)
  const [itemEditRecord, setItemEditRecord] = useState(null)
  const [itemSubmitting, setItemSubmitting] = useState(false)
  const itemFormApiRef = useRef()

  const fetchTypes = (page = typePage, search = typeSearch) => {
    setTypeLoading(true)
    getDictTypes({ page, per_page: 20, search })
      .then((res) => {
        const list = Array.isArray(res.items) ? res.items : []
        setTypeData(list)
        setTypeTotal(res.total || 0)

        if (!selectedType?.id) {
          setSelectedType(list[0] || null)
          return
        }
        const matched = list.find((item) => item.id === selectedType.id)
        setSelectedType(matched || list[0] || null)
      })
      .catch(() => Toast.error('加载字典类型失败'))
      .finally(() => setTypeLoading(false))
  }

  const fetchItems = (dictTypeId = selectedType?.id, search = itemSearch) => {
    if (!dictTypeId) {
      setItemData([])
      return
    }
    setItemLoading(true)
    getDictItems(dictTypeId, { search })
      .then((res) => {
        setItemData(Array.isArray(res.items) ? res.items : [])
      })
      .catch(() => Toast.error('加载字典项失败'))
      .finally(() => setItemLoading(false))
  }

  useEffect(() => {
    fetchTypes()
  }, [])

  useEffect(() => {
    if (selectedType?.id) {
      fetchItems(selectedType.id, '')
    } else {
      setItemData([])
    }
    setItemSearch('')
  }, [selectedType?.id])

  const handleTypeSearch = () => {
    setTypePage(1)
    fetchTypes(1, typeSearch)
  }

  const handleTypeReset = () => {
    setTypeSearch('')
    setTypePage(1)
    fetchTypes(1, '')
  }

  const handleItemSearch = () => {
    fetchItems(selectedType?.id, itemSearch)
  }

  const handleItemReset = () => {
    setItemSearch('')
    fetchItems(selectedType?.id, '')
  }

  const openCreateType = () => {
    setTypeEditRecord(null)
    setTypeModalVisible(true)
  }

  const openEditType = (record) => {
    setTypeEditRecord(record)
    setTypeModalVisible(true)
  }

  const openCreateItem = () => {
    if (!selectedType?.id) {
      Toast.warning('请先选择一个字典类型')
      return
    }
    setItemEditRecord(null)
    setItemModalVisible(true)
  }

  const openEditItem = (record) => {
    setItemEditRecord(record)
    setItemModalVisible(true)
  }

  const handleSubmitType = () => {
    typeFormApiRef.current.validate().then((values) => {
      setTypeSubmitting(true)
      const req = typeEditRecord?.id
        ? updateDictType(typeEditRecord.id, values)
        : createDictType(values)
      req.then(() => {
        Toast.success(typeEditRecord?.id ? '字典类型更新成功' : '字典类型创建成功')
        setTypeModalVisible(false)
        fetchTypes(typePage, typeSearch)
      })
        .catch((err) => Toast.error(err?.error || '保存失败'))
        .finally(() => setTypeSubmitting(false))
    })
  }

  const handleDeleteType = (id) => {
    deleteDictType(id)
      .then(() => {
        Toast.success('删除成功')
        if (selectedType?.id === id) {
          setSelectedType(null)
        }
        fetchTypes(typePage, typeSearch)
      })
      .catch((err) => Toast.error(err?.error || '删除失败'))
  }

  const handleSubmitItem = () => {
    itemFormApiRef.current.validate().then((values) => {
      setItemSubmitting(true)
      const req = itemEditRecord?.id
        ? updateDictItem(itemEditRecord.id, values)
        : createDictItem(selectedType.id, values)

      req.then(() => {
        Toast.success(itemEditRecord?.id ? '字典项更新成功' : '字典项创建成功')
        setItemModalVisible(false)
        fetchItems(selectedType.id, itemSearch)
      })
        .catch((err) => Toast.error(err?.error || '保存失败'))
        .finally(() => setItemSubmitting(false))
    })
  }

  const handleDeleteItem = (id) => {
    deleteDictItem(id)
      .then(() => {
        Toast.success('删除成功')
        fetchItems(selectedType?.id, itemSearch)
      })
      .catch((err) => Toast.error(err?.error || '删除失败'))
  }

  const typeColumns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '名称', dataIndex: 'name', width: 140 },
    {
      title: '编码',
      dataIndex: 'code',
      width: 170,
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 80,
      render: (value) => <Tag color={value ? 'green' : 'grey'}>{value ? '启用' : '停用'}</Tag>,
    },
    { title: '排序', dataIndex: 'sort_order', width: 70 },
    { title: '字典项数', dataIndex: 'item_count', width: 90 },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 165,
      render: formatDateTime,
    },
    {
      title: '操作',
      width: 230,
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            type={selectedType?.id === record.id ? 'primary' : 'tertiary'}
            theme={selectedType?.id === record.id ? 'solid' : 'borderless'}
            onClick={() => setSelectedType(record)}
          >
            字典项
          </Button>
          <Button size="small" onClick={() => openEditType(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该字典类型？"
            content="删除前需要先清空字典项"
            onConfirm={() => handleDeleteType(record.id)}
          >
            <Button size="small" type="danger">删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const itemColumns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '标签', dataIndex: 'label', width: 120 },
    {
      title: '值',
      dataIndex: 'value',
      width: 160,
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: '颜色',
      dataIndex: 'color',
      width: 90,
      render: (value) => (value ? <Tag style={{ backgroundColor: value, color: '#fff' }}>{value}</Tag> : '-'),
    },
    {
      title: '默认',
      dataIndex: 'is_default',
      width: 70,
      render: (value) => <Tag color={value ? 'blue' : 'grey'}>{value ? '是' : '否'}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 80,
      render: (value) => <Tag color={value ? 'green' : 'grey'}>{value ? '启用' : '停用'}</Tag>,
    },
    { title: '排序', dataIndex: 'sort_order', width: 70 },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 165,
      render: formatDateTime,
    },
    {
      title: '操作',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openEditItem(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该字典项？"
            onConfirm={() => handleDeleteItem(record.id)}
          >
            <Button size="small" type="danger">删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const typeInitValues = typeEditRecord || { sort_order: 0, is_active: true }
  const itemInitValues = itemEditRecord || {
    sort_order: 0,
    is_active: true,
    is_default: false,
  }

  return (
    <div>
      <Typography.Title heading={5} style={{ marginBottom: 16 }}>
        数据字典
      </Typography.Title>

      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        <div style={{ padding: 16, border: '1px solid var(--semi-color-border)', borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <Typography.Text strong>字典类型</Typography.Text>
            <Space>
              <Input
                prefix={<IconSearch />}
                placeholder="搜索名称/编码"
                value={typeSearch}
                onChange={(value) => setTypeSearch(value)}
                onEnterPress={handleTypeSearch}
                style={{ width: 200 }}
              />
              <Button icon={<IconRefresh />} onClick={handleTypeReset}>重置</Button>
              <Button icon={<IconPlus />} type="primary" theme="solid" onClick={openCreateType}>
                新建
              </Button>
            </Space>
          </div>

          <Table
            columns={typeColumns}
            dataSource={typeData}
            rowKey="id"
            loading={typeLoading}
            pagination={{
              total: typeTotal,
              currentPage: typePage,
              pageSize: 20,
              onPageChange: (page) => {
                setTypePage(page)
                fetchTypes(page, typeSearch)
              },
            }}
          />
        </div>

        <div style={{ padding: 16, border: '1px solid var(--semi-color-border)', borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <div>
              <Typography.Text strong>字典项</Typography.Text>
              <Typography.Text type="tertiary" style={{ marginLeft: 8 }}>
                {selectedType ? `当前类型：${selectedType.name} (${selectedType.code})` : '请先在左侧选择字典类型'}
              </Typography.Text>
            </div>
            <Space>
              <Input
                prefix={<IconSearch />}
                placeholder="搜索标签/值"
                value={itemSearch}
                onChange={(value) => setItemSearch(value)}
                onEnterPress={handleItemSearch}
                style={{ width: 180 }}
                disabled={!selectedType}
              />
              <Button icon={<IconRefresh />} onClick={handleItemReset} disabled={!selectedType}>重置</Button>
              <Button icon={<IconPlus />} type="primary" theme="solid" onClick={openCreateItem} disabled={!selectedType}>
                新建
              </Button>
            </Space>
          </div>

          <Table
            columns={itemColumns}
            dataSource={itemData}
            rowKey="id"
            loading={itemLoading}
            pagination={false}
            empty={
              selectedType
                ? <Typography.Text type="tertiary">该字典类型暂无字典项</Typography.Text>
                : <Typography.Text type="tertiary">请先选择字典类型</Typography.Text>
            }
          />
        </div>
      </div>

      <Modal
        title={typeEditRecord?.id ? '编辑字典类型' : '新建字典类型'}
        visible={typeModalVisible}
        onOk={handleSubmitType}
        onCancel={() => setTypeModalVisible(false)}
        okButtonProps={{ loading: typeSubmitting }}
        width={520}
        afterClose={() => typeFormApiRef.current?.reset()}
      >
        <Form
          getFormApi={api => typeFormApiRef.current = api}
          initValues={typeInitValues}
          labelPosition="left"
          labelWidth={95}
        >
          <Form.Input
            field="name"
            label="字典名称"
            rules={[{ required: true, message: '请输入字典名称' }]}
          />
          <Form.Input
            field="code"
            label="字典编码"
            placeholder="例如：order_status"
            rules={[{ required: true, message: '请输入字典编码' }]}
          />
          <Form.InputNumber field="sort_order" label="排序" min={0} />
          <Form.Switch field="is_active" label="启用" />
          <Form.TextArea field="description" label="描述" rows={3} maxCount={300} />
        </Form>
      </Modal>

      <Modal
        title={itemEditRecord?.id ? '编辑字典项' : '新建字典项'}
        visible={itemModalVisible}
        onOk={handleSubmitItem}
        onCancel={() => setItemModalVisible(false)}
        okButtonProps={{ loading: itemSubmitting }}
        width={520}
        afterClose={() => itemFormApiRef.current?.reset()}
      >
        <Form
          getFormApi={api => itemFormApiRef.current = api}
          initValues={itemInitValues}
          labelPosition="left"
          labelWidth={95}
        >
          <Form.Input
            field="label"
            label="字典标签"
            rules={[{ required: true, message: '请输入字典标签' }]}
          />
          <Form.Input
            field="value"
            label="字典值"
            rules={[{ required: true, message: '请输入字典值' }]}
          />
          <Form.Input
            field="color"
            label="标签颜色"
            placeholder="例如：#16a34a"
          />
          <Form.InputNumber field="sort_order" label="排序" min={0} />
          <Form.Switch field="is_default" label="默认项" />
          <Form.Switch field="is_active" label="启用" />
          <Form.TextArea field="description" label="描述" rows={3} maxCount={300} />
        </Form>
      </Modal>
    </div>
  )
}
