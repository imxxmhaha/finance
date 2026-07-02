<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { fetchChatHistory } from '../utils/api'

const router = useRouter()
const authStore = useAuthStore()

const sessions = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const selectedSession = ref(null)
const sessionMessages = ref([])

// 获取会话列表
async function loadSessions() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const data = await fetchChatHistory(authStore.customerNo)
    const messages = data.messages || []

    // 按 session_id 分组
    const sessionMap = new Map()
    for (const msg of messages) {
      const sid = msg.session_id || 'default'
      if (!sessionMap.has(sid)) {
        sessionMap.set(sid, {
          session_id: sid,
          messages: [],
          started_at: null,
          last_message: '',
        })
      }
      const session = sessionMap.get(sid)
      session.messages.push(msg)
      session.last_message = msg.text || (msg.object ? `[${msg.object.type}]` : '')
    }

    sessions.value = Array.from(sessionMap.values()).reverse()
  } catch (error) {
    errorMessage.value = error.message || '加载历史对话失败'
  } finally {
    isLoading.value = false
  }
}

// 查看会话详情
function viewSession(session) {
  selectedSession.value = session
  sessionMessages.value = session.messages
}

// 返回列表
function backToList() {
  selectedSession.value = null
  sessionMessages.value = []
}

// 继续对话
function continueChat(session) {
  // 存储会话信息到本地，聊天页面可以读取
  localStorage.setItem('continueSessionId', session.session_id)
  router.push('/')
}

// 格式化时间
function formatTime(text) {
  if (!text) return ''
  return text.length > 50 ? text.substring(0, 50) + '...' : text
}

onMounted(() => {
  loadSessions()
})
</script>

<template>
  <div class="history-page">
    <header class="history-header">
      <div class="header-left">
        <button class="back-button" @click="router.push('/')">
          ← 返回聊天
        </button>
        <h1>历史对话</h1>
      </div>
      <div class="header-right">
        <span class="user-info">{{ authStore.customerName || authStore.customerNo }}</span>
        <button class="logout-button" @click="authStore.logout(); router.push('/login')">退出</button>
      </div>
    </header>

    <main class="history-content">
      <!-- 会话列表 -->
      <div v-if="!selectedSession" class="session-list">
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="errorMessage" class="error-state">
          <p>{{ errorMessage }}</p>
          <button @click="loadSessions">重试</button>
        </div>

        <div v-else-if="sessions.length === 0" class="empty-state">
          <div class="empty-icon">💬</div>
          <p>暂无历史对话</p>
          <button @click="router.push('/')">开始新对话</button>
        </div>

        <div v-else class="sessions">
          <div
            v-for="(session, index) in sessions"
            :key="session.session_id"
            class="session-card"
            @click="viewSession(session)"
          >
            <div class="session-header">
              <span class="session-number">对话 #{{ sessions.length - index }}</span>
              <span class="message-count">{{ session.messages.length }} 条消息</span>
            </div>
            <div class="session-preview">
              {{ formatTime(session.last_message) || '空对话' }}
            </div>
            <div class="session-actions">
              <button class="continue-btn" @click.stop="continueChat(session)">继续对话</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 会话详情 -->
      <div v-else class="session-detail">
        <div class="detail-header">
          <button class="back-btn" @click="backToList">← 返回列表</button>
          <h2>对话详情</h2>
          <button class="continue-btn" @click="continueChat(selectedSession)">继续对话</button>
        </div>

        <div class="messages-list">
          <div
            v-for="(msg, index) in sessionMessages"
            :key="index"
            class="message-item"
            :class="msg.role"
          >
            <div class="message-role">{{ msg.role === 'user' ? '用户' : '客服' }}</div>
            <div class="message-content">
              <template v-if="msg.text">{{ msg.text }}</template>
              <template v-else-if="msg.object">
                <div class="object-card">
                  <span class="object-type">{{ msg.object.type }}</span>
                  <span class="object-id">{{ msg.object.id }}</span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.history-page {
  min-height: 100vh;
  background: linear-gradient(165deg, #070a14 0%, #0c1024 25%, #0a0f1f 50%, #0c1024 75%, #080d1c 100%);
  color: #e6e3dc;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 32px;
  background: rgba(14, 16, 30, 0.9);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(20px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  background: linear-gradient(135deg, #f0ede6, #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.back-button, .logout-button {
  padding: 8px 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  color: #9b9790;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.back-button:hover, .logout-button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #e6e3dc;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  font-size: 14px;
  color: #9b9790;
}

.history-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px;
}

/* 加载状态 */
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #9b9790;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 错误状态 */
.error-state {
  text-align: center;
  padding: 60px 20px;
  color: #fb7185;
}

.error-state button {
  margin-top: 16px;
  padding: 10px 24px;
  border: 1px solid rgba(251, 113, 133, 0.3);
  border-radius: 12px;
  background: rgba(251, 113, 133, 0.1);
  color: #fb7185;
  cursor: pointer;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  color: #9b9790;
  margin-bottom: 24px;
}

.empty-state button {
  padding: 12px 28px;
  border: none;
  border-radius: 16px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

/* 会话卡片 */
.sessions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.session-card {
  padding: 20px 24px;
  background: rgba(14, 16, 30, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.session-card:hover {
  background: rgba(20, 22, 38, 0.9);
  border-color: rgba(59, 130, 246, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.session-number {
  font-size: 15px;
  font-weight: 600;
  color: #e6e3dc;
}

.message-count {
  font-size: 12px;
  color: #726f68;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
}

.session-preview {
  font-size: 14px;
  color: #9b9790;
  line-height: 1.5;
  margin-bottom: 12px;
}

.session-actions {
  display: flex;
  justify-content: flex-end;
}

.continue-btn {
  padding: 8px 16px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
}

.continue-btn:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.4);
}

/* 会话详情 */
.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.detail-header h2 {
  margin: 0;
  flex: 1;
  font-size: 20px;
  font-weight: 600;
  color: #e6e3dc;
}

.back-btn {
  padding: 8px 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #9b9790;
  font-size: 13px;
  cursor: pointer;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #e6e3dc;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-item {
  padding: 16px 20px;
  border-radius: 16px;
  max-width: 80%;
}

.message-item.user {
  align-self: flex-end;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #ffffff;
}

.message-item.bot {
  align-self: flex-start;
  background: rgba(14, 16, 30, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #e6e3dc;
}

.message-role {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
  opacity: 0.7;
}

.message-content {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.object-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

.object-type {
  font-size: 12px;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.object-id {
  font-size: 13px;
}
</style>
