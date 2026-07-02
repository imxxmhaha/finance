import { useAuthStore } from '../stores/auth'

// 封装 fetch 请求，自动添加认证头
export async function apiFetch(url, options = {}) {
  const authStore = useAuthStore()

  const headers = {
    ...authStore.getAuthHeaders(),
    ...options.headers,
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  // 如果返回 401，清除登录状态
  if (response.status === 401) {
    authStore.logout()
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }

  return response
}

// 聊天 API
export async function sendMessage(senderId, payload) {
  const response = await apiFetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      sender_id: senderId,
      ...payload,
    }),
  })
  return response.json()
}

// 获取聊天历史
export async function fetchChatHistory(senderId) {
  const response = await apiFetch(`/api/chat/history?sender_id=${encodeURIComponent(senderId)}`)
  return response.json()
}

// 获取会话列表
export async function fetchSessions(senderId) {
  const response = await apiFetch(`/api/chat/history/sessions?sender_id=${encodeURIComponent(senderId)}`)
  return response.json()
}

// 获取账户列表
export async function fetchAccounts(customerNo) {
  const response = await apiFetch(`/finance/api/v1/customers/${encodeURIComponent(customerNo)}/accounts`)
  return response.json()
}

// 获取理财产品
export async function fetchWealthProducts() {
  const response = await apiFetch('/finance/api/v1/wealth/products')
  return response.json()
}

// 获取贷款产品
export async function fetchLoanProducts() {
  const response = await apiFetch('/finance/api/v1/loan/products')
  return response.json()
}

// 知识库检索
export async function searchKnowledge(query, topK = 5, sourceType = null) {
  const body = { query, top_k: topK }
  if (sourceType) body.source_type = sourceType
  const response = await apiFetch('/api/knowledge/search', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return response.json()
}

// 知识库统计
export async function fetchKnowledgeStats() {
  const response = await apiFetch('/api/knowledge/stats')
  return response.json()
}
