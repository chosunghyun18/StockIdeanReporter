<template>
  <div v-if="result" class="result-panel">
    <div class="result-header">
      <div class="ticker-badge">{{ result.ticker }}</div>
      <div class="meta">
        <span class="market">{{ result.market }}</span>
        <span
          class="status-badge"
          :class="result.status === 'success' ? 'success' : 'error'"
        >
          {{ result.status === 'success' ? '분석 완료' : '분석 실패' }}
        </span>
      </div>
    </div>

    <div v-if="result.status === 'error'" class="error-box">
      {{ result.error }}
    </div>

    <template v-else>
      <div class="markdown-body" v-html="renderedIdea" />

      <div class="action-bar">
        <SlackSendButton
          :ticker="result.ticker"
          :content="result.investment_idea || ''"
        />
        <span v-if="result.slack_sent" class="auto-sent-note">
          분석 시 자동 전송됨
        </span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import SlackSendButton from './SlackSendButton.vue'

const props = defineProps({
  result: { type: Object, default: null },
})

const renderedIdea = computed(() => {
  if (!props.result?.investment_idea) return ''
  return marked.parse(props.result.investment_idea)
})
</script>

<style scoped>
.result-panel {
  background: #1e1e2e;
  border-radius: 12px;
  padding: 24px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 8px;
}

.ticker-badge {
  font-size: 1.4rem;
  font-weight: 700;
  color: #89b4fa;
  letter-spacing: 1px;
}

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.market {
  padding: 3px 10px;
  background: #313244;
  border-radius: 20px;
  font-size: 0.8rem;
  color: #a6adc8;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.status-badge.success {
  background: #1d3b2f;
  color: #a6e3a1;
}

.status-badge.error {
  background: #3b1d1d;
  color: #f38ba8;
}

.error-box {
  padding: 12px 16px;
  background: #45293a;
  border-left: 4px solid #f38ba8;
  border-radius: 6px;
  color: #f38ba8;
  font-size: 0.9rem;
}

/* Markdown 렌더링 스타일 */
.markdown-body {
  color: #cdd6f4;
  font-size: 0.92rem;
  line-height: 1.7;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
  margin-bottom: 20px;
}

.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  color: #89b4fa;
  margin-top: 1.2em;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 8px 12px;
  border: 1px solid #313244;
  font-size: 0.88rem;
}

.markdown-body :deep(th) {
  background: #181825;
  color: #89b4fa;
}

.markdown-body :deep(code) {
  background: #313244;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.88em;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid #89b4fa;
  margin: 0;
  padding: 8px 16px;
  background: #181825;
  border-radius: 0 6px 6px 0;
}

.markdown-body :deep(strong) {
  color: #f5c2e7;
}

.action-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-top: 16px;
  border-top: 1px solid #313244;
  flex-wrap: wrap;
}

.auto-sent-note {
  font-size: 0.82rem;
  color: #6c7086;
}
</style>
