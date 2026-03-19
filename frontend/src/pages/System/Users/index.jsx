import { useState, useEffect, useRef } from 'react'
import {
  Table, Button, Modal, Form, Toast,
  Popconfirm, Tag, Input, Space, Typography,
} from '@douyinfe/semi-ui'
import { IconPlus, IconRefresh, IconSearch } from '@douyinfe/semi-icons'
import {
  getUsers, createUser, updateUser, deleteUser,
  exportUsers, downloadUsersTemplate, importUsers,
} from '../../../api/users'
import { getRoles } from '../../../api/roles'
import ExportFieldsModal from '../../../components/ImportExport/ExportFieldsModal'
import ImportCsvModal from '../../../components/ImportExport/ImportCsvModal'
import { downloadBlobFile } from '../../../utils/file'

const USER_EXPORT_FIELDS = [
  { label: 'ID', value: 'id' },
  { label: '用户名', value: 'username' },
  { label: '角色名称', value: 'role_names' },
  { label: '角色编码', value: 'role_codes' },
  { label: '创建时间', value: 'created_at' },
]
const normalizeFileType = (raw) => (['csv', 'xls', 'xlsx'].includes(raw) ? raw : 'xlsx')
const CARD_STYLE = {
  background: 'var(--semi-color-bg-1)',
  borderRadius: 8,
  padding: 16,
  marginBottom: 12,
  boxShadow: '0 1px 2px rgba(15,23,42,0.04), 0 6px 18px rgba(15,23,42,0.06)',
}

export default function Users() {
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [querySearch, setQuerySearch] = useState('')
  const [modalVisible, setModalVisible] = useState(false)
  const [editRecord, setEditRecord] = useState(null)
  const [roles, setRoles] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [exportModalVisible, setExportModalVisible] = useState(false)
  const [importModalVisible, setImportModalVisible] = useState(false)
  const formApiRef = useRef()

  const fetchData = (p = 1, s = querySearch) => {
    setQuerySearch(s)
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
        fetchData(page, querySearch)
      })
        .catch((err) => Toast.error(err?.error || '操作失败'))
        .finally(() => setSubmitting(false))
    })
  }

  const handleDelete = (id) => {
    deleteUser(id)
      .then(() => { Toast.success('删除成功'); fetchData(page, querySearch) })
      .catch((err) => Toast.error(err?.error || '删除失败'))
  }

  const handleSearch = () => {
    setPage(1)
    setSelectedRowKeys([])
    fetchData(1, search)
  }

  const handleReset = () => {
    setSearch('')
    setPage(1)
    setSelectedRowKeys([])
    fetchData(1, '')
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
      payload.filters = { search: querySearch }
    }
    exportUsers(payload)
      .then((blob) => {
        downloadBlobFile(blob, `users_export.${finalFileType}`)
        Toast.success('导出成功')
        setExportModalVisible(false)
      })
      .catch((err) => Toast.error(err?.error || '导出失败'))
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
      <Typography.Title heading={5} style={{ marginBottom: 16 }}>
        用户管理
      </Typography.Title>

      <div style={CARD_STYLE}>
        <Space style={{ flexWrap: 'wrap' }}>
          <Input
            prefix={<IconSearch />}
            placeholder="搜索用户名"
            value={search}
            onChange={(v) => setSearch(v)}
            onEnterPress={handleSearch}
            style={{ width: 240 }}
          />
          <Button icon={<IconSearch />} type="primary" onClick={handleSearch}>查询</Button>
          <Button icon={<IconRefresh />} onClick={handleReset}>重置</Button>
        </Space>
      </div>

      <div style={CARD_STYLE}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
          <Typography.Text strong>用户列表</Typography.Text>
          <Space>
            <Button onClick={() => setImportModalVisible(true)}>导入</Button>
            <Button onClick={() => setExportModalVisible(true)}>导出</Button>
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
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys),
          }}
          pagination={{
            total,
            currentPage: page,
            pageSize: 20,
            onPageChange: (p) => { setPage(p); fetchData(p, querySearch) },
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
            disabled={editRecord?.username === 'admin'}
          />
        </Form>
      </Modal>

      <ExportFieldsModal
        visible={exportModalVisible}
        title="用户导出字段"
        ruleHint={
          selectedRowKeys.length > 0
            ? `已勾选 ${selectedRowKeys.length} 条，将优先导出勾选数据`
            : '未勾选数据时，将按当前查询条件导出全部结果'
        }
        fieldOptions={USER_EXPORT_FIELDS}
        defaultFields={['username', 'role_names', 'created_at']}
        onCancel={() => setExportModalVisible(false)}
        onConfirm={handleExport}
      />

      <ImportCsvModal
        visible={importModalVisible}
        title="导入用户"
        targetLabel="用户管理"
        onCancel={() => setImportModalVisible(false)}
        onDownloadTemplate={(fileType) =>
          downloadUsersTemplate(normalizeFileType(fileType))
            .then((blob) => {
              const ext = normalizeFileType(fileType)
              downloadBlobFile(blob, `users_import_template.${ext}`)
              Toast.success('模板下载成功')
            })
            .catch((err) => Toast.error(err?.error || '模板下载失败'))
        }
        onImport={(file) => importUsers(file)}
        onImported={(res) => {
          Toast.success(`导入成功：新增 ${res?.created || 0} 条，更新 ${res?.updated || 0} 条`)
          fetchData(page, querySearch)
        }}
        errorExportFileName="users_import_error_rows.csv"
      />
    </div>
  )
}
