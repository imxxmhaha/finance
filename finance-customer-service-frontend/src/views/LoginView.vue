<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const customerNo = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  if (!customerNo.value.trim()) {
    errorMessage.value = '请输入客户号'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    await authStore.login(customerNo.value.trim(), password.value.trim() || customerNo.value.trim())
    router.push('/')
  } catch (error) {
    errorMessage.value = error.message || '登录失败，请检查客户号'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon">🏦</div>
        <h1>金融客服系统</h1>
        <p class="subtitle">登录后开始智能对话</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="customerNo">客户号</label>
          <input
            id="customerNo"
            v-model="customerNo"
            type="text"
            placeholder="请输入客户号，如：CUS00000001"
            :disabled="isLoading"
            autofocus
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="请输入密码（默认与客户号相同）"
            :disabled="isLoading"
          />
        </div>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <button type="submit" class="login-button" :disabled="isLoading">
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="login-footer">
        <p>演示账号：CUS00000001 ~ CUS00000010</p>
        <p>密码与客户号相同</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(165deg, #070a14 0%, #0c1024 25%, #0a0f1f 50%, #0c1024 75%, #080d1c 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: rgba(14, 16, 30, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  padding: 48px 40px;
  backdrop-filter: blur(32px);
  box-shadow: 0 20px 56px rgba(0, 0, 0, 0.4), 0 0 60px rgba(59, 130, 246, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.login-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #f0ede6, #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  margin: 0;
  color: #9b9790;
  font-size: 15px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  font-weight: 500;
  color: #9b9790;
}

.form-group input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  background: rgba(10, 12, 22, 0.6);
  color: #e6e3dc;
  font-size: 15px;
  transition: all 0.25s ease;
}

.form-group input::placeholder {
  color: #726f68;
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-group input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  margin: 0;
  padding: 10px 14px;
  background: rgba(251, 113, 133, 0.1);
  border: 1px solid rgba(251, 113, 133, 0.2);
  border-radius: 12px;
  color: #fb7185;
  font-size: 13px;
}

.login-button {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 16px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.3);
}

.login-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 16px 32px rgba(59, 130, 246, 0.4);
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.login-footer {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  text-align: center;
}

.login-footer p {
  margin: 4px 0;
  font-size: 12px;
  color: #726f68;
}
</style>
