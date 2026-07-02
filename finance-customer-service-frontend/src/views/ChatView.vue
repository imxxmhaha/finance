<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { sendMessage, fetchAccounts, fetchWealthProducts, fetchLoanProducts } from '../utils/api'

const router = useRouter()
const authStore = useAuthStore()

const senderId = ref(authStore.customerNo)
const draftMessage = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const messages = ref([])
const messagesContainer = ref(null)

// 侧边栏数据
const accounts = ref([])
const wealthProducts = ref([])
const loanProducts = ref([])
const isLoadingSidebar = ref(false)
const sidebarError = ref('')
const activeTab = ref('accounts')

// 历史对话状态
const sessions = ref([])
const isLoadingSessions = ref(false)
const sessionsError = ref('')
const selectedSession = ref(null)
const currentSessionId = ref('')

// TTS state
const ttsState = ref({})
let currentAudio = null

// Copy state
const copyState = ref({})

// ── Canvas 粒子背景系统 ──────────────────────────────────────────────
const bgCanvas = ref(null)
let animFrameId = null
let bgParticles = []
const BG_PARTICLE_COUNT = 80
const BG_CONNECT_DIST = 150
const BG_MOUSE_RADIUS = 180
const bgMouse = { x: null, y: null }

function createBgParticles(w, h) {
  const palette = [
    [59, 130, 246], [99, 102, 241], [245, 158, 11],
    [217, 119, 6], [16, 185, 129], [52, 211, 153],
  ]
  bgParticles = Array.from({ length: BG_PARTICLE_COUNT }, () => {
    const color = palette[Math.floor(Math.random() * palette.length)]
    return {
      x: Math.random() * w, y: Math.random() * h,
      size: Math.random() * 2.5 + 1,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      color, opacity: Math.random() * 0.45 + 0.12,
      phase: Math.random() * Math.PI * 2,
      pulse: Math.random() * 0.015 + 0.005,
    }
  })
}

function animateBg(ctx, w, h, time) {
  ctx.clearRect(0, 0, w, h)

  for (const p of bgParticles) {
    p.x += p.vx + Math.sin(time * 0.001 + p.phase) * 0.25
    p.y += p.vy + Math.cos(time * 0.001 + p.phase + 1) * 0.25

    if (bgMouse.x !== null) {
      const dx = p.x - bgMouse.x, dy = p.y - bgMouse.y
      const dist = Math.hypot(dx, dy)
      if (dist < BG_MOUSE_RADIUS) {
        const force = (BG_MOUSE_RADIUS - dist) / BG_MOUSE_RADIUS
        p.x += (dx / dist) * force * 0.7
        p.y += (dy / dist) * force * 0.7
      }
    }

    if (p.x < -20) p.x = w + 20; if (p.x > w + 20) p.x = -20
    if (p.y < -20) p.y = h + 20; if (p.y > h + 20) p.y = -20
  }

  // 连线
  ctx.lineWidth = 0.5
  for (let i = 0; i < bgParticles.length; i++) {
    for (let j = i + 1; j < bgParticles.length; j++) {
      const dx = bgParticles[i].x - bgParticles[j].x
      const dy = bgParticles[i].y - bgParticles[j].y
      const dist = Math.hypot(dx, dy)
      if (dist < BG_CONNECT_DIST) {
        const alpha = (1 - dist / BG_CONNECT_DIST) * 0.1
        ctx.strokeStyle = `rgba(59,130,246,${alpha})`
        ctx.beginPath()
        ctx.moveTo(bgParticles[i].x, bgParticles[i].y)
        ctx.lineTo(bgParticles[j].x, bgParticles[j].y)
        ctx.stroke()
      }
    }
  }

  // 粒子光晕
  for (const p of bgParticles) {
    const pulse = 1 + Math.sin(time * p.pulse + p.phase) * 0.25
    const r = p.size * pulse
    const [cr, cg, cb] = p.color

    ctx.beginPath()
    ctx.arc(p.x, p.y, r * 2.5, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.opacity * 0.08})`
    ctx.fill()

    ctx.beginPath()
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.opacity * 0.7})`
    ctx.fill()
  }
}

function initBg() {
  const canvas = bgCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')

  const resize = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
    createBgParticles(canvas.width, canvas.height)
  }
  resize()
  window.addEventListener('resize', resize)

  const onMouseMove = (e) => { bgMouse.x = e.clientX; bgMouse.y = e.clientY }
  const onMouseLeave = () => { bgMouse.x = null; bgMouse.y = null }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseleave', onMouseLeave)

  const loop = (time) => {
    animateBg(ctx, canvas.width, canvas.height, time)
    animFrameId = requestAnimationFrame(loop)
  }
  animFrameId = requestAnimationFrame(loop)

  canvas._cleanup = () => {
    cancelAnimationFrame(animFrameId)
    window.removeEventListener('resize', resize)
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseleave', onMouseLeave)
  }
}
// ── 粒子背景系统结束 ──────────────────────────────────────────────────

// 客服数字人配置
const customerService = {
  name: '小金',
  title: '金牌客服',
  avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=finance&backgroundColor=b6e3f4',
  status: '在线'
}

// 用户配置
const userProfile = {
  name: '你',
  avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=user&backgroundColor=c0aede'
}

// 将消息分组为 Turn 结构
const turns = computed(() => {
  const result = []
  let currentTurn = null
  let turnIndex = 0

  for (const message of messages.value) {
    if (message.type === 'divider') {
      if (currentTurn) {
        result.push(currentTurn)
        currentTurn = null
      }
      result.push({
        type: 'divider',
        text: message.text
      })
      continue
    }

    if (message.role === 'user') {
      if (currentTurn) {
        result.push(currentTurn)
      }
      turnIndex++
      currentTurn = {
        type: 'turn',
        id: `turn-${turnIndex}`,
        index: turnIndex,
        userMessage: message,
        botMessages: []
      }
    } else if (message.role === 'bot') {
      if (!currentTurn) {
        turnIndex++
        currentTurn = {
          type: 'turn',
          id: `turn-${turnIndex}`,
          index: turnIndex,
          userMessage: null,
          botMessages: []
        }
      }
      currentTurn.botMessages.push(message)
    }
  }

  if (currentTurn) {
    result.push(currentTurn)
  }

  return result
})

const chatEndpoint = computed(() => '/api/chat')
const chatHistoryEndpoint = computed(
  () => `/api/chat/history?sender_id=${encodeURIComponent(senderId.value.trim())}`
)
const financeAccountsEndpoint = computed(
  () => `/finance/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/accounts`
)
const financeWealthEndpoint = computed(
  () => '/finance/api/v1/wealth/products'
)
const financeLoanEndpoint = computed(
  () => '/finance/api/v1/loan/products'
)

// 金融 API 请求头（携带认证信息）
function financeHeaders() {
  const id = senderId.value.trim()
  return {
    'Content-Type': 'application/json',
    'X-Channel-Code': 'ONLINE_BANK',
    'Authorization': `Bearer ${id}`,
  }
}

function createBaseMessage(role) {
  return {
    id: crypto.randomUUID(),
    role,
    buttons: [],
  }
}

function appendUserText(text) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'text',
    text,
  })
}

function appendUserObject(objectType, payload) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'object',
    objectType,
    payload,
  })
}

function appendBotMessages(botMessages) {
  for (const message of botMessages) {
    appendMessage('bot', message)
  }
}

function appendMessage(role, message) {
  if (role === 'divider') {
    messages.value.push({
      ...createBaseMessage('divider'),
      type: 'divider',
      text: message.text ?? '以上为历史消息',
    })
    return
  }

  if (message.object) {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'object',
      objectType: message.object.type,
      payload: message.object,
    })
  } else {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'text',
      text: message.text ?? '',
      suggestions: message.suggestions ?? null,
    })
  }
}

function setHistoryMessages(historyMessages) {
  messages.value = []
  for (const message of historyMessages) {
    const role = ['user', 'bot', 'divider'].includes(message.role) ? message.role : 'bot'
    appendMessage(role, message)
  }
}

async function scrollToBottom() {
  await nextTick()
  const container = messagesContainer.value
  if (!container) {
    return
  }
  container.scrollTop = container.scrollHeight
}

watch(
  () => messages.value.length,
  async () => {
    await scrollToBottom()
  }
)

// 新对话
async function resetConversation() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) return

  // 为当前对话生成概要标题（如果有消息）
  if (messages.value.length > 0 && currentSessionId.value) {
    const session = sessions.value.find(s => s.session_id === currentSessionId.value)
    if (session && session.title === '新对话') {
      const title = await generateSummary(messages.value)
      session.title = title
    }
  }

  let newSessionId = 'local_' + Date.now()

  try {
    // 调用后端接口创建新会话
    const response = await fetch('/api/chat/new-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender_id: currentSenderId }),
    })

    if (response.ok) {
      const data = await response.json()
      newSessionId = data.session_id || newSessionId
    }
  } catch (error) {
    console.error('创建新会话失败:', error)
  }

  // 立即在侧边栏添加新会话记录
  const newSession = {
    session_id: newSessionId,
    messages: [],
    last_message: '',
    title: '新对话',
    message_count: 0,
  }
  sessions.value.unshift(newSession)

  // 设置当前会话ID
  currentSessionId.value = newSessionId

  // 清空当前对话
  messages.value = []
  errorMessage.value = ''
  selectedSession.value = null
}

function formatAmount(amount) {
  const numericAmount = Number(amount)
  if (Number.isNaN(numericAmount)) {
    return '￥0.00'
  }
  return `￥${numericAmount.toFixed(2)}`
}

// 账户状态样式
const ACCOUNT_STATUS_CLASS = {
  '正常': 'status-success',
  '活跃': 'status-success',
  '冻结': 'status-warning',
  '部分冻结': 'status-warning',
  '挂失': 'status-danger',
  '销户': 'status-muted',
  '睡眠': 'status-muted',
}

// 理财产品状态样式
const WEALTH_STATUS_CLASS = {
  'selling': 'status-success',
  'active': 'status-success',
  'paused': 'status-warning',
  'closed': 'status-muted',
  'terminated': 'status-danger',
}

// 贷款状态样式
const LOAN_STATUS_CLASS = {
  '正常': 'status-success',
  '逾期': 'status-danger',
  '已结清': 'status-muted',
  '审批中': 'status-info',
  '已放款': 'status-success',
  '待放款': 'status-warning',
}

function getAccountStatusClass(status) {
  return ACCOUNT_STATUS_CLASS[status] || 'status-muted'
}

function getWealthStatusClass(status) {
  return WEALTH_STATUS_CLASS[status] || 'status-muted'
}

function getLoanStatusClass(status) {
  return LOAN_STATUS_CLASS[status] || 'status-muted'
}

function getObjectTitle(message) {
  const payload = message.payload ?? {}
  if (payload.title) {
    return payload.title
  }
  if (message.objectType === 'account') {
    return payload.account_product?.product_name || payload.account_name || '银行账户'
  }
  if (message.objectType === 'wealth_product') return payload.product_name || '理财产品'
  if (message.objectType === 'loan_product') return payload.product_code || '贷款产品'
  return '业务对象'
}

function getObjectIdentifier(message) {
  const payload = message.payload ?? {}
  const id = payload.account_no ?? payload.product_code ?? payload.id
  const label = message.objectType === 'account' ? '账户号' : '产品编号'
  return id ? `${label}：${id}` : label
}

function getObjectSummary(message) {
  const payload = message.payload ?? {}
  if (message.objectType === 'account') {
    const balance = payload.balance_amount ?? payload.attributes?.balance_amount
    const currency = payload.currency_code ?? payload.attributes?.currency_code ?? 'CNY'
    return balance ? `余额：${balance} ${currency}` : '银行账户'
  }
  if (message.objectType === 'wealth_product') {
    const risk = payload.risk_level ?? payload.attributes?.risk_level
    return risk ? `风险等级：${risk}` : '理财产品'
  }
  if (message.objectType === 'loan_product') {
    const rateRange = payload.rate_range ?? payload.attributes?.rate_range
    if (rateRange) {
      return `利率：${(parseFloat(rateRange.min) * 100).toFixed(1)}%~${(parseFloat(rateRange.max) * 100).toFixed(1)}%`
    }
    return '贷款产品'
  }
  return '业务信息'
}

function getObjectAmount(message) {
  const payload = message.payload ?? {}
  if (message.objectType === 'account') {
    const balance = payload.balance_amount ?? payload.available_balance ?? payload.attributes?.balance_amount
    return formatAmount(balance)
  }
  if (message.objectType === 'wealth_product') {
    const yieldRate = payload.expected_yield_rate ?? payload.attributes?.expected_yield_rate
    return yieldRate ? `年化 ${(parseFloat(yieldRate) * 100).toFixed(2)}%` : '—'
  }
  if (message.objectType === 'loan_product') {
    const termRange = payload.term_range ?? payload.attributes?.term_range
    return termRange ? `${termRange.min}~${termRange.max} 期` : '—'
  }
  return '—'
}

async function fetchSidebarData() {
  const currentSenderId = senderId.value.trim()
  accounts.value = []
  wealthProducts.value = []
  loanProducts.value = []
  sidebarError.value = ''

  if (!currentSenderId) {
    return
  }

  isLoadingSidebar.value = true
  try {
    const headers = financeHeaders()
    const [accountsRes, wealthRes, loanRes] = await Promise.all([
      fetch(financeAccountsEndpoint.value, { headers }),
      fetch(financeWealthEndpoint.value, { headers }),
      fetch(financeLoanEndpoint.value, { headers }),
    ])

    const [accountsData, wealthData, loanData] = await Promise.all([
      accountsRes.json(),
      wealthRes.json(),
      loanRes.json(),
    ])

    // 后端错误格式: { code: "ERROR_CODE", message: "错误信息" }
    if (!accountsRes.ok || (accountsData.code && accountsData.code !== 0)) {
      throw new Error(accountsData.message || accountsData.detail || '加载账户列表失败。')
    }
    if (!wealthRes.ok || (wealthData.code && wealthData.code !== 0)) {
      throw new Error(wealthData.message || wealthData.detail || '加载理财产品失败。')
    }
    if (!loanRes.ok || (loanData.code && loanData.code !== 0)) {
      throw new Error(loanData.message || loanData.detail || '加载贷款产品失败。')
    }

    // 后端返回格式: { code: 0, data: { list: [...] } } 或 { code: 0, data: [...] }
    const extractList = (resp) => {
      if (Array.isArray(resp?.data?.list)) return resp.data.list
      if (Array.isArray(resp?.data)) return resp.data
      if (Array.isArray(resp)) return resp
      return []
    }
    accounts.value = extractList(accountsData)
    wealthProducts.value = extractList(wealthData)
    loanProducts.value = extractList(loanData)
  } catch (error) {
    sidebarError.value = error instanceof Error ? error.message : '加载右侧列表失败。'
  } finally {
    isLoadingSidebar.value = false
  }
}

// 加载会话列表
async function loadSessions() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) return

  isLoadingSessions.value = true
  sessionsError.value = ''
  selectedSession.value = null

  try {
    const response = await fetch(`/api/chat/history?sender_id=${encodeURIComponent(currentSenderId)}`)
    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || '加载历史对话失败')
    }

    const messages = data.messages || []

    // 按 session_id 分组
    const sessionMap = new Map()
    for (const msg of messages) {
      const sid = msg.session_id || 'default'
      if (!sessionMap.has(sid)) {
        sessionMap.set(sid, {
          session_id: sid,
          messages: [],
          last_message: '',
          title: '新对话',
        })
      }
      const session = sessionMap.get(sid)
      session.messages.push(msg)
      if (msg.text) {
        session.last_message = msg.text.length > 50 ? msg.text.substring(0, 50) + '...' : msg.text
      }
    }

    // 为每个会话生成标题
    const sessionsList = Array.from(sessionMap.values()).reverse()
    for (const session of sessionsList) {
      if (session.messages.length > 0) {
        const title = await generateSummary(session.messages)
        session.title = title
      }
    }

    sessions.value = sessionsList
  } catch (error) {
    sessionsError.value = error instanceof Error ? error.message : '加载历史对话失败'
  } finally {
    isLoadingSessions.value = false
  }
}

// 查看会话详情 - 将历史消息加载到主对话框
function viewSession(session) {
  selectedSession.value = null
  messages.value = []
  currentSessionId.value = session.session_id

  for (const msg of session.messages) {
    const role = msg.role === 'user' ? 'user' : 'bot'
    if (msg.text) {
      messages.value.push({
        id: crypto.randomUUID(),
        role,
        type: 'text',
        text: msg.text,
        buttons: [],
      })
    } else if (msg.object) {
      messages.value.push({
        id: crypto.randomUUID(),
        role,
        type: 'object',
        objectType: msg.object.type,
        payload: msg.object,
        buttons: [],
      })
    }
  }
}

async function loadChatHistory() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    messages.value = []
    return
  }

  try {
    const response = await fetch(chatHistoryEndpoint.value)
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '加载历史消息失败。')
    }
    if (currentSenderId === senderId.value.trim()) {
      setHistoryMessages(Array.isArray(data?.messages) ? data.messages : [])
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载历史消息失败。'
  }
}

async function sendPayload(payload) {
  if (isSending.value) {
    return
  }

  errorMessage.value = ''
  isSending.value = true

  try {
    const response = await fetch(chatEndpoint.value, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sender_id: senderId.value.trim(),
        ...payload,
      }),
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '请求失败。')
    }

    appendBotMessages(data.messages ?? [])

    // 更新当前会话的最后消息
    updateCurrentSession(data.messages?.[0]?.text || payload.text || '')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '请求失败。'
  } finally {
    isSending.value = false
  }
}

// 更新当前会话在侧边栏的显示
function updateCurrentSession(lastMessage) {
  if (!currentSessionId.value) return

  const session = sessions.value.find(s => s.session_id === currentSessionId.value)
  if (session) {
    session.message_count = messages.value.length
    session.last_message = lastMessage
      ? (lastMessage.length > 30 ? lastMessage.substring(0, 30) + '...' : lastMessage)
      : session.last_message
  }
}

// 生成对话概要标题
async function generateSummary(msgs) {
  try {
    const response = await fetch('/api/chat/summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: msgs.map(m => ({ role: m.role, text: m.text || '' }))
      }),
    })
    const data = await response.json()
    return data.title || '对话'
  } catch {
    return '对话'
  }
}

async function sendSuggestion(text) {
  appendUserText(text)
  await sendPayload({ text })
}

async function sendQuickText(text) {
  draftMessage.value = text
  await sendTextMessage()
}
async function sendTextMessage() {
  const text = draftMessage.value.trim()
  const currentSenderId = senderId.value.trim()

  if (!currentSenderId) {
    errorMessage.value = '请先输入客户号。'
    return
  }
  if (!text) {
    return
  }

  draftMessage.value = ''
  appendUserText(text)
  await sendPayload({ text })
}

async function sendAccount(account) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入客户号。'
    return
  }

  appendUserObject('account', { ...account })
  await sendPayload({
    object: {
      type: 'account',
      id: account.account_no,
      title: account.account_product?.product_name || account.account_name || '银行账户',
      attributes: {
        balance_amount: account.balance_amount,
        currency_code: account.currency_code,
        product_code: account.account_product?.product_code,
      },
    },
  })
}

// 在聊天区域显示对象详情
function showObjectDetail(type, data) {
  let title = ''
  let details = []

  if (type === 'account') {
    title = data.account_product?.product_name || data.account_name || '银行账户'
    details = [
      { label: '账户号', value: data.account_no },
      { label: '余额', value: formatAmount(data.balance_amount ?? data.available_balance) },
      { label: '币种', value: data.currency_code || data.currency || 'CNY' },
      { label: '状态', value: data.account_status || '正常' },
    ]
  } else if (type === 'wealth_product') {
    title = data.product_name || '理财产品'
    details = [
      { label: '产品编号', value: data.product_code },
      { label: '预期年化', value: data.expected_yield_rate ? (parseFloat(data.expected_yield_rate) * 100).toFixed(2) + '%' : '—' },
      { label: '风险等级', value: data.risk_level || '—' },
      { label: '状态', value: data.open_status || '—' },
    ]
  } else if (type === 'loan_product') {
    title = data.product_code || '贷款产品'
    details = [
      { label: '产品编号', value: data.product_code },
      { label: '利率范围', value: data.rate_range ? (parseFloat(data.rate_range.min) * 100).toFixed(1) + '%~' + (parseFloat(data.rate_range.max) * 100).toFixed(1) + '%' : '—' },
      { label: '期限范围', value: data.term_range ? data.term_range.min + '~' + data.term_range.max + '个月' : '—' },
    ]
  }

  // 构建详情文本
  let detailText = `📋 ${title}\n${'─'.repeat(20)}\n`
  for (const item of details) {
    detailText += `${item.label}：${item.value}\n`
  }

  // 添加为系统消息
  messages.value.push({
    id: crypto.randomUUID(),
    role: 'bot',
    type: 'text',
    text: detailText,
    buttons: [],
  })
}

async function sendWealthProduct(product) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入客户号。'
    return
  }

  appendUserObject('wealth_product', { ...product })
  await sendPayload({
    object: {
      type: 'wealth_product',
      id: product.product_code,
      title: product.product_name,
      attributes: {
        risk_level: product.risk_level,
        expected_yield_rate: product.expected_yield_rate,
        open_status: product.open_status,
      },
    },
  })
}

async function sendLoanProduct(product) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入客户号。'
    return
  }

  // 发送贷款申请文本，触发贷款申请流程
  const text = '贷款申请'
  appendUserText(text)
  await sendPayload({ text })
}

watch(
  () => senderId.value.trim(),
  async (value, previousValue) => {
    if (value === previousValue) {
      return
    }

    resetConversation()
    if (!value) {
      accounts.value = []
      wealthProducts.value = []
      loanProducts.value = []
      return
    }
    await Promise.all([fetchSidebarData(), loadChatHistory()])
  }
)

onMounted(async () => {
  initBg()
  await Promise.all([fetchSidebarData(), loadChatHistory(), loadSessions()])
})

onUnmounted(() => {
  if (bgCanvas.value?._cleanup) bgCanvas.value._cleanup()
})

async function playTts(botMsg) {
  const msgId = botMsg.id
  if (!botMsg.text || ttsState.value[msgId] === 'loading') return

  if (currentAudio) { currentAudio.pause(); currentAudio = null }
  for (const key of Object.keys(ttsState.value)) {
    if (ttsState.value[key] === 'playing') ttsState.value[key] = 'idle'
  }

  ttsState.value[msgId] = 'loading'
  try {
    const response = await fetch('/api/chat/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: botMsg.text }),
    })
    if (!response.ok) throw new Error('TTS 请求失败')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    currentAudio = new Audio(url)
    ttsState.value[msgId] = 'playing'
    currentAudio.onended = () => { ttsState.value[msgId] = 'idle'; URL.revokeObjectURL(url); currentAudio = null }
    currentAudio.onerror = () => { ttsState.value[msgId] = 'idle'; URL.revokeObjectURL(url); currentAudio = null }
    await currentAudio.play()
  } catch (error) {
    ttsState.value[msgId] = 'idle'
    console.error('TTS error:', error)
  }
}

async function copyBotText(botMsg) {
  const msgId = botMsg.id
  try {
    await navigator.clipboard.writeText(botMsg.text)
    copyState.value[msgId] = true
    setTimeout(() => { copyState.value[msgId] = false }, 1800)
  } catch (error) {
    console.error('Copy failed:', error)
  }
}
</script>

<template>
  <div class="app-shell">
    <canvas ref="bgCanvas" class="bg-canvas"></canvas>
    <div class="workspace">
      <!-- 左侧历史对话栏 -->
      <aside class="history-sidebar">
        <div class="history-sidebar-header">
          <h2>💬 历史对话</h2>
          <button type="button" class="new-chat-btn" title="新对话" @click="resetConversation">
            +
          </button>
        </div>

        <div class="history-sidebar-content">
          <div v-if="isLoadingSessions" class="history-loading">
            <div class="loading-spinner-small"></div>
            <p>加载中...</p>
          </div>

          <div v-else-if="sessionsError" class="history-error">
            <p>{{ sessionsError }}</p>
            <button class="retry-btn" @click="loadSessions">重试</button>
          </div>

          <div v-else-if="sessions.length === 0" class="history-empty">
            <p>暂无历史对话</p>
            <p class="history-empty-hint">开始新对话后将显示在这里</p>
          </div>

          <div v-else class="history-list">
            <div
              v-for="(session, index) in sessions"
              :key="session.session_id"
              class="history-item"
              :class="{ active: selectedSession?.session_id === session.session_id }"
              @click="viewSession(session)"
            >
              <div class="history-item-icon">💬</div>
              <div class="history-item-content">
                <div class="history-item-title">{{ session.title || '对话 #' + (sessions.length - index) }}</div>
                <div class="history-item-preview">{{ session.last_message || '空对话' }}</div>
              </div>
              <div class="history-item-count">{{ session.messages.length }}</div>
            </div>
          </div>
        </div>
      </aside>

      <div class="chat-card">
        <header class="chat-header">
          <div class="header-content">
            <div class="header-info">
              <h1>金融客服系统</h1>
              <div class="service-info">
                <div class="service-avatar-wrapper">
                  <img :src="customerService.avatar" class="service-avatar" />
                  <span class="status-indicator"></span>
                </div>
                <div class="service-details">
                  <span class="service-name">{{ customerService.name }}</span>
                  <span class="service-status">{{ customerService.status }}</span>
                </div>
              </div>
            </div>
            <div class="header-actions">
              <button type="button" class="clear-button" title="清空对话" @click="resetConversation">
                <span>🔄</span>
                <span>新对话</span>
              </button>
              <button type="button" class="logout-button" title="退出登录" @click="authStore.logout(); router.push('/login')">
                <span>🚪</span>
                <span>{{ authStore.customerName || authStore.customerNo }}</span>
              </button>
            </div>
          </div>
        </header>

        <section class="controls">
          <div class="controls-info">
            <span class="customer-label">当前客户：{{ authStore.customerName || authStore.customerNo }}</span>
            <button
              type="button"
              class="secondary-button"
              :disabled="isLoadingSidebar"
              @click="fetchSidebarData"
            >
              {{ isLoadingSidebar ? '加载中...' : '刷新数据' }}
            </button>
          </div>
        </section>

        <section ref="messagesContainer" class="messages">
          <div v-if="turns.length === 0" class="welcome">
            <div class="welcome-card">
              <div class="welcome-glow"></div>
              <div class="welcome-avatar-wrapper">
                <img :src="customerService.avatar" class="welcome-avatar" alt="小金" />
                <span class="welcome-status-pulse"></span>
              </div>
              <h2 class="welcome-greeting">Hi，我是 {{ customerService.name }}</h2>
              <p class="welcome-subtitle">你的专属金融客服，随时为你服务</p>
              <div class="welcome-chips">
                <button
                  v-for="chip in ['查询账户余额', '理财产品推荐', '贷款申请', '信用卡挂失']"
                  :key="chip"
                  type="button"
                  class="welcome-chip"
                  :disabled="isSending"
                  @click="sendQuickText(chip)"
                >{{ chip }}</button>
              </div>
              <p class="welcome-features">
                <span>💬 文字对话</span>
                <span>🔊 语音播报</span>
                <span>🏦 账户查询</span>
                <span>💰 理财咨询</span>
              </p>
            </div>
          </div>

          <!-- Turn 结构展示 -->
          <template v-for="(item, index) in turns" :key="item.id || index">
            <!-- 分隔线 -->
            <div v-if="item.type === 'divider'" class="history-divider">
              <span>{{ item.text }}</span>
            </div>

            <!-- Turn 卡片 -->
            <div v-else class="turn-card" :class="{ 'has-user-message': item.userMessage }">
              <!-- Turn 标识 -->
              <div class="turn-header">
                <span class="turn-badge">Turn {{ item.index }}</span>
                <span class="turn-label">对话轮次</span>
              </div>

              <!-- 用户消息区域 -->
              <div v-if="item.userMessage" class="turn-section user-section">
                <div class="section-header">
                  <div class="avatar-wrapper user-avatar">
                    <img :src="userProfile.avatar" class="avatar" />
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ userProfile.name }}</span>
                    <span class="agent-label">用户</span>
                  </div>
                </div>
                <div class="turn-bubble user-bubble">
                  <template v-if="item.userMessage.type === 'object'">
                    <div class="object-card" :class="`object-card-${item.userMessage.objectType}`">
                      <div class="object-card-badge">
                        {{ item.userMessage.objectType === 'account' ? '账户对象' : item.userMessage.objectType === 'wealth_product' ? '理财产品' : '贷款产品' }}
                      </div>
                      <div class="object-card-title">{{ getObjectTitle(item.userMessage) }}</div>
                      <div class="object-card-meta">{{ getObjectIdentifier(item.userMessage) }}</div>
                      <div class="object-card-meta">
                        <span>{{ getObjectSummary(item.userMessage) }}</span>
                      </div>
                      <div class="object-card-price">{{ getObjectAmount(item.userMessage) }}</div>
                    </div>
                  </template>
                  <template v-else>
                    <p>{{ item.userMessage.text }}</p>
                  </template>
                </div>
              </div>

              <!-- 客服回复区域 -->
              <div v-if="item.botMessages.length > 0" class="turn-section bot-section">
                <div class="section-header">
                  <div class="avatar-wrapper service-avatar">
                    <img :src="customerService.avatar" class="avatar" />
                    <span class="status-dot"></span>
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ customerService.name }}</span>
                    <span class="agent-label">{{ customerService.title }}</span>
                  </div>
                </div>
                <div class="bot-messages">
                  <div
                    v-for="(botMsg, msgIndex) in item.botMessages"
                    :key="msgIndex"
                    class="turn-bubble bot-bubble"
                  >
                    <template v-if="botMsg.type === 'object'">
                      <div class="object-card" :class="`object-card-${botMsg.objectType}`">
                        <div class="object-card-badge">
                          {{ botMsg.objectType === 'account' ? '账户对象' : botMsg.objectType === 'wealth_product' ? '理财产品' : '贷款产品' }}
                        </div>
                        <div class="object-card-title">{{ getObjectTitle(botMsg) }}</div>
                        <div class="object-card-meta">{{ getObjectIdentifier(botMsg) }}</div>
                        <div class="object-card-meta">
                          <span>{{ getObjectSummary(botMsg) }}</span>
                        </div>
                        <div class="object-card-price">{{ getObjectAmount(botMsg) }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="bot-text-row">
                        <p>{{ botMsg.text }}</p>
                        <div class="bot-actions">
                          <button type="button" class="tts-button"
                            :class="{ 'tts-loading': ttsState[botMsg.id] === 'loading', 'tts-playing': ttsState[botMsg.id] === 'playing' }"
                            :disabled="ttsState[botMsg.id] === 'loading'"
                            :title="ttsState[botMsg.id] === 'playing' ? '正在播放...' : '语音播报'"
                            @click.stop="playTts(botMsg)">
                            <span v-if="ttsState[botMsg.id] === 'loading'" class="tts-spinner"></span>
                            <span v-else-if="ttsState[botMsg.id] === 'playing'" class="tts-bars">
                              <span></span><span></span><span></span>
                            </span>
                            <span v-else>🔈</span>
                          </button>
                          <button type="button" class="copy-button"
                            :class="{ 'copy-done': copyState[botMsg.id] }"
                            :title="copyState[botMsg.id] ? '已复制' : '复制文字'"
                            @click.stop="copyBotText(botMsg)">
                            <span v-if="copyState[botMsg.id]">✓</span>
                            <span v-else>📋</span>
                          </button>
                        </div>
                      </div>
                    </template>
                    <div v-if="botMsg.suggestions && botMsg.suggestions.length > 0" class="suggestion-chips">
                      <button
                        v-for="sug in botMsg.suggestions"
                        :key="sug"
                        type="button"
                        class="suggestion-chip"
                        :disabled="isSending"
                        @click.stop="sendSuggestion(sug)"
                      >{{ sug }}</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </section>

        <div v-if="isSending" class="typing-indicator">
          <div class="typing-avatar">
            <img :src="customerService.avatar" class="avatar-small" alt="小金" />
          </div>
          <div class="typing-bubble">
            <span class="typing-dots">
              <span></span><span></span><span></span>
            </span>
            <span class="typing-label">小金正在输入...</span>
          </div>
        </div>

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <form class="composer" @submit.prevent="sendTextMessage">
          <input
            v-model="draftMessage"
            type="text"
            placeholder="请输入咨询内容..."
            :disabled="isSending"
          />
          <button type="submit" :disabled="isSending || !draftMessage.trim()">
            {{ isSending ? '发送中...' : '发送' }}
          </button>
        </form>
      </div>

      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>业务对象</h2>
        </div>

        <div class="tabs">
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'accounts' }"
            @click="activeTab = 'accounts'"
          >
            账户
          </button>
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'wealth' }"
            @click="activeTab = 'wealth'"
          >
            理财
          </button>
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'loans' }"
            @click="activeTab = 'loans'"
          >
            贷款
          </button>
        </div>

        <p v-if="sidebarError" class="sidebar-error">{{ sidebarError }}</p>

        <!-- 账户列表 -->
        <div v-if="activeTab === 'accounts'" class="sidebar-list">
          <div v-if="!accounts.length && !isLoadingSidebar" class="sidebar-empty">
            暂无账户数据
          </div>

          <article v-for="account in accounts" :key="account.account_no" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ account.account_product?.product_name || account.account_name || '银行账户' }}</div>
              <div class="card-amount">{{ formatAmount(account.balance_amount ?? account.available_balance) }}</div>
            </div>
            <div class="card-meta">账户号：{{ account.account_no }}</div>
            <div class="card-meta">
              <span v-if="account.currency_code" class="card-tag">{{ account.currency_code }}</span>
              <span v-else-if="account.currency" class="card-tag">{{ account.currency }}</span>
            </div>
            <div class="card-actions">
              <button
                type="button"
                class="detail-button"
                @click="showObjectDetail('account', account)"
              >
                查看详情
              </button>
              <button
                type="button"
                class="send-button"
                :disabled="isSending"
                @click="sendAccount(account)"
              >
                发送
              </button>
            </div>
          </article>
        </div>

        <!-- 理财产品列表 -->
        <div v-else-if="activeTab === 'wealth'" class="sidebar-list">
          <div v-if="!wealthProducts.length && !isLoadingSidebar" class="sidebar-empty">
            暂无理财产品数据
          </div>

          <article v-for="product in wealthProducts" :key="product.product_code" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ product.product_name }}</div>
              <div class="card-amount">{{ product.expected_yield_rate ? (parseFloat(product.expected_yield_rate) * 100).toFixed(2) + '%' : '—' }}</div>
            </div>
            <div class="card-meta">产品编号：{{ product.product_code }}</div>
            <div class="card-meta">
              <span class="status-badge" :class="getWealthStatusClass(product.open_status)">{{ product.open_status }}</span>
              <span v-if="product.risk_level" class="card-tag risk-tag">{{ product.risk_level }}</span>
            </div>
            <div class="card-actions">
              <button
                type="button"
                class="detail-button"
                @click="showObjectDetail('wealth_product', product)"
              >
                查看详情
              </button>
              <button
                type="button"
                class="send-button"
                :disabled="isSending"
                @click="sendWealthProduct(product)"
              >
                发送
              </button>
            </div>
          </article>
        </div>

        <!-- 贷款产品列表 -->
        <div v-else class="sidebar-list">
          <div v-if="!loanProducts.length && !isLoadingSidebar" class="sidebar-empty">
            暂无贷款产品数据
          </div>

          <article v-for="product in loanProducts" :key="product.product_code" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ product.product_code }}</div>
              <div class="card-amount">{{ product.rate_range ? (parseFloat(product.rate_range.min) * 100).toFixed(1) + '%~' + (parseFloat(product.rate_range.max) * 100).toFixed(1) + '%' : '—' }}</div>
            </div>
            <div class="card-meta">产品编号：{{ product.product_code }}</div>
            <div v-if="product.term_range" class="card-meta">期限：{{ product.term_range.min }}~{{ product.term_range.max }} 个月</div>
            <div class="card-actions">
              <button
                type="button"
                class="detail-button"
                @click="showObjectDetail('loan_product', product)"
              >
                查看详情
              </button>
              <button
                type="button"
                class="send-button"
                :disabled="isSending"
                @click="sendLoanProduct(product)"
              >
                发送
              </button>
            </div>
          </article>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300..700&family=Zen+Maru+Gothic:wght@400;500;700&display=swap');

:global(*) {
  box-sizing: border-box;
}

:global(:root) {
  /* ── Palette ── */
  --color-bg-deep: #070a14;
  --color-bg-mid: #0c1024;
  --color-bg-surface: #11162b;
  --color-surface: rgba(14, 16, 30, 0.78);
  --color-surface-hover: rgba(20, 22, 38, 0.86);
  --color-surface-dim: rgba(14, 16, 30, 0.60);
  --color-surface-raised: rgba(24, 26, 44, 0.70);
  --color-surface-field: rgba(10, 12, 22, 0.62);
  --color-text-primary: #e6e3dc;
  --color-text-secondary: #9b9790;
  --color-text-muted: #726f68;
  --color-text-inverse: #18171c;
  /* Accent — blue (finance) */
  --color-accent: #3b82f6;
  --color-accent-strong: #2563eb;
  --color-accent-soft: rgba(59, 130, 246, 0.10);
  --color-accent-glow: rgba(59, 130, 246, 0.20);
  --color-accent-soft-bg: rgba(59, 130, 246, 0.06);
  /* Warm — amber */
  --color-warm: #f59e0b;
  --color-warm-strong: #d97706;
  --color-warm-soft: rgba(245, 158, 11, 0.10);
  --color-warm-glow: rgba(245, 158, 11, 0.18);
  --color-warm-soft-bg: rgba(245, 158, 11, 0.05);
  /* Semantic */
  --color-success: #34d399;
  --color-success-soft: rgba(52, 211, 153, 0.12);
  --color-info: #38bdf8;
  --color-info-soft: rgba(56, 189, 248, 0.10);
  --color-danger: #fb7185;
  --color-danger-soft: rgba(251, 113, 133, 0.10);
  /* Borders */
  --color-border: rgba(255, 255, 255, 0.08);
  --color-border-light: rgba(255, 255, 255, 0.05);
  --color-border-strong: rgba(255, 255, 255, 0.13);
  /* ── Radii ── */
  --radius-sm: 10px;
  --radius-md: 16px;
  --radius-lg: 24px;
  --radius-xl: 28px;
  --radius-full: 9999px;
  /* ── Shadows ── */
  --shadow-xs: 0 1px 3px rgba(0, 0, 0, 0.18);
  --shadow-sm: 0 4px 14px rgba(0, 0, 0, 0.22);
  --shadow-md: 0 8px 32px rgba(0, 0, 0, 0.28);
  --shadow-lg: 0 20px 56px rgba(0, 0, 0, 0.35);
  --shadow-glow-blue: 0 0 60px rgba(59, 130, 246, 0.10), 0 0 120px rgba(59, 130, 246, 0.04);
  --shadow-glow-amber: 0 0 50px rgba(245, 158, 11, 0.08), 0 0 100px rgba(245, 158, 11, 0.03);
  --shadow-inner-glow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  /* ── Transitions ── */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --duration-fast: 150ms;
  --duration-base: 250ms;
  --duration-slow: 400ms;
}

:global(body) {
  margin: 0;
  font-family: "Outfit", "Zen Maru Gothic", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--color-bg-deep);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:global(button),
:global(input) {
  font: inherit;
}

:global(#app) {
  min-height: 100vh;
}

.app-shell {
  min-height: 100vh;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(165deg, #070a14 0%, #0c1024 25%, #0a0f1f 50%, #0c1024 75%, #080d1c 100%);
  background-size: 400% 400%;
  animation: bgShift 24s ease-in-out infinite;
}
.app-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.028;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.bg-canvas {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.app-shell::after {
  content: "";
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  width: 820px; height: 820px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.18) 0%, rgba(99, 102, 241, 0.06) 35%, transparent 70%);
  top: -320px; left: -280px;
  animation: orb1 20s ease-in-out infinite;
}
.workspace::before {
  content: "";
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  width: 640px; height: 640px;
  background: radial-gradient(circle, rgba(217, 119, 6, 0.13) 0%, rgba(245, 158, 11, 0.05) 40%, transparent 70%);
  bottom: -280px; right: -220px;
  animation: orb2 24s ease-in-out infinite;
}

@keyframes bgShift {
  0%, 100% { background-position: 0% 0%; }
  25% { background-position: 100% 0%; }
  50% { background-position: 100% 100%; }
  75% { background-position: 0% 100%; }
}
@keyframes orb1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(140px, 90px) scale(1.22); }
  66% { transform: translate(-50px, 150px) scale(0.82); }
}
@keyframes orb2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-110px, -70px) scale(1.18); }
  66% { transform: translate(70px, -130px) scale(0.88); }
}

.workspace {
  width: min(1920px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 370px;
  gap: 18px;
  position: relative;
  z-index: 1;
}

.history-sidebar,
.chat-card,
.sidebar {
  min-height: calc(100vh - 48px);
  height: calc(100vh - 48px);
  background: var(--color-surface);
  backdrop-filter: blur(32px) saturate(1.2);
  -webkit-backdrop-filter: blur(32px) saturate(1.2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color var(--duration-slow) var(--ease-in-out), box-shadow var(--duration-slow) var(--ease-in-out);
}
.chat-card {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-glow-blue), var(--shadow-lg), var(--shadow-inner-glow);
}
.chat-card:hover {
  border-color: rgba(59, 130, 246, 0.15);
}
.sidebar {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-glow-amber), var(--shadow-lg), var(--shadow-inner-glow);
}
.sidebar:hover {
  border-color: rgba(245, 158, 11, 0.15);
}

/* 左侧历史对话栏 */
.history-sidebar {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg), var(--shadow-inner-glow);
  overflow: hidden;
  position: relative;
}

.history-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 16px 14px;
  border-bottom: 1px solid var(--color-border-light);
}

.history-sidebar-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.new-chat-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface-raised);
  color: var(--color-accent);
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-base) var(--ease-out-expo);
}

.new-chat-btn:hover {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  transform: scale(1.05);
}

.history-sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.history-loading,
.history-error,
.history-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}

.history-empty-hint {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.7;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
  border: 1px solid transparent;
}

.history-item:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border);
}

.history-item.active {
  background: var(--color-accent-soft);
  border-color: rgba(59, 130, 246, 0.2);
}

.history-item-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.history-item-content {
  flex: 1;
  min-width: 0;
}

.history-item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 2px;
}

.history-item-preview {
  font-size: 11px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-count {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-surface-raised);
  padding: 2px 8px;
  border-radius: 10px;
}

/* 会话详情弹出层 */
.session-detail-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-surface);
  z-index: 10;
  display: flex;
  flex-direction: column;
}

.session-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-header-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.back-btn-small {
  padding: 4px 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 12px;
  cursor: pointer;
}

.back-btn-small:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-primary);
}

.detail-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.close-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-primary);
}

.detail-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-msg {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  max-width: 85%;
}

.detail-msg.user {
  background: var(--color-accent);
  color: #ffffff;
  align-self: flex-end;
  border-bottom-right-radius: 4px;
}

.detail-msg.bot {
  background: var(--color-surface-field);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  align-self: flex-start;
  border-bottom-left-radius: 4px;
}

.detail-msg-role {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
  opacity: 0.7;
}

.detail-msg-text {
  word-break: break-word;
  white-space: pre-wrap;
}

.chat-header,
.sidebar-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.chat-header h1,
.sidebar-header h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #f0ede6 0%, var(--color-accent) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar-header h2 {
  font-size: 22px;
  background: linear-gradient(135deg, #f0ede6 0%, var(--color-warm) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.service-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.service-avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.service-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
  padding: 3px;
  background: conic-gradient(var(--color-success), var(--color-accent), var(--color-warm), var(--color-success));
  animation: avatarSpin 4s linear infinite;
  box-shadow: 0 0 20px var(--color-accent-glow), 0 4px 12px var(--color-success-soft);
}
@keyframes avatarSpin {
  to { transform: rotate(360deg); }
}

.status-indicator {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 14px;
  height: 14px;
  background: var(--color-success);
  border: 3px solid #ffffff;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.service-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.service-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.service-status {
  font-size: 12px;
  color: var(--color-success);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.service-status::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--color-success);
  border-radius: 50%;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-button, .logout-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
  white-space: nowrap;
}

.nav-button:hover {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.logout-button:hover {
  background: rgba(251, 113, 133, 0.1);
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.controls-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.customer-label {
  font-size: 14px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.clear-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
  white-space: nowrap;
}
.clear-button:hover {
  background: rgba(251, 113, 133, 0.10);
  border-color: var(--color-danger);
  color: var(--color-danger);
  transform: translateY(-1px);
  box-shadow: 0 4px 18px var(--color-danger-soft);
}

.controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
}

.field-row {
  display: flex;
  gap: 12px;
}

.field input,
.composer input {
  width: 100%;
  min-width: 0;
  min-height: 46px;
  padding: 11px 14px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-field);
  color: var(--color-text-primary);
  font-size: 15px;
  line-height: 1.4;
  transition: border-color var(--duration-fast) var(--ease-in-out), box-shadow var(--duration-fast) var(--ease-in-out);
}
.field input::placeholder,
.composer input::placeholder {
  color: var(--color-text-muted);
}
.field input:focus,
.composer input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-soft);
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.turn-card {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 24px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--duration-base) var(--ease-out-expo);
  position: relative;
  overflow: hidden;
  animation: msgEnter 0.4s var(--ease-out-back) both;
}
@keyframes msgEnter {
  from { opacity: 0; transform: translateY(24px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.turn-card::before {
  content: "";
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.04) 50%, transparent 60%);
  transition: left 0.5s ease;
  pointer-events: none;
  z-index: 2;
}
.turn-card:hover::before {
  left: 100%;
}
.turn-card:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md), 0 0 40px rgba(59, 130, 246, 0.04);
  transform: translateY(-2px);
}

.turn-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--color-border);
}

.turn-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  background: linear-gradient(135deg, var(--color-accent), #1d4ed8);
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  box-shadow: 0 2px 12px var(--color-accent-glow);
}

.turn-label {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.turn-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  font-weight: 600;
}

.avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #e5e7eb;
  background: #f3f4f6;
  transition: all var(--duration-base) var(--ease-out-expo);
}

.user-avatar .avatar {
  border: 3px solid transparent;
  background: linear-gradient(#ffffff, #ffffff) padding-box,
              linear-gradient(135deg, var(--color-info), var(--color-accent)) border-box;
  box-shadow: 0 2px 14px var(--color-info-soft);
}

.service-avatar .avatar {
  border-color: var(--color-success);
  box-shadow: 0 2px 10px var(--color-success-soft);
}

.status-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 12px;
  height: 12px;
  background: var(--color-success);
  border: 2px solid #ffffff;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.65;
    transform: scale(1.12);
  }
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.agent-label {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.user-section .agent-name {
  color: var(--color-info);
}

.bot-section .agent-name {
  color: var(--color-success);
}

.turn-bubble {
  padding: 14px 18px;
  border-radius: var(--radius-md);
  max-width: 100%;
}

.user-bubble {
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-strong));
  border: 1px solid transparent;
  color: #ffffff;
  box-shadow: 0 4px 18px var(--color-accent-glow);
  margin-left: auto;
  max-width: 85%;
}

.bot-bubble {
  background: var(--color-surface-field);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-xs);
}

.bot-messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.turn-bubble p {
  margin: 0;
  font-size: 15px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.user-bubble p {
  color: #ffffff;
}

.history-divider {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 8px 0;
}

.history-divider::before,
.history-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-border-strong);
}

.history-divider span {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  font-size: 12px;
}

.welcome {
  flex-shrink: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.welcome-card {
  position: relative;
  max-width: 480px;
  width: 100%;
  padding: 44px 40px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-align: center;
  box-shadow: var(--shadow-glow-blue), var(--shadow-lg);
  overflow: hidden;
  animation: welcomeFloat 0.6s var(--ease-out-back);
}
@keyframes welcomeFloat {
  from { opacity: 0; transform: translateY(36px) scale(0.94); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.welcome-glow {
  position: absolute;
  top: -100px; left: 50%; transform: translateX(-50%);
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, rgba(59,130,246,0.02) 45%, transparent 70%);
  pointer-events: none;
}
.welcome-avatar-wrapper {
  position: relative;
  display: inline-block;
  margin-bottom: 20px;
}
.welcome-avatar {
  width: 88px; height: 88px;
  border-radius: 50%;
  padding: 4px;
  background: conic-gradient(var(--color-success), var(--color-accent), var(--color-warm), var(--color-success));
  animation: avatarSpin 4s linear infinite;
  box-shadow: 0 0 36px var(--color-accent-glow);
}
.welcome-status-pulse {
  position: absolute;
  bottom: 6px; right: 6px;
  width: 18px; height: 18px;
  background: var(--color-success);
  border: 3px solid var(--color-bg-mid);
  border-radius: 50%;
  animation: pulse 2s infinite;
  box-shadow: 0 0 16px rgba(52, 211, 153, 0.4);
}
.welcome-greeting {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  background: linear-gradient(135deg, #f0ede6, var(--color-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.welcome-subtitle {
  margin: 0 0 28px;
  color: var(--color-text-secondary);
  font-size: 15px;
}
.welcome-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-bottom: 28px;
}
.welcome-chip {
  padding: 10px 20px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  border-radius: var(--radius-full);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.welcome-chip:hover:not(:disabled) {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--color-accent-glow);
}
.welcome-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.welcome-features {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.sidebar-empty {
  margin: auto;
  max-width: 420px;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.7;
}

.typing-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 0 20px;
  animation: msgEnter 0.3s var(--ease-out-expo);
}
.avatar-small {
  width: 34px; height: 34px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--color-success);
  box-shadow: 0 0 12px rgba(52, 211, 153, 0.25);
}
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: 20px 20px 20px 6px;
  box-shadow: var(--shadow-sm);
}
.typing-dots {
  display: flex;
  gap: 4px;
  align-items: center;
}
.typing-dots span {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: dotBounce 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
  30% { transform: translateY(-8px); opacity: 1; }
}
.typing-label {
  font-size: 13px;
  color: var(--color-text-muted);
}

.object-card-price {
  font-size: 15px;
  font-weight: 600;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.status-warning {
  background: var(--color-warm-soft);
  color: var(--color-warm-strong);
  border: 1px solid rgba(245, 158, 11, 0.25);
}
.status-info {
  background: var(--color-info-soft);
  color: var(--color-info);
  border: 1px solid rgba(56, 189, 248, 0.25);
}
.status-success {
  background: var(--color-success-soft);
  color: var(--color-success);
  border: 1px solid rgba(52, 211, 153, 0.25);
}
.status-muted {
  background: rgba(113, 111, 104, 0.12);
  color: var(--color-text-muted);
  border: 1px solid rgba(113, 111, 104, 0.18);
}
.status-danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border: 1px solid rgba(251, 113, 133, 0.25);
}

.card-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 500;
  background: var(--color-accent-soft);
  color: var(--color-accent);
  border: 1px solid rgba(59, 130, 246, 0.2);
  margin-left: 6px;
}

.risk-tag {
  background: var(--color-warm-soft);
  color: var(--color-warm-strong);
  border-color: rgba(245, 158, 11, 0.2);
}

.composer button,
.secondary-button,
.tab-button {
  min-height: 42px;
  padding: 9px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
  transition:
    transform var(--duration-fast) var(--ease-out-expo),
    box-shadow var(--duration-fast) var(--ease-out-expo),
    background var(--duration-fast) var(--ease-in-out),
    border-color var(--duration-fast) var(--ease-in-out);
}

.composer button:hover:not(:disabled),
.secondary-button:hover:not(:disabled),
.tab-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.composer button:active:not(:disabled),
.secondary-button:active:not(:disabled),
.tab-button:active:not(:disabled) {
  transform: translateY(0);
}

.composer button:disabled,
.secondary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 卡片操作按钮 */
.card-actions {
  display: flex;
  gap: 8px;
}

.detail-button,
.send-button {
  flex: 1;
  min-height: 36px;
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.detail-button {
  background: var(--color-surface);
  color: var(--color-text-secondary);
}

.detail-button:hover {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.send-button {
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-strong));
  border-color: transparent;
  color: #ffffff;
  box-shadow: 0 4px 12px var(--color-accent-glow);
}

.send-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px var(--color-accent-glow);
}

.send-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.error-message,
.sidebar-error {
  margin: 0;
  padding: 0 24px 14px;
  color: var(--color-danger);
  font-size: 13px;
  font-weight: 500;
}

.composer {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid var(--color-border-light);
  background: var(--color-surface-dim);
}

.composer button {
  min-width: 96px;
  padding-inline: 20px;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-strong));
  border-color: transparent;
  color: #f0fdfa;
  box-shadow: 0 14px 28px var(--color-accent-glow);
}
.composer button:hover:not(:disabled) {
  box-shadow: 0 18px 36px var(--color-accent-glow);
  transform: translateY(-2px);
}

.sidebar {
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  gap: 8px;
  padding: 16px 24px 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.tab-button {
  min-width: 72px;
}

.tab-button.active {
  background: linear-gradient(135deg, var(--color-accent-strong), var(--color-accent));
  border-color: transparent;
  color: #f0fdfa;
  box-shadow: 0 4px 14px var(--color-accent-glow);
}

.sidebar-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sidebar-card {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.sidebar-card:hover {
  background: var(--color-surface-hover);
  border-color: rgba(245, 158, 11, 0.18);
  transform: translateY(-3px);
  box-shadow: var(--shadow-md), var(--shadow-glow-amber);
}

.card-top {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: flex-start;
}

.card-title {
  font-size: 15px;
  line-height: 1.5;
  color: var(--color-text-primary);
  font-weight: 600;
}

.card-amount {
  flex-shrink: 0;
  color: var(--color-warm-strong);
  font-weight: 700;
}

.card-meta {
  font-size: 14px;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 历史对话样式 */
.history-card {
  cursor: pointer;
}

.history-preview {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.loading-spinner-small {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(59, 130, 246, 0.2);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  margin: 0 auto 8px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.retry-btn {
  margin-top: 8px;
  padding: 6px 16px;
  border: 1px solid var(--color-accent);
  border-radius: 8px;
  background: var(--color-accent-soft);
  color: var(--color-accent);
  font-size: 13px;
  cursor: pointer;
}

.session-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-header-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light);
  margin-bottom: 12px;
}

.back-btn-small {
  padding: 4px 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 12px;
  cursor: pointer;
}

.back-btn-small:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-primary);
}

.detail-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.detail-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-msg {
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.5;
}

.detail-msg.user {
  background: var(--color-accent);
  color: #ffffff;
  align-self: flex-end;
  max-width: 85%;
}

.detail-msg.bot {
  background: var(--color-surface-field);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  align-self: flex-start;
  max-width: 85%;
}

.detail-msg-role {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
  opacity: 0.7;
}

.detail-msg-text {
  word-break: break-word;
  white-space: pre-wrap;
}

.bot-text-row { display: flex; align-items: flex-start; gap: 8px; }
.bot-text-row p { flex: 1; margin: 0; }
.bot-actions {
  display: flex; gap: 6px; flex-shrink: 0; align-items: center;
}
.tts-button, .copy-button {
  flex-shrink: 0; width: 32px; height: 32px; padding: 0;
  border: 1px solid var(--color-border-light); border-radius: 8px;
  background: var(--color-surface); cursor: pointer;
  font-size: 14px; display: inline-flex; align-items: center; justify-content: center;
  transition: all var(--duration-base) var(--ease-out-expo); color: var(--color-text-muted);
}
.tts-button:hover:not(:disabled), .copy-button:hover:not(:disabled) {
  background: var(--color-accent-soft); border-color: var(--color-accent); color: var(--color-accent-strong);
  transform: scale(1.1);
}
.tts-button:disabled, .copy-button:disabled { cursor: not-allowed; opacity: 0.65; }
.tts-button.tts-playing { background: var(--color-accent-soft); border-color: var(--color-accent); color: var(--color-accent-strong); }
.tts-bars {
  display: inline-flex; align-items: flex-end; gap: 3px; height: 16px;
}
.tts-bars span {
  width: 3px;
  background: var(--color-accent);
  border-radius: 2px;
  animation: barBounce 0.6s ease-in-out infinite;
}
.tts-bars span:nth-child(1) { height: 8px; animation-delay: 0s; }
.tts-bars span:nth-child(2) { height: 14px; animation-delay: 0.15s; }
.tts-bars span:nth-child(3) { height: 10px; animation-delay: 0.3s; }
@keyframes barBounce {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}
.tts-spinner {
  width: 14px; height: 14px;
  border: 2px solid var(--color-accent-soft); border-top-color: var(--color-accent);
  border-radius: 50%; animation: tts-spin 0.6s linear infinite;
}
@keyframes tts-spin { to { transform: rotate(360deg); } }
.copy-button.copy-done {
  background: var(--color-success-soft);
  border-color: var(--color-success);
  color: var(--color-success);
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border-light);
}
.suggestion-chip {
  padding: 6px 14px;
  border: 1px solid rgba(59, 130, 246, 0.14);
  border-radius: var(--radius-full);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.suggestion-chip:hover:not(:disabled) {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  transform: translateY(-1px);
}
.suggestion-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.full-width {
  width: 100%;
}

.sidebar .secondary-button.full-width {
  min-height: 42px;
}

.turn-bubble .object-card {
  min-width: 200px;
}

.user-bubble .object-card-badge {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

@media (max-width: 1400px) {
  .workspace {
    grid-template-columns: 220px minmax(0, 1fr) 320px;
  }
}

@media (max-width: 1180px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .history-sidebar {
    display: none;
  }

  .chat-header {
    flex-direction: column;
  }

  .sidebar {
    min-height: auto;
    height: auto;
  }
}

@media (max-width: 720px) {
  .app-shell {
    padding: 0;
  }

  .workspace {
    gap: 0;
  }

  .chat-card,
  .sidebar {
    min-height: auto;
    height: auto;
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .chat-card {
    min-height: 100vh;
  }

  .message {
    max-width: 100%;
  }

  .composer,
  .field-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
