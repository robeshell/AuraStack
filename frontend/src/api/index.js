import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 10000,
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    return Promise.reject(err.response?.data || err)
  }
)

export default request
