<template>
  <div class="discovery-result">
    <div class="summary-bar">
      <span class="summary-title">발굴 결과</span>
      <span class="summary-count">{{ successCount }}개 종목 인사이트</span>
      <span class="markets-tag">{{ marketsLabel }}</span>
    </div>

    <div class="cards-grid">
      <div
        v-for="item in result.results"
        :key="item.ticker"
        class="stock-card"
        :class="{ selected: selectedTicker === item.ticker, error: item.status === 'error' }"
        @click="select(item)"
      >
        <div class="card-header">
          <span class="ticker">{{ item.ticker }}</span>
          <span class="market-tag">{{ item.market }}</span>
          <span class="status-dot" :class="item.status" />
        </div>
        <p class="idea-preview">{{ preview(item) }}</p>
        <div v-if="item.slack_sent" class="slack-badge">Slack 전송됨</div>
      </div>
    </div>

    <div v-if="selected" class="detail-panel">
      <div class="detail-header">
        <span class="detail-ticker">{{ selected.ticker }}</span>
        <button class="close-btn" @click="selectedTicker = null">닫기</button>
      </div>
      <div v-if="selected.status === 'error'" class="error-box">{{ selected.error }}</div>
      <div v-else class="markdown-body" v-html="renderedIdea" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  result: { type: Object, required: true },
})

const selectedTicker = ref(null)

const successCount = computed(() =>
  props.result.results.filter(r => r.status === 'success').length
)

const marketsLabel = computed(() => {
  const ms = [...new Set(props.result.results.map(r => r.market))]
  return ms.join(' · ')
})

const selected = computed(() =>
  props.result.results.find(r => r.ticker === selectedTicker.value) ?? null
)

const renderedIdea = computed(() => {
  if (!selected.value?.investment_idea) return ''
  return marked.parse(selected.value.investment_idea)
})

function preview(item) {
  if (item.status === 'error') return item.error || '분석 실패'
  if (!item.investment_idea) return '분석 결과 없음'
  const plain = item.investment_idea.replace(/#{1,6}\s/g, '').replace(/\*\*/g, '')
  return plain.slice(0, 100) + (plain.length > 100 ? '…' : '')
}

function select(item) {
  selectedTicker.value = selectedTicker.value === item.ticker ? null : item.ticker
}
</script>

<style scoped>
.discovery-result {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.summary-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.summary-title {
  font-size: 1rem;
  font-weight: 700;
  color: #cdd6f4;
}

.summary-count {
  padding: 3px 10px;
  background: #1d3b2f;
  color: #a6e3a1;
  border-radius: 20px;
  font-size: 0.82rem;
  font-weight: 600;
}

.markets-tag {
  padding: 3px 10px;
  background: #313244;
  color: #a6adc8;
  border-radius: 20px;
  font-size: 0.82rem;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.stock-card {
  background: #181825;
  border: 1px solid #313244;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.stock-card:hover {
  border-color: #89b4fa;
  background: #1e1e2e;
}

.stock-card.selected {
  border-color: #a6e3a1;
  background: #1d3b2f22;
}

.stock-card.error {
  border-color: #f38ba833;
  opacity: 0.7;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.ticker {
  font-weight: 700;
  font-size: 1rem;
  color: #89b4fa;
  letter-spacing: 0.5px;
}

.market-tag {
  padding: 2px 7px;
  background: #313244;
  border-radius: 10px;
  font-size: 0.75rem;
  color: #a6adc8;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-left: auto;
  flex-shrink: 0;
}

.status-dot.success { background: #a6e3a1; }
.status-dot.error   { background: #f38ba8; }

.idea-preview {
  margin: 0 0 8px;
  font-size: 0.82rem;
  color: #a6adc8;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.slack-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #2e3b4e;
  color: #89dceb;
  border-radius: 10px;
  font-size: 0.75rem;
}

/* 상세 패널 */
.detail-panel {
  background: #1e1e2e;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #313244;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.detail-ticker {
  font-size: 1.3rem;
  font-weight: 700;
  color: #89b4fa;
  letter-spacing: 1px;
}

.close-btn {
  padding: 4px 14px;
  border: 1px solid #45475a;
  border-radius: 6px;
  background: transparent;
  color: #a6adc8;
  font-size: 0.82rem;
  cursor: pointer;
}

.close-btn:hover {
  background: #313244;
}

.error-box {
  padding: 12px 16px;
  background: #45293a;
  border-left: 4px solid #f38ba8;
  border-radius: 6px;
  color: #f38ba8;
  font-size: 0.9rem;
}

.markdown-body {
  color: #cdd6f4;
  font-size: 0.92rem;
  line-height: 1.7;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) { color: #89b4fa; margin-top: 1.2em; }

.markdown-body :deep(table) { width: 100%; border-collapse: collapse; margin: 12px 0; }
.markdown-body :deep(th), .markdown-body :deep(td) { padding: 8px 12px; border: 1px solid #313244; font-size: 0.88rem; }
.markdown-body :deep(th) { background: #181825; color: #89b4fa; }
.markdown-body :deep(code) { background: #313244; padding: 2px 6px; border-radius: 4px; font-size: 0.88em; }
.markdown-body :deep(blockquote) { border-left: 3px solid #89b4fa; margin: 0; padding: 8px 16px; background: #181825; border-radius: 0 6px 6px 0; }
.markdown-body :deep(strong) { color: #f5c2e7; }
</style>
