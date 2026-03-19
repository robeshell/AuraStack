import { useState, useEffect, useRef } from 'react'
import {
  Table, Button, Modal, Form, Toast,
  Popconfirm, Input, Select, Space, Typography, Tag, Progress,
} from '@douyinfe/semi-ui'
import { IconPlus, IconSearch, IconRefresh } from '@douyinfe/semi-icons'
import {
  getDictTypes,
  createDictType,
  updateDictType,
  deleteDictType,
  getDictItems,
  exportDictItems,
  downloadDictItemsTemplate,
  importDictItems,
  createDictItem,
  updateDictItem,
  deleteDictItem,
} from '../../../api/dicts'

const formatDateTime = (value) => (value ? value.slice(0, 19).replace('T', ' ') : '-')
const FILE_TYPE_OPTIONS = [
  { label: 'CSV', value: 'csv' },
  { label: 'XLS', value: 'xls' },
  { label: 'XLSX', value: 'xlsx' },
]
const normalizeFileType = (raw) => (['csv', 'xls', 'xlsx'].includes(raw) ? raw : 'xlsx')
const PANEL_CARD_STYLE = {
  background: 'var(--semi-color-bg-1)',
  borderRadius: 8,
  padding: 16,
  boxShadow: '0 1px 2px rgba(15,23,42,0.04), 0 6px 18px rgba(15,23,42,0.06)',
}
const PANEL_SECTION_STYLE = {
  background: 'var(--semi-color-fill-0)',
  borderRadius: 6,
  padding: 12,
  marginBottom: 12,
}

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
  const [dictFileType, setDictFileType] = useState('xlsx')

  const [typeModalVisible, setTypeModalVisible] = useState(false)
  const [typeEditRecord, setTypeEditRecord] = useState(null)
  const [typeSubmitting, setTypeSubmitting] = useState(false)
  const typeFormApiRef = useRef()

  const [itemModalVisible, setItemModalVisible] = useState(false)
  const [itemEditRecord, setItemEditRecord] = useState(null)
  const [itemSubmitting, setItemSubmitting] = useState(false)
  const [itemColor, setItemColor] = useState('#1677ff')
  const [importModalVisible, setImportModalVisible] = useState(false)
  const [importFile, setImportFile] = useState(null)
  const [importDragging, setImportDragging] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importProgress, setImportProgress] = useState(0)
  const [importResult, setImportResult] = useState(null)
  const itemFormApiRef = useRef()
  const fileInputRef = useRef()
  const importProgressTimerRef = useRef(null)

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

  useEffect(() => () => {
    if (importProgressTimerRef.current) {
      clearInterval(importProgressTimerRef.current)
      importProgressTimerRef.current = null
    }
  }, [])

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
    setItemColor('')
    setItemModalVisible(true)
  }

  const openEditItem = (record) => {
    setItemEditRecord(record)
    setItemColor(record?.color || '')
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
      const payload = {
        ...values,
        color: (itemColor || '').trim() || null,
      }
      const req = itemEditRecord?.id
        ? updateDictItem(itemEditRecord.id, payload)
        : createDictItem(selectedType.id, payload)

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

  const handleExportItems = () => {
    if (!selectedType?.id) {
      Toast.warning('请先选择字典类型')
      return
    }
    const finalFileType = normalizeFileType(dictFileType)
    exportDictItems(selectedType.id, finalFileType)
      .then((blob) => {
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `dict_${selectedType.code}_items.${finalFileType}`
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
        Toast.success('导出成功')
      })
      .catch((err) => Toast.error(err?.error || '导出失败'))
  }

  const clearImportProgressTimer = () => {
    if (importProgressTimerRef.current) {
      clearInterval(importProgressTimerRef.current)
      importProgressTimerRef.current = null
    }
  }

  const startImportProgressSimulation = () => {
    clearImportProgressTimer()
    setImportProgress(0)
    importProgressTimerRef.current = setInterval(() => {
      setImportProgress((prev) => {
        if (prev >= 92) {
          return prev
        }
        const step = Math.max(1, Math.round((92 - prev) * 0.2))
        return Math.min(92, prev + step)
      })
    }, 120)
  }

  const openImportModal = () => {
    if (!selectedType?.id) {
      Toast.warning('请先选择字典类型')
      return
    }
    setImportModalVisible(true)
    setImportFile(null)
    setImportResult(null)
    setImportProgress(0)
  }

  const closeImportModal = () => {
    if (importing) {
      return
    }
    setImportModalVisible(false)
    setImportDragging(false)
    setImportFile(null)
    setImportResult(null)
    setImportProgress(0)
    clearImportProgressTimer()
  }

  const handleDownloadTemplate = () => {
    if (!selectedType?.id) {
      Toast.warning('请先选择字典类型')
      return
    }
    const finalFileType = normalizeFileType(dictFileType)
    downloadDictItemsTemplate(selectedType.id, finalFileType)
      .then((blob) => {
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `dict_${selectedType.code}_import_template.${finalFileType}`
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
        Toast.success('模板下载成功')
      })
      .catch((err) => Toast.error(err?.error || '模板下载失败'))
  }

  const normalizeImportFile = (file) => {
    if (!file) {
      return null
    }
    const name = (file.name || '').toLowerCase()
    const ext = name.includes('.') ? name.split('.').pop() : ''
    if (!['csv', 'xls', 'xlsx'].includes(ext)) {
      Toast.error('仅支持 CSV / XLS / XLSX 文件')
      return null
    }
    return file
  }

  const handleChooseImportFile = (event) => {
    const file = normalizeImportFile(event.target.files?.[0])
    event.target.value = ''
    if (!file) {
      return
    }
    setImportFile(file)
    setImportResult(null)
    setImportProgress(0)
  }

  const handleImportDragOver = (event) => {
    event.preventDefault()
    if (!importDragging) {
      setImportDragging(true)
    }
  }

  const handleImportDragLeave = (event) => {
    event.preventDefault()
    setImportDragging(false)
  }

  const handleImportDrop = (event) => {
    event.preventDefault()
    setImportDragging(false)
    const file = normalizeImportFile(event.dataTransfer?.files?.[0])
    if (!file) {
      return
    }
    setImportFile(file)
    setImportResult(null)
    setImportProgress(0)
  }

  const handleConfirmImport = () => {
    if (!selectedType?.id) {
      Toast.warning('请先选择字典类型')
      return
    }
    if (!importFile) {
      Toast.warning('请先上传导入文件')
      return
    }

    setImporting(true)
    setImportResult(null)
    startImportProgressSimulation()

    importDictItems(selectedType.id, importFile)
      .then((res) => {
        clearImportProgressTimer()
        setImportProgress(100)
        setImportResult(res)
        Toast.success(`导入成功：新增 ${res.created || 0} 条，更新 ${res.updated || 0} 条`)
        fetchItems(selectedType.id, itemSearch)
      })
      .catch((err) => Toast.error(err?.error || '导入失败'))
      .finally(() => setImporting(false))
  }

  const handleReSelectImportFile = () => {
    fileInputRef.current?.click()
  }

  const handleClearImportFile = () => {
    if (importing) {
      return
    }
    setImportFile(null)
    setImportResult(null)
    setImportProgress(0)
    clearImportProgressTimer()
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
        <div style={PANEL_CARD_STYLE}>
          <Typography.Text strong>字典类型</Typography.Text>

          <div style={{ ...PANEL_SECTION_STYLE, marginTop: 12 }}>
            <Typography.Text strong>查询条件</Typography.Text>
            <div style={{ marginTop: 10 }}>
              <Space>
                <Input
                  prefix={<IconSearch />}
                  placeholder="搜索名称/编码"
                  value={typeSearch}
                  onChange={(value) => setTypeSearch(value)}
                  onEnterPress={handleTypeSearch}
                  style={{ width: 200 }}
                />
                <Button icon={<IconSearch />} type="primary" onClick={handleTypeSearch}>查询</Button>
                <Button icon={<IconRefresh />} onClick={handleTypeReset}>重置</Button>
              </Space>
            </div>
          </div>

          <div style={PANEL_SECTION_STYLE}>
            <Typography.Text strong>快捷操作</Typography.Text>
            <div style={{ marginTop: 10 }}>
              <Space>
                <Button icon={<IconPlus />} type="primary" theme="solid" onClick={openCreateType}>
                  新建
                </Button>
              </Space>
            </div>
          </div>

          <div style={{ ...PANEL_SECTION_STYLE, marginBottom: 0 }}>
            <Typography.Text strong>字典类型列表</Typography.Text>
            <div style={{ marginTop: 10 }}>
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
          </div>
        </div>

        <div style={PANEL_CARD_STYLE}>
          <div>
            <Typography.Text strong>字典项</Typography.Text>
            <Typography.Text type="tertiary" style={{ marginLeft: 8 }}>
              {selectedType ? `当前类型：${selectedType.name} (${selectedType.code})` : '请先在左侧选择字典类型'}
            </Typography.Text>
          </div>

          <div style={{ ...PANEL_SECTION_STYLE, marginTop: 12 }}>
            <Typography.Text strong>查询条件</Typography.Text>
            <div style={{ marginTop: 10 }}>
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
                <Button icon={<IconSearch />} type="primary" onClick={handleItemSearch} disabled={!selectedType}>查询</Button>
                <Button icon={<IconRefresh />} onClick={handleItemReset} disabled={!selectedType}>重置</Button>
              </Space>
            </div>
          </div>

          <div style={PANEL_SECTION_STYLE}>
            <Typography.Text strong>快捷操作</Typography.Text>
            <div style={{ marginTop: 10 }}>
              <Space>
                <Select
                  value={dictFileType}
                  optionList={FILE_TYPE_OPTIONS}
                  style={{ width: 90 }}
                  onChange={(value) => setDictFileType(normalizeFileType(value))}
                />
                <Button onClick={handleExportItems} disabled={!selectedType}>导出</Button>
                <Button onClick={openImportModal} disabled={!selectedType}>导入</Button>
                <Button icon={<IconPlus />} type="primary" theme="solid" onClick={openCreateItem} disabled={!selectedType}>
                  新建
                </Button>
              </Space>
            </div>
          </div>

          <div style={{ ...PANEL_SECTION_STYLE, marginBottom: 0 }}>
            <Typography.Text strong>字典项列表</Typography.Text>
            <div style={{ marginTop: 10 }}>
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
          <div style={{ margin: '8px 0 16px 95px' }}>
            <Typography.Text type="secondary" size="small">标签颜色</Typography.Text>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
              <input
                type="color"
                value={itemColor || '#1677ff'}
                onChange={(e) => setItemColor(e.target.value)}
                style={{ width: 40, height: 32, border: '1px solid var(--semi-color-border)', borderRadius: 4, padding: 0, background: 'transparent' }}
              />
              <Input
                value={itemColor || ''}
                onChange={(value) => setItemColor(value)}
                placeholder="例如：#16a34a"
                style={{ width: 180 }}
              />
              {itemColor ? (
                <Tag style={{ backgroundColor: itemColor, color: '#fff', border: 'none' }}>{itemColor}</Tag>
              ) : (
                <Tag>无</Tag>
              )}
            </div>
          </div>
          <Form.InputNumber field="sort_order" label="排序" min={0} />
          <Form.Switch field="is_default" label="默认项" />
          <Form.Switch field="is_active" label="启用" />
          <Form.TextArea field="description" label="描述" rows={3} maxCount={300} />
        </Form>
      </Modal>

      <Modal
        title="导入字典项"
        visible={importModalVisible}
        onOk={handleConfirmImport}
        okText="确认导入"
        cancelText="关闭"
        onCancel={closeImportModal}
        okButtonProps={{ loading: importing, disabled: !importFile || importing }}
        cancelButtonProps={{ disabled: importing }}
        width={620}
        maskClosable={!importing}
      >
        <div style={{ marginBottom: 12 }}>
          <Typography.Text>
            当前字典类型：
            {selectedType ? `${selectedType.name} (${selectedType.code})` : '-'}
          </Typography.Text>
        </div>
        <div style={{ marginBottom: 12 }}>
          <Space>
            <Select
              value={dictFileType}
              optionList={FILE_TYPE_OPTIONS}
              style={{ width: 120 }}
              onChange={(value) => setDictFileType(normalizeFileType(value))}
              disabled={importing}
            />
            <Button onClick={handleDownloadTemplate} disabled={!selectedType || importing}>
              下载导入模板
            </Button>
          </Space>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xls,.xlsx"
          style={{ display: 'none' }}
          onChange={handleChooseImportFile}
        />

        <div
          role="button"
          tabIndex={0}
          onClick={handleReSelectImportFile}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              handleReSelectImportFile()
            }
          }}
          onDragOver={handleImportDragOver}
          onDragLeave={handleImportDragLeave}
          onDrop={handleImportDrop}
          style={{
            border: `1px dashed ${importDragging ? 'var(--semi-color-primary)' : 'var(--semi-color-border)'}`,
            background: importDragging ? 'var(--semi-color-fill-0)' : 'transparent',
            borderRadius: 6,
            padding: '28px 20px',
            textAlign: 'center',
            cursor: 'pointer',
            marginBottom: 12,
            transition: 'all .15s ease',
          }}
        >
          <Typography.Text strong>拖拽 CSV/XLS/XLSX 到此处上传</Typography.Text>
          <div style={{ marginTop: 8 }}>
            <Typography.Text type="tertiary">
              或点击这里选择文件
            </Typography.Text>
          </div>
        </div>

        <div style={{ marginBottom: 12 }}>
          {importFile ? (
            <Space>
              <Tag color="blue">{importFile.name}</Tag>
              <Typography.Text type="tertiary">
                {(importFile.size / 1024).toFixed(1)} KB
              </Typography.Text>
              <Button size="small" onClick={handleReSelectImportFile} disabled={importing}>重新选择</Button>
              <Button size="small" type="tertiary" onClick={handleClearImportFile} disabled={importing}>清空</Button>
            </Space>
          ) : (
            <Typography.Text type="tertiary">尚未选择文件</Typography.Text>
          )}
        </div>

        {(importing || importProgress > 0) && (
          <div style={{ marginBottom: 12 }}>
            <Progress percent={importProgress} showInfo strokeWidth={8} aria-label="导入进度" />
            <div style={{ marginTop: 6 }}>
              <Typography.Text type="tertiary">
                {importing ? '正在导入，请稍候...' : (importProgress >= 100 ? '导入完成' : '等待导入')}
              </Typography.Text>
            </div>
          </div>
        )}

        {importResult && (
          <div
            style={{
              border: '1px solid var(--semi-color-success-light-default)',
              background: 'var(--semi-color-success-light-default)',
              borderRadius: 4,
              padding: '10px 12px',
            }}
          >
            <Typography.Text>
              导入结果：新增 {importResult.created || 0} 条，更新 {importResult.updated || 0} 条
            </Typography.Text>
          </div>
        )}
      </Modal>
    </div>
  )
}
