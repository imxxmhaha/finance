<template>
  <div class="knowledge-page">
    <!-- 顶部导航 -->
    <header class="top-bar">
      <button class="back-btn" @click="$router.push('/')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        <span>返回对话</span>
      </button>
      <h1 class="page-title">知识库检索</h1>
      <div class="stats" v-if="stats">
        <span class="stats-dot"></span>
        <span>{{ stats.count }} 条知识</span>
      </div>
    </header>

    <!-- 搜索区域 -->
    <div class="search-section">
      <div class="search-box">
        <svg class="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          v-model="query"
          type="text"
          placeholder="输入问题，如：贷款利率是多少？"
          class="search-input"
          @keyup.enter="doSearch"
        />
        <button class="search-btn" @click="doSearch" :disabled="!query.trim() || loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>搜索</span>
        </button>
      </div>

      <!-- 筛选器 -->
      <div class="filters">
        <button
          v-for="opt in sourceOptions"
          :key="opt.value"
          class="filter-chip"
          :class="{ active: sourceType === opt.value }"
          @click="sourceType = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- 结果区域 -->
    <div class="results-section">
      <div v-if="searched && results.length === 0 && !loading" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <p>未找到相关知识</p>
      </div>

      <div v-if="results.length > 0" class="results-list">
        <div class="results-header">
          <span>找到 {{ results.length }} 条相关结果</span>
        </div>
        <div
          v-for="(item, index) in results"
          :key="index"
          class="result-card"
        >
          <div class="result-header">
            <span class="result-badge" :class="item.source_type">{{ sourceLabel(item.source_type) }}</span>
            <span class="result-score">{{ (item.score * 100).toFixed(1) }}%</span>
          </div>
          <div class="result-text">{{ item.chunk_text }}</div>
          <div class="result-meta">
            <span class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              {{ item.source_file }}
            </span>
            <span class="meta-item" v-if="item.metadata?.product_name">
              {{ item.metadata.product_name }}
            </span>
          </div>
        </div>
      </div>

      <!-- 初始状态 -->
      <div v-if="!searched && !loading" class="initial-state">
        <div class="initial-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
        </div>
        <p class="initial-title">金融知识库</p>
        <p class="initial-desc">支持贷款、理财、账户、服务等产品的智能检索</p>
        <div class="quick-queries">
          <button
            v-for="q in quickQueries"
            :key="q"
            class="quick-btn"
            @click="query = q; doSearch()"
          >
            {{ q }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { searchKnowledge, fetchKnowledgeStats } from '../utils/api'

const query = ref('')
const sourceType = ref(null)
const results = ref([])
const loading = ref(false)
const searched = ref(false)
const stats = ref(null)

const sourceOptions = [
  { label: '全部', value: null },
  { label: '贷款', value: 'loan' },
  { label: '理财', value: 'wealth' },
  { label: '账户', value: 'account' },
  { label: '服务', value: 'service' },
]

const quickQueries = [
  '贷款利率是多少',
  '有什么理财产品',
  '开户需要什么条件',
  '贷款需要什么材料',
]

function sourceLabel(type) {
  const map = { loan: '贷款', wealth: '理财', account: '账户', service: '服务' }
  return map[type] || type
}

async function doSearch() {
  if (!query.value.trim() || loading.value) return
  loading.value = true
  searched.value = true
  try {
    const res = await searchKnowledge(query.value, 5, sourceType.value)
    if (res.code === 0) {
      results.value = res.data?.results || []
    } else {
      results.value = []
    }
  } catch (e) {
    console.error('搜索失败:', e)
    results.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await fetchKnowledgeStats()
    if (res.code === 0) {
      stats.value = res.data
    }
  } catch (e) {
    console.error('获取统计失败:', e)
  }
})
</script>

<style scoped>
.knowledge-page {
  min-height: 100vh;
  background: var(--color-bg-deep);
  color: var(--color-text-primary);
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
.top-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  backdrop-filter: blur(20px);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  transition: color var(--duration-fast);
}
.back-btn:hover { color: var(--color-text-primary); }

.page-title {
  font-size: 16px;
  font-weight: 600;
  flex: 1;
}

.stats {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
}
.stats-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-success);
}

/* 搜索区域 */
.search-section {
  padding: 32px 24px 16px;
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--color-surface-field);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 4px;
  transition: border-color var(--duration-fast);
}
.search-box:focus-within {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-soft);
}

.search-icon {
  margin: 0 12px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--color-text-primary);
  font-size: 15px;
  padding: 12px 0;
}
.search-input::placeholder { color: var(--color-text-muted); }

.search-btn {
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--duration-fast);
  flex-shrink: 0;
}
.search-btn:hover:not(:disabled) { background: var(--color-accent-strong); }
.search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 筛选器 */
.filters {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.filter-chip {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  padding: 6px 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.filter-chip:hover { border-color: var(--color-accent); color: var(--color-text-primary); }
.filter-chip.active {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

/* 结果区域 */
.results-section {
  flex: 1;
  padding: 0 24px 32px;
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
}

.results-header {
  font-size: 13px;
  color: var(--color-text-muted);
  margin-bottom: 16px;
}

.result-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 12px;
  transition: border-color var(--duration-fast);
}
.result-card:hover { border-color: var(--color-border-strong); }

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.result-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  text-transform: uppercase;
}
.result-badge.loan { background: var(--color-accent-soft); color: var(--color-accent); }
.result-badge.wealth { background: var(--color-warm-soft); color: var(--color-warm); }
.result-badge.account { background: var(--color-success-soft); color: var(--color-success); }
.result-badge.service { background: var(--color-info-soft); color: var(--color-info); }

.result-score {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent);
}

.result-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.result-meta {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-muted);
}

/* 空状态 */
.empty-state, .initial-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}
.empty-state p, .initial-title {
  margin-top: 16px;
  font-size: 16px;
  color: var(--color-text-secondary);
}
.initial-desc {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text-muted);
}

/* 快捷查询 */
.quick-queries {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 24px;
  justify-content: center;
}
.quick-btn {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  padding: 8px 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.quick-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-soft);
}
</style>
