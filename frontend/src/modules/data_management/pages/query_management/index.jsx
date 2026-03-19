import { useEffect, useRef, useState } from 'react'
import {
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Toast,
  Typography,
} from '@douyinfe/semi-ui'
import { IconPlus, IconRefresh, IconSearch } from '@douyinfe/semi-icons'
import ExportFieldsModal from '../../../../shared/components/import-export/ExportFieldsModal'
import ImportCsvModal from '../../../../shared/components/import-export/ImportCsvModal'
import { downloadBlobFile } from '../../../../shared/utils/file'
import {
  createQueryManagement,
  deleteQueryManagement,
  downloadQueryManagementTemplate,
  exportQueryManagement,
  getQueryManagementList,
  importQueryManagement,
  updateQueryManagement,
} from '../../api/query_management'

const CARD_STYLE = {
  background: 'var(--semi-color-bg-1)',
  borderRadius: 8,
  padding: 16,
  marginBottom: 12,
  boxShadow: '0 1px 2px rgba(15,23,42,0.04), 0 6px 18px rgba(15,23,42,0.06)',
}

const CATEGORY_OPTIONS = [
  { label: '通用', value: 'general' },
  { label: '订单', value: 'order' },
  { label: '用户', value: 'user' },
  { label: '财务', value: 'finance' },
  { label: '风控', value: 'risk' },
]

const ACTIVE_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '启用', value: 'true' },
  { label: '停用', value: 'false' },
]

const QUERY_EXPORT_FIELDS = [
  { label: 'ID', value: 'id' },
  { label: '查询名称', value: 'name' },
  { label: '查询编码', value: 'query_code' },
  { label: '查询分类', value: 'category' },
  { label: '关键字', value: 'keyword' },
  { label: '数据源', value: 'data_source' },
  { label: '负责人', value: 'owner' },
  { label: '优先级', value: 'priority' },
  { label: '状态', value: 'is_active' },
  { label: '描述', value: 'description' },
  { label: '创建时间', value: 'created_at' },
  { label: '更新时间', value: 'updated_at' },
]

const normalizeFileType = (raw) => (['csv', 'xls', 'xlsx'].includes(raw) ? raw : 'xlsx')
const formatDateTime = (value) => (value ? value.slice(0, 19).replace('T', ' ') : '-')

const mapCategoryLabel = (value) => {
  const matched = CATEGORY_OPTIONS.find((item) => item.value === value)
  return matched?.label || value || '-'
}

export default function QueryManagement() {
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [owner, setOwner] = useState('')
  const [isActive, setIsActive] = useState('')
  const [queryFilters, setQueryFilters] = useState({
    search: '',
    category: '',
    owner: '',
    is_active: '',
  })

  const [modalVisible, setModalVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editRecord, setEditRecord] = useState(null)

  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [exportModalVisible, setExportModalVisible] = useState(false)
  const [importModalVisible, setImportModalVisible] = useState(false)

  const formApiRef = useRef()

  const fetchData = (nextPage = 1, customFilters = queryFilters) => {
    setLoading(true)
    const payload = {
      page: nextPage,
      per_page: 20,
      search: customFilters.search || undefined,
      category: customFilters.category || undefined,
      owner: customFilters.owner || undefined,
      is_active: customFilters.is_active || undefined,
    }
    getQueryManagementList(payload)
      .then((res) => {
        setData(res.items || [])
        setTotal(res.total || 0)
      })
      .catch(() => Toast.error('加载查询管理列表失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchData(1, queryFilters)
  }, [])

  const handleSearch = () => {
    const nextFilters = {
      search: search.trim(),
      category: category || '',
      owner: owner.trim(),
      is_active: isActive || '',
    }
    setQueryFilters(nextFilters)
    setPage(1)
    setSelectedRowKeys([])
    fetchData(1, nextFilters)
  }

  const handleReset = () => {
    setSearch('')
    setCategory('')
    setOwner('')
    setIsActive('')
    const nextFilters = {
      search: '',
      category: '',
      owner: '',
      is_active: '',
    }
    setQueryFilters(nextFilters)
    setPage(1)
    setSelectedRowKeys([])
    fetchData(1, nextFilters)
  }

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
      const payload = {
        ...values,
        query_code: (values.query_code || '').trim(),
        name: (values.name || '').trim(),
        keyword: (values.keyword || '').trim(),
        owner: (values.owner || '').trim(),
        data_source: (values.data_source || '').trim(),
        description: (values.description || '').trim(),
      }
      setSubmitting(true)
      const req = editRecord?.id
        ? updateQueryManagement(editRecord.id, payload)
        : createQueryManagement(payload)
      req.then(() => {
        Toast.success(editRecord?.id ? '更新成功' : '创建成功')
        setModalVisible(false)
        fetchData(page, queryFilters)
      })
        .catch((err) => Toast.error(err?.error || '保存失败'))
        .finally(() => setSubmitting(false))
    })
  }

  const handleDelete = (id) => {
    deleteQueryManagement(id)
      .then(() => {
        Toast.success('删除成功')
        fetchData(page, queryFilters)
      })
      .catch((err) => Toast.error(err?.error || '删除失败'))
  }

  const handleExport = ({ fields, fileType }) => {
    const finalFileType = normalizeFileType(fileType)
    const hasSelected = selectedRowKeys.length > 0
    const payload = {
      fields,
      file_type: finalFileType,
      export_mode: hasSelected ? 'selected' : 'filtered',
    }
    if (hasSelected) {
      payload.ids = selectedRowKeys
    } else {
      payload.filters = queryFilters
    }
    exportQueryManagement(payload)
      .then((blob) => {
        downloadBlobFile(blob, `query_management_export.${finalFileType}`)
        Toast.success('导出成功')
        setExportModalVisible(false)
      })
      .catch((err) => Toast.error(err?.error || '导出失败'))
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '查询名称', dataIndex: 'name', width: 170 },
    {
      title: '查询编码',
      dataIndex: 'query_code',
      width: 180,
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 100,
      render: (value) => mapCategoryLabel(value),
    },
    { title: '关键字', dataIndex: 'keyword', width: 180, render: (value) => value || '-' },
    { title: '数据源', dataIndex: 'data_source', width: 140, render: (value) => value || '-' },
    { title: '负责人', dataIndex: 'owner', width: 100, render: (value) => value || '-' },
    { title: '优先级', dataIndex: 'priority', width: 80 },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 90,
      render: (value) => <Tag color={value ? 'green' : 'grey'}>{value ? '启用' : '停用'}</Tag>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 170,
      render: formatDateTime,
    },
    {
      title: '操作',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除该查询配置？" content="删除后不可恢复" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" type="danger">删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const initValues = editRecord || {
    category: 'general',
    priority: 0,
    is_active: true,
  }

  return (
    <div>
      <Typography.Title heading={5} style={{ marginBottom: 16 }}>
        查询管理
      </Typography.Title>

      <div style={CARD_STYLE}>
        <Space style={{ flexWrap: 'wrap' }}>
          <Input
            prefix={<IconSearch />}
            placeholder="名称/编码/关键字/数据源/负责人"
            value={search}
            onChange={(value) => setSearch(value)}
            onEnterPress={handleSearch}
            style={{ width: 280 }}
          />
          <Select
            style={{ width: 140 }}
            value={category}
            optionList={[{ label: '全部分类', value: '' }, ...CATEGORY_OPTIONS]}
            onChange={(value) => setCategory(value)}
          />
          <Input
            placeholder="负责人"
            value={owner}
            onChange={(value) => setOwner(value)}
            onEnterPress={handleSearch}
            style={{ width: 140 }}
          />
          <Select
            style={{ width: 130 }}
            value={isActive}
            optionList={ACTIVE_OPTIONS}
            onChange={(value) => setIsActive(value)}
          />
          <Button icon={<IconSearch />} type="primary" onClick={handleSearch}>查询</Button>
          <Button icon={<IconRefresh />} onClick={handleReset}>重置</Button>
        </Space>
      </div>

      <div style={CARD_STYLE}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
          <Typography.Text strong>查询配置列表</Typography.Text>
          <Space>
            <Button onClick={() => setImportModalVisible(true)}>导入</Button>
            <Button onClick={() => setExportModalVisible(true)}>导出</Button>
            <Button icon={<IconPlus />} theme="solid" type="primary" onClick={openCreate}>
              新建查询
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys),
          }}
          pagination={{
            total,
            currentPage: page,
            pageSize: 20,
            onPageChange: (nextPage) => {
              setPage(nextPage)
              fetchData(nextPage, queryFilters)
            },
          }}
        />

        <div style={{ marginTop: 8 }}>
          <Space>
            <Typography.Text type="tertiary">已勾选 {selectedRowKeys.length} 条</Typography.Text>
            {selectedRowKeys.length > 0 ? (
              <Button size="small" type="tertiary" onClick={() => setSelectedRowKeys([])}>
                清空勾选
              </Button>
            ) : null}
          </Space>
        </div>
      </div>

      <Modal
        title={editRecord?.id ? '编辑查询配置' : '新建查询配置'}
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        okButtonProps={{ loading: submitting }}
        width={560}
        afterClose={() => formApiRef.current?.reset()}
      >
        <Form getFormApi={(api) => { formApiRef.current = api }} initValues={initValues} labelPosition="left" labelWidth={95}>
          <Form.Input
            field="name"
            label="查询名称"
            rules={[{ required: true, message: '请输入查询名称' }]}
          />
          <Form.Input
            field="query_code"
            label="查询编码"
            placeholder="例如：order_main_query"
            rules={[{ required: true, message: '请输入查询编码' }]}
            disabled={Boolean(editRecord?.id)}
          />
          <Form.Select
            field="category"
            label="查询分类"
            optionList={CATEGORY_OPTIONS}
            style={{ width: '100%' }}
          />
          <Form.Input field="keyword" label="关键字" placeholder="多个关键字用逗号分隔" />
          <Form.Input field="data_source" label="数据源" placeholder="例如：orders" />
          <Form.Input field="owner" label="负责人" placeholder="例如：admin" />
          <Form.InputNumber field="priority" label="优先级" min={0} max={9999} />
          <Form.Switch field="is_active" label="启用" />
          <Form.TextArea field="description" label="描述" rows={3} maxCount={500} />
        </Form>
      </Modal>

      <ExportFieldsModal
        visible={exportModalVisible}
        title="查询管理导出字段"
        ruleHint={
          selectedRowKeys.length > 0
            ? `已勾选 ${selectedRowKeys.length} 条，将优先导出勾选数据`
            : '未勾选数据时，将按当前筛选条件导出'
        }
        fieldOptions={QUERY_EXPORT_FIELDS}
        defaultFields={['name', 'query_code', 'category', 'owner', 'is_active', 'updated_at']}
        onCancel={() => setExportModalVisible(false)}
        onConfirm={handleExport}
      />

      <ImportCsvModal
        visible={importModalVisible}
        title="导入查询管理"
        targetLabel="查询管理"
        onCancel={() => setImportModalVisible(false)}
        onDownloadTemplate={(fileType) =>
          downloadQueryManagementTemplate(normalizeFileType(fileType))
            .then((blob) => {
              const ext = normalizeFileType(fileType)
              downloadBlobFile(blob, `query_management_import_template.${ext}`)
              Toast.success('模板下载成功')
            })
            .catch((err) => Toast.error(err?.error || '模板下载失败'))
        }
        onImport={(file) => importQueryManagement(file)}
        onImported={(res) => {
          Toast.success(`导入成功：新增 ${res?.created || 0} 条，更新 ${res?.updated || 0} 条`)
          fetchData(page, queryFilters)
        }}
        errorExportFileName="query_management_import_error_rows.csv"
      />
    </div>
  )
}
