<template>
  <div class="discovery-panel">
    <h2>종목 자동 발굴</h2>
    <p class="desc">스크리닝으로 유망 종목을 자동 선별해 투자 인사이트를 한 번에 받습니다.</p>

    <div class="options">
      <div class="option-group">
        <label class="option-label">시장</label>
        <div class="checkbox-row">
          <label class="checkbox-item">
            <input type="checkbox" v-model="markets" value="US" />
            <span>미국 (US)</span>
          </label>
          <label class="checkbox-item">
            <input type="checkbox" v-model="markets" value="KR" />
            <span>국내 (KR)</span>
          </label>
        </div>
      </div>

      <div class="option-group">
        <label class="option-label">종목 수</label>
        <div class="radio-row">
          <label v-for="n in [3, 5, 10]" :key="n" class="radio-item">
            <input type="radio" v-model="topN" :value="n" />
            <span>{{ n }}개</span>
          </label>
        </div>
      </div>
    </div>

    <button class="discover-btn" :disabled="loading || markets.length === 0" @click="handleDiscover">
      <span v-if="loading" class="btn-spinner" />
      {{ loading ? `분석 중... (${progressLabel})` : '인사이트 발굴 실행' }}
    </button>

    <div v-if="error" class="error-box">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { discoverStocks } from '../api/index.js'

const emit = defineEmits(['result'])

const markets = ref(['US', 'KR'])
const topN = ref(5)
const loading = ref(false)
const error = ref('')
const elapsed = ref(0)
let timer = null

const progressLabel = computed(() => {
  if (elapsed.value < 60) return `${elapsed.value}초`
  return `${Math.floor(elapsed.value / 60)}분 ${elapsed.value % 60}초`
})

async function handleDiscover() {
  if (markets.value.length === 0) return
  loading.value = true
  error.value = ''
  elapsed.value = 0
  timer = setInterval(() => { elapsed.value++ }, 1000)
  try {
    const result = await discoverStocks(markets.value, topN.value)
    emit('result', result)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '발굴 중 오류가 발생했습니다.'
  } finally {
    loading.value = false
    clearInterval(timer)
  }
}
</script>

<style scoped>
.discovery-panel {
  background: #1e1e2e;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #313244;
}

h2 {
  margin: 0 0 6px;
  font-size: 1.1rem;
  color: #cdd6f4;
}

.desc {
  margin: 0 0 20px;
  font-size: 0.82rem;
  color: #6c7086;
  line-height: 1.5;
}

.options {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 20px;
}

.option-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.option-label {
  font-size: 0.82rem;
  color: #a6adc8;
  width: 48px;
  flex-shrink: 0;
}

.checkbox-row,
.radio-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.checkbox-item,
.radio-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.88rem;
  color: #cdd6f4;
  cursor: pointer;
}

.checkbox-item input,
.radio-item input {
  accent-color: #a6e3a1;
  cursor: pointer;
}

.discover-btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 8px;
  background: #a6e3a1;
  color: #1e1e2e;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: background 0.2s;
}

.discover-btn:hover:not(:disabled) {
  background: #cba6f7;
}

.discover-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #1e1e2e44;
  border-top-color: #1e1e2e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-box {
  margin-top: 12px;
  padding: 10px 14px;
  background: #45293a;
  border-left: 4px solid #f38ba8;
  border-radius: 6px;
  color: #f38ba8;
  font-size: 0.88rem;
}
</style>
