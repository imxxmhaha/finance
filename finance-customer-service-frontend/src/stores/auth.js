import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const customerNo = ref(localStorage.getItem('customerNo') || '')
  const customerName = ref(localStorage.getItem('customerName') || '')

  const isAuthenticated = computed(() => !!token.value)

  async function login(no, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_no: no, password }),
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.message || '登录失败')
    }

    token.value = data.token
    customerNo.value = data.customer_no
    customerName.value = data.customer_name || data.customer_no

    localStorage.setItem('token', data.token)
    localStorage.setItem('customerNo', data.customer_no)
    localStorage.setItem('customerName', data.customer_name || data.customer_no)
  }

  function logout() {
    token.value = ''
    customerNo.value = ''
    customerName.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('customerNo')
    localStorage.removeItem('customerName')
  }

  function getAuthHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token.value}`,
      'X-Channel-Code': 'ONLINE_BANK',
    }
  }

  return {
    token,
    customerNo,
    customerName,
    isAuthenticated,
    login,
    logout,
    getAuthHeaders,
  }
})
