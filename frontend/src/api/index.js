import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 10000,
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const shouldRedirectToLogin =
      err.response?.status === 401 &&
      Boolean(err.response?.data?.redirect) &&
      window.location.pathname !== '/login'

    if (shouldRedirectToLogin) {
      window.location.href = '/login'
    }
    return Promise.reject(err.response?.data || err)
  }
)

export default request
