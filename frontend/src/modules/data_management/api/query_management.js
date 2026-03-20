import request from '../../../shared/api/request'

export const getQueryManagementList = (params) => request.get('/admin/query-management', { params })
export const getQueryManagementDetail = (id) => request.get(`/admin/query-management/${id}`)
export const createQueryManagement = (data) => request.post('/admin/query-management', data)
export const updateQueryManagement = (id, data) => request.put(`/admin/query-management/${id}`, data)
export const deleteQueryManagement = (id) => request.delete(`/admin/query-management/${id}`)

export const exportQueryManagement = (data) =>
  request.post('/admin/query-management/export', data, { responseType: 'blob' })

export const downloadQueryManagementTemplate = (fileType = 'csv') =>
  request.get('/admin/query-management/template', {
    params: { file_type: fileType },
    responseType: 'blob',
  })

export const importQueryManagement = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/admin/query-management/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const uploadQueryManagementImage = (file) => {
  const uploadFile = file?.fileInstance || file
  if (!uploadFile) {
    return Promise.reject(new Error('请先选择图片文件'))
  }
  const formData = new FormData()
  formData.append('file', uploadFile, uploadFile?.name || 'query-image')
  return request.post('/admin/query-management/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const uploadQueryManagementFile = (file) => {
  const uploadFile = file?.fileInstance || file
  if (!uploadFile) {
    return Promise.reject(new Error('请先选择文件'))
  }
  const formData = new FormData()
  formData.append('file', uploadFile, uploadFile?.name || 'query-file')
  return request.post('/admin/query-management/upload-file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
