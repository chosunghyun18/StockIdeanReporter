<template>
  <div class="history">
    <div class="history-header">
      <h3>최근 분석 결과</h3>
      <button class="refresh-btn" @click="load" :disabled="loading">새로고침</button>
    </div>

    <div v-if="loading" class="loading-text">로딩 중...</div>
    <div v-else-if="!items.length" class="empty-text">분석 결과가 없습니다.</div>

    <ul v-else class="result-list">
      <li
        v-for="item in items"
        :key="`${item.ticker}-${item.date}-${item.file_type}`"
        class="result-item"
        @click="handleSelect(item.ticker)"
      >
        <span class="item-ticker">{{ item.ticker }}</span>
        <span class="item-type">{{ typeLabel(item.file_type) }}</span>
        <span class="item-date">{{ item.date }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchResults, fetchResult } from '../api/index.js'

const emit = defineEmits(['select'])

const items = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    items.value = await fetchResults()
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function handleSelect(ticker) {
  try {
    const data = await fetchResult(ticker)
    emit('select', {
      ticker,
      market: ticker.endsWith('.KS') || ticker.endsWith('.KQ') ? 'KR' : 'US',
      status: 'success',
      investment_idea: data.content,
      slack_sent: false,
    })
  } catch (e) {
    console.error('결과 로드 실패:', e)
  }
}

function typeLabel(type) {
  const map = {
    investment_idea: '투자 아이디어',
    price_analysis: '가격 분석',
    industry_analysis: '산업 분석',
  }
  return map[type] || type
}

onMounted(load)
</script>

<style scoped>
.history {
  background: #1e1e2e;
  border-radius: 12px;
  padding: 20px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #cdd6f4;
}

.refresh-btn {
  padding: 4px 12px;
  border: 1px solid #313244;
  border-radius: 6px;
  background: transparent;
  color: #a6adc8;
  font-size: 0.82rem;
  cursor: pointer;
  transition: background 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #313244;
}

.loading-text,
.empty-text {
  color: #6c7086;
  font-size: 0.88rem;
  text-align: center;
  padding: 16px 0;
}

.result-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.result-item:hover {
  background: #313244;
}

.item-ticker {
  font-weight: 700;
  color: #89b4fa;
  min-width: 80px;
  font-size: 0.88rem;
}

.item-type {
  flex: 1;
  color: #a6adc8;
  font-size: 0.82rem;
}

.item-date {
  color: #6c7086;
  font-size: 0.8rem;
}
</style>
