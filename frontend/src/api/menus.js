import request from './index'

export const getMenus = (params) => request.get('/admin/menus', { params })
export const createMenu = (data) => request.post('/admin/menus', data)
export const updateMenu = (id, data) => request.put(`/admin/menus/${id}`, data)
export const deleteMenu = (id) => request.delete(`/admin/menus/${id}`)
