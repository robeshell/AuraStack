import request from './index'

export const getDictTypes = (params) => request.get('/admin/dicts', { params })
export const getDictTypeDetail = (id, params) => request.get(`/admin/dicts/${id}`, { params })
export const createDictType = (data) => request.post('/admin/dicts', data)
export const updateDictType = (id, data) => request.put(`/admin/dicts/${id}`, data)
export const deleteDictType = (id) => request.delete(`/admin/dicts/${id}`)

export const getDictItems = (dictId, params) => request.get(`/admin/dicts/${dictId}/items`, { params })
export const createDictItem = (dictId, data) => request.post(`/admin/dicts/${dictId}/items`, data)
export const updateDictItem = (id, data) => request.put(`/admin/dicts/items/${id}`, data)
export const deleteDictItem = (id) => request.delete(`/admin/dicts/items/${id}`)
