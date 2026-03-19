import request from './index'

export const getLoginLogs = (params) => request.get('/admin/logs/login', { params })
export const getOperationLogs = (params) => request.get('/admin/logs/operation', { params })
