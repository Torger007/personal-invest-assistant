import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000  // 2分钟超时，Agent 分析可能需要较长时间
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

// Agent 相关
export const agentApi = {
  triggerAnalysis: () => api.post('/agent/analyze'),
  chat: (question) => api.post('/agent/chat', { question }),
  getHistory: (limit = 10) => api.get('/agent/history', { params: { limit } })
}

export default api