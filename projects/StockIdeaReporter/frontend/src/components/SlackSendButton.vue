<template>
  <div class="slack-sender">
    <button
      class="slack-btn"
      :class="{ sending: sending, sent: sent, failed: failed }"
      :disabled="sending || sent"
      @click="handleSend"
    >
      <span class="slack-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
        </svg>
      </span>
      <span class="btn-label">{{ label }}</span>
    </button>
    <p v-if="sent" class="success-msg">Slack 전송 완료!</p>
    <p v-if="failed" class="error-msg">{{ errorMsg }}</p>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { sendToSlack } from '../api/index.js'

const props = defineProps({
  ticker: { type: String, required: true },
  content: { type: String, required: true },
  reportFields: { type: Object, default: null },
})

const sending = ref(false)
const sent = ref(false)
const failed = ref(false)
const errorMsg = ref('')

const label = computed(() => {
  if (sending.value) return '전송 중...'
  if (sent.value) return '전송 완료'
  return 'Slack으로 전송하기'
})

async function handleSend() {
  if (sending.value || sent.value) return
  sending.value = true
  failed.value = false
  errorMsg.value = ''
  try {
    await sendToSlack(props.ticker, props.content, props.reportFields)
    sent.value = true
  } catch (e) {
    failed.value = true
    errorMsg.value = e.response?.data?.detail || 'Slack 전송에 실패했습니다.'
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.slack-sender {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.slack-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #4a154b;
  color: #ffffff;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}

.slack-btn:hover:not(:disabled) {
  background: #611f64;
}

.slack-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.slack-btn.sending {
  background: #611f64;
}

.slack-btn.sent {
  background: #1d6948;
}

.slack-btn.failed {
  background: #7a2929;
}

.slack-icon {
  display: flex;
  align-items: center;
}

.success-msg {
  margin: 0;
  color: #a6e3a1;
  font-size: 0.85rem;
}

.error-msg {
  margin: 0;
  color: #f38ba8;
  font-size: 0.85rem;
}
</style>
