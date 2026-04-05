<template>
  <div class="app">
    <header class="app-header">
      <div class="logo">
        <span class="logo-icon">📊</span>
        <span class="logo-text">StockIdeaReporter</span>
      </div>
      <p class="subtitle">AI 기반 투자 아이디어 분석 · Slack 전송</p>
    </header>

    <main class="app-main">
      <div class="left-panel">
        <StockAnalyzer @result="handleSingleResult" />
        <DiscoveryPanel @result="handleDiscoveryResult" />
        <ResultHistory @select="handleSingleResult" />
      </div>

      <div class="right-panel">
        <DiscoveryResult v-if="viewMode === 'discovery'" :result="discoveryResult" />
        <AnalysisResult v-else-if="viewMode === 'single'" :result="singleResult" />
        <div v-else class="placeholder">
          <span>종목 코드를 입력해 개별 분석하거나<br>자동 발굴로 다종목 인사이트를 받으세요.</span>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import StockAnalyzer from './components/StockAnalyzer.vue'
import AnalysisResult from './components/AnalysisResult.vue'
import ResultHistory from './components/ResultHistory.vue'
import DiscoveryPanel from './components/DiscoveryPanel.vue'
import DiscoveryResult from './components/DiscoveryResult.vue'

const viewMode = ref(null)   // null | 'single' | 'discovery'
const singleResult = ref(null)
const discoveryResult = ref(null)

function handleSingleResult(result) {
  singleResult.value = result
  viewMode.value = 'single'
}

function handleDiscoveryResult(result) {
  discoveryResult.value = result
  viewMode.value = 'discovery'
}
</script>

<style>
*, *::before, *::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
  background: #11111b;
  color: #cdd6f4;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #181825; }
::-webkit-scrollbar-thumb { background: #45475a; border-radius: 3px; }
</style>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  padding: 20px 32px 12px;
  border-bottom: 1px solid #1e1e2e;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 1.6rem;
}

.logo-text {
  font-size: 1.3rem;
  font-weight: 700;
  color: #cdd6f4;
  letter-spacing: 0.5px;
}

.subtitle {
  margin: 4px 0 0 36px;
  font-size: 0.82rem;
  color: #6c7086;
}

.app-main {
  flex: 1;
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 20px;
  padding: 24px 32px;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.right-panel {
  min-width: 0;
}

.placeholder {
  height: 100%;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e1e2e;
  border-radius: 12px;
  color: #45475a;
  font-size: 0.9rem;
  text-align: center;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .app-main {
    grid-template-columns: 1fr;
    padding: 16px;
  }
}
</style>
