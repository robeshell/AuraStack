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
import {
  createScheduledTask,
  deleteScheduledTask,
  getScheduledTaskList,
  getScheduledTaskRunLogs,
  runScheduledTaskNow,
  updateScheduledTask,
} from '../../api/scheduled_tasks'

const CARD_STYLE = {
  background: 'var(--semi-color-bg-1)',
  borderRadius: 8,
  padding: 16,
  marginBottom: 12,
  boxShadow: '0 1px 2px rgba(15,23,42,0.04), 0 6px 18px rgba(15,23,42,0.06)',
}

const STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: 'idle', value: 'idle' },
  { label: 'running', value: 'running' },
  { label: 'success', value: 'success' },
  { label: 'failed', value: 'failed' },
]

const ACTIVE_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '启用', value: 'true' },
  { label: '停用', value: 'false' },
]

const METHOD_OPTIONS = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
  { label: 'PATCH', value: 'PATCH' },
]

const formatDateTime = (value) => (value ? value.slice(0, 19).replace('T', ' ') : '-')

const statusColor = (status) => {
  if (status === 'success') return 'green'
  if (status === 'failed') return 'red'
  if (status === 'running') return 'blue'
  return 'grey'
}

export default function ScheduledTasks() {
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)

  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [isActive, setIsActive] = useState('')
  const [queryFilters, setQueryFilters] = useState({
    search: '',
    status: '',
    is_active: '',
  })

  const [modalVisible, setModalVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editRecord, setEditRecord] = useState(null)
  const [runningTaskId, setRunningTaskId] = useState(null)

  const [runLogs, setRunLogs] = useState([])
  const [runLogsTotal, setRunLogsTotal] = useState(0)
  const [runLogsLoading, setRunLogsLoading] = useState(false)
  const [runLogsPage, setRunLogsPage] = useState(1)

  const formApiRef = useRef()

  const fetchData = (nextPage = 1, customFilters = queryFilters) => {
    setLoading(true)
    getScheduledTaskList({
      page: nextPage,
      per_page: 20,
      search: customFilters.search || undefined,
      status: customFilters.status || undefined,
      is_active: customFilters.is_active || undefined,
    })
      .then((res) => {
        setData(res.items || [])
        setTotal(res.total || 0)
      })
      .catch(() => Toast.error('加载定时任务失败'))
      .finally(() => setLoading(false))
  }

  const fetchRunLogs = (nextPage = 1) => {
    setRunLogsLoading(true)
    getScheduledTaskRunLogs({
      page: nextPage,
      per_page: 20,
    })
      .then((res) => {
        setRunLogs(res.items || [])
        setRunLogsTotal(res.total || 0)
      })
      .catch(() => Toast.error('加载执行记录失败'))
      .finally(() => setRunLogsLoading(false))
  }

  useEffect(() => {
    fetchData(1, queryFilters)
    fetchRunLogs(1)
  }, [])

  const handleSearch = () => {
    const nextFilters = {
      search: search.trim(),
      status: status || '',
      is_active: isActive || '',
    }
    setQueryFilters(nextFilters)
    setPage(1)
    fetchData(1, nextFilters)
  }

  const handleReset = () => {
    setSearch('')
    setStatus('')
    setIsActive('')
    const nextFilters = {
      search: '',
      status: '',
      is_active: '',
    }
    setQueryFilters(nextFilters)
    setPage(1)
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
        name: (values.name || '').trim(),
        task_code: (values.task_code || '').trim(),
        cron_expression: (values.cron_expression || '').trim(),
        request_url: (values.request_url || '').trim(),
        request_headers: (values.request_headers || '').trim(),
        request_body: (values.request_body || '').trim(),
        remark: (values.remark || '').trim(),
      }
      setSubmitting(true)
      const req = editRecord?.id
        ? updateScheduledTask(editRecord.id, payload)
        : createScheduledTask(payload)
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
    deleteScheduledTask(id)
      .then(() => {
        Toast.success('删除成功')
        fetchData(page, queryFilters)
      })
      .catch((err) => Toast.error(err?.error || '删除失败'))
  }

  const handleRunNow = (record) => {
    setRunningTaskId(record.id)
    runScheduledTaskNow(record.id)
      .then((res) => {
        if (res?.run?.status === 'success') {
          Toast.success('执行成功')
        } else {
          Toast.warning(res?.error || '执行失败')
        }
        fetchData(page, queryFilters)
        fetchRunLogs(runLogsPage)
      })
      .catch((err) => Toast.error(err?.error || '执行失败'))
      .finally(() => setRunningTaskId(null))
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '任务名称', dataIndex: 'name', width: 160 },
    { title: '任务编码', dataIndex: 'task_code', width: 170, render: (value) => <Tag>{value}</Tag> },
    { title: 'Cron 表达式', dataIndex: 'cron_expression', width: 160, render: (value) => <Typography.Text code>{value}</Typography.Text> },
    { title: '方法', dataIndex: 'request_method', width: 80 },
    {
      title: '请求地址',
      dataIndex: 'request_url',
      width: 260,
      render: (value) => (
        <Typography.Text ellipsis={{ showTooltip: true }} style={{ maxWidth: 240, display: 'inline-block' }}>
          {value}
        </Typography.Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'last_status',
      width: 100,
      render: (value) => <Tag color={statusColor(value)}>{value || 'idle'}</Tag>,
    },
    { title: '下次执行', dataIndex: 'next_run_at', width: 170, render: formatDateTime },
    { title: '最近执行', dataIndex: 'last_run_at', width: 170, render: formatDateTime },
    { title: '执行次数', dataIndex: 'run_count', width: 90, render: (value) => value || 0 },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 90,
      render: (value) => <Tag color={value ? 'green' : 'grey'}>{value ? '启用' : '停用'}</Tag>,
    },
    {
      title: '操作',
      width: 260,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            type="primary"
            theme="borderless"
            loading={runningTaskId === record.id}
            onClick={() => handleRunNow(record)}
          >
            立即执行
          </Button>
          <Button size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除该定时任务？" content="删除后不可恢复" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" type="danger">删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const runLogColumns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '任务', dataIndex: 'task_name', width: 140 },
    { title: '任务编码', dataIndex: 'task_code', width: 170 },
    { title: '触发方式', dataIndex: 'trigger_type', width: 90 },
    { title: '状态', dataIndex: 'status', width: 90, render: (value) => <Tag color={statusColor(value)}>{value}</Tag> },
    { title: '响应码', dataIndex: 'response_status', width: 90, render: (value) => value || '-' },
    { title: '耗时(ms)', dataIndex: 'duration_ms', width: 90, render: (value) => value || 0 },
    { title: '开始时间', dataIndex: 'started_at', width: 170, render: formatDateTime },
    { title: '结束时间', dataIndex: 'finished_at', width: 170, render: formatDateTime },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      width: 220,
      render: (value) => (
        <Typography.Text ellipsis={{ showTooltip: true }} style={{ maxWidth: 200, display: 'inline-block' }}>
          {value || '-'}
        </Typography.Text>
      ),
    },
  ]

  const initValues = editRecord || {
    request_method: 'GET',
    timeout_seconds: 10,
    is_active: true,
    request_headers: '{"Content-Type":"application/json"}',
  }

  return (
    <div>
      <Typography.Title heading={5} style={{ marginBottom: 16 }}>
        定时任务
      </Typography.Title>

      <div style={CARD_STYLE}>
        <Space style={{ flexWrap: 'wrap' }}>
          <Input
            prefix={<IconSearch />}
            placeholder="任务名称/编码/请求地址"
            value={search}
            onChange={(value) => setSearch(value)}
            onEnterPress={handleSearch}
            style={{ width: 280 }}
          />
          <Select
            style={{ width: 140 }}
            value={status}
            optionList={STATUS_OPTIONS}
            onChange={(value) => setStatus(value)}
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
          <Typography.Text strong>任务列表</Typography.Text>
          <Button icon={<IconPlus />} theme="solid" type="primary" onClick={openCreate}>
            新建任务
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            total,
            currentPage: page,
            pageSize: 20,
            onPageChange: (nextPage) => {
              setPage(nextPage)
              fetchData(nextPage, queryFilters)
            },
          }}
          scroll={{ x: 1750 }}
        />
      </div>

      <div style={CARD_STYLE}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
          <Typography.Text strong>执行记录</Typography.Text>
          <Button onClick={() => fetchRunLogs(1)}>刷新记录</Button>
        </div>
        <Table
          columns={runLogColumns}
          dataSource={runLogs}
          rowKey="id"
          loading={runLogsLoading}
          pagination={{
            total: runLogsTotal,
            currentPage: runLogsPage,
            pageSize: 20,
            onPageChange: (nextPage) => {
              setRunLogsPage(nextPage)
              fetchRunLogs(nextPage)
            },
          }}
          scroll={{ x: 1300 }}
        />
      </div>

      <Modal
        title={editRecord?.id ? '编辑定时任务' : '新建定时任务'}
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        okButtonProps={{ loading: submitting }}
        width={720}
        afterClose={() => formApiRef.current?.reset()}
      >
        <Form getFormApi={(api) => { formApiRef.current = api }} initValues={initValues} labelPosition="left" labelWidth={110}>
          <Form.Input field="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]} />
          <Form.Input
            field="task_code"
            label="任务编码"
            placeholder="例如：sync_orders_job"
            rules={[{ required: true, message: '请输入任务编码' }]}
            disabled={Boolean(editRecord?.id)}
          />
          <Form.Input
            field="cron_expression"
            label="Cron 表达式"
            placeholder="例如：*/5 * * * *"
            rules={[{ required: true, message: '请输入 Cron 表达式' }]}
          />
          <Form.Select field="request_method" label="请求方法" optionList={METHOD_OPTIONS} style={{ width: '100%' }} />
          <Form.Input
            field="request_url"
            label="请求地址"
            placeholder="例如：https://api.example.com/tasks/sync"
            rules={[{ required: true, message: '请输入请求地址' }]}
          />
          <Form.InputNumber field="timeout_seconds" label="超时(秒)" min={1} max={120} />
          <Form.TextArea
            field="request_headers"
            label="请求头(JSON)"
            placeholder='例如：{"Content-Type":"application/json","Authorization":"Bearer xxx"}'
            rows={3}
          />
          <Form.TextArea
            field="request_body"
            label="请求体"
            placeholder='例如：{"biz_date":"2026-03-19"}'
            rows={3}
          />
          <Form.Switch field="is_active" label="启用任务" />
          <Form.TextArea field="remark" label="备注" rows={2} maxCount={500} />
        </Form>
      </Modal>
    </div>
  )
}
