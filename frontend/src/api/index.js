import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 市场相关
export const marketApi = {
  getOverview: () => api.get('/market/overview'),
  getIndexDetail: (code, days = 30) => api.get(`/market/index/${code}`, { params: { days } }),
  getFundFlow: (days = 30) => api.get('/market/fund-flow', { params: { days } }),
  getSectors: () => api.get('/market/sectors')
}

// 基金相关
export const fundApi = {
  getList: () => api.get('/funds/'),
  getDetail: (code) => api.get(`/funds/${code}`)
}

// 建议相关
export const adviceApi = {
  getList: () => api.get('/advice/'),
  getFundAdvice: (code) => api.get(`/advice/${code}`)
}

// 任务相关
export const taskApi = {
  refresh: () => api.post('/tasks/refresh'),
  getStatus: () => api.get('/tasks/status')
}

export default api