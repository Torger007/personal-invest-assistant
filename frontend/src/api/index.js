import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 120000  // 2分钟超时，Agent 分析可能需要较长时间
})

function getCookie(name) {
  const prefix = `${name}=`
  return document.cookie.split('; ').find(row => row.startsWith(prefix))?.slice(prefix.length)
}

api.interceptors.request.use(config => {
  if (!['get', 'head', 'options'].includes((config.method || 'get').toLowerCase())) {
    const csrf = getCookie('invest_csrf')
    if (csrf) config.headers['X-CSRF-Token'] = csrf
  }
  return config
})

export const authApi = {
  login: (username, password) => api.post('/auth/login', { username, password }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me')
}

// 市场相关
export const marketApi = {
  getOverview: () => api.get('/market/overview'),
  getIndexDetail: (code, days = 30) => api.get(`/market/index/${code}`, { params: { days } }),
  getFundFlow: (days = 30) => api.get('/market/fund-flow', { params: { days } }),
  getSectors: (sectorType = 'concept', limit = 50) =>
    api.get('/market/sectors', { params: { sector_type: sectorType, limit } }),
  getSectorHist: (name, days = 30) =>
    api.get(`/market/sectors/${encodeURIComponent(name)}/hist`, { params: { days } }),
  getSectorTrend: (sectorType = 'concept', limit = 50) =>
    api.get('/market/sectors/trend', { params: { sector_type: sectorType, limit } })
}

// 基金相关
export const fundApi = {
  getList: () => api.get('/funds/'),
  getDetail: (code) => api.get(`/funds/${code}`),
  getNav: (code, days = 30) => api.get(`/funds/${code}/nav`, { params: { days } }),
  refresh: (code, days = 90) => api.post(`/funds/${code}/refresh`, null, { params: { days } })
}

// 建议相关
export const adviceApi = {
  getList: () => api.get('/advice/'),
  getFundAdvice: (code) => api.get(`/advice/${code}`),
  getPortfolio: () => api.get('/advice/portfolio'),
  getHistory: (code, limit = 30) => api.get(`/advice/history/${code}`, { params: { limit } }),
  getCompare: () => api.get('/advice/compare'),
  generate: () => api.post('/advice/generate')
}

// 任务相关
export const taskApi = {
  refresh: () => api.post('/tasks/refresh'),
  getStatus: () => api.get('/tasks/status')
}

// Agent 相关
export const agentApi = {
  triggerAnalysis: () => api.post('/agent/analyze'),
  getAnalysisTask: (taskId) => api.get(`/agent/analyze/${taskId}`),
  getHistory: (limit = 10) => api.get('/agent/history', { params: { limit } }),
  chatStream: (question, conversationId, onEvent) => {
    if (typeof conversationId === 'function') {
      onEvent = conversationId
      conversationId = null
    }
    return readSseResponse('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCookie('invest_csrf') || '' },
      credentials: 'include',
      body: JSON.stringify({ question, conversation_id: conversationId || null })
    }, onEvent)
  },
  createConversation: () => api.post('/agent/conversations'),
  getConversations: (limit = 30) => api.get('/agent/conversations', { params: { limit } }),
  getConversation: (conversationId) => api.get(`/agent/conversations/${conversationId}`),
  archiveConversation: (conversationId) => api.post(`/agent/conversations/${conversationId}/archive`),
  getReport: (analysisId) => api.get(`/agent/reports/${analysisId}`),
  subscribeAnalysis: (taskId, onEvent) => subscribeSse(`/api/agent/analyze/${taskId}/events`, onEvent)
}

async function readSseResponse(url, options, onEvent) {
  const response = await fetch(url, options)
  if (!response.ok || !response.body) {
    throw new Error(`请求失败 (${response.status})`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''
    frames.forEach(frame => {
      const dataLine = frame.split('\n').find(line => line.startsWith('data: '))
      if (dataLine) onEvent(JSON.parse(dataLine.slice(6)))
    })
    if (done) break
  }
}

function subscribeSse(url, onEvent) {
  const source = new EventSource(url)
  source.onmessage = event => onEvent(JSON.parse(event.data), source)
  return source
}

export default api
