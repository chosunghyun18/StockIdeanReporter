<template>
  <div class="analyzer">
    <h2>종목 분석</h2>
    <form @submit.prevent="handleAnalyze">
      <div class="input-row">
        <input
          v-model="ticker"
          placeholder="종목 코드 (예: AAPL, 005930)"
          required
        />
        <select v-model="market">
          <option value="US">미국 (US)</option>
          <option value="KR">국내 (KR)</option>
        </select>
        <button type="submit" :disabled="loading">
          {{ loading ? '분석 중...' : '분석 실행' }}
        </button>
      </div>
    </form>

    <div v-if="loading" class="spinner-wrap">
      <div class="spinner" />
      <span>AI 에이전트가 분석 중입니다. 잠시 기다려 주세요...</span>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { analyzeStock } from '../api/index.js'

const emit = defineEmits(['result'])

const ticker = ref('')
const market = ref('US')
const loading = ref(false)
const error = ref('')

async function handleAnalyze() {
  if (!ticker.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const result = await analyzeStock(ticker.value.trim(), market.value)
    emit('result', result)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '분석 중 오류가 발생했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.analyzer {
  background: #1e1e2e;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}

h2 {
  margin: 0 0 16px;
  font-size: 1.1rem;
  color: #cdd6f4;
}

.input-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

input {
  flex: 1;
  min-width: 180px;
  padding: 10px 14px;
  border: 1px solid #313244;
  border-radius: 8px;
  background: #11111b;
  color: #cdd6f4;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.2s;
}

input:focus {
  border-color: #89b4fa;
}

select {
  padding: 10px 14px;
  border: 1px solid #313244;
  border-radius: 8px;
  background: #11111b;
  color: #cdd6f4;
  font-size: 0.95rem;
  cursor: pointer;
}

button[type='submit'] {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  background: #89b4fa;
  color: #1e1e2e;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background 0.2s;
}

button[type='submit']:hover:not(:disabled) {
  background: #b4befe;
}

button[type='submit']:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  color: #a6adc8;
  font-size: 0.9rem;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid #313244;
  border-top-color: #89b4fa;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-box {
  margin-top: 12px;
  padding: 12px 16px;
  background: #45293a;
  border-left: 4px solid #f38ba8;
  border-radius: 6px;
  color: #f38ba8;
  font-size: 0.9rem;
}
</style>
