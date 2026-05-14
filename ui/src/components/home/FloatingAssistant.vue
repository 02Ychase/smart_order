<template>
  <!-- Launcher button -->
  <button v-if="!panelOpen" class="launcher" @click="panelOpen = true">
    <span class="launcher-icon">AI</span>
  </button>

  <!-- Panel -->
  <aside v-else class="assistant-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-left">
        <div class="ai-avatar-sm">AI</div>
        <div>
          <p class="header-title">智能助手</p>
          <p class="header-sub">● 在线 · 帮你挑、帮你点</p>
        </div>
      </div>
      <button class="header-close" @click="panelOpen = false">×</button>
    </div>

    <!-- Messages -->
    <div ref="scrollArea" class="panel-messages mt-scroll">
      <div v-for="(message, index) in messages" :key="`msg-${index}`" class="bubble-row" :class="message.role">
        <div class="bubble-avatar" :class="message.role">{{ message.role === 'assistant' ? 'AI' : '我' }}</div>
        <div class="bubble" :class="message.role">{{ message.text }}</div>
      </div>

      <div v-if="loading" class="thinking">
        <span class="thinking-dot" /> AI 正在思考…
      </div>

      <!-- Constraint chips -->
      <div v-if="extractedConstraints.length && !loading" class="section-stack">
        <p class="section-label">已识别条件</p>
        <div class="chip-row">
          <span v-for="c in extractedConstraints" :key="c" class="chip chip--warm">{{ c }}</span>
        </div>
      </div>

      <!-- Recommendation cards -->
      <div v-if="recommendations.length && !loading" class="section-stack">
        <p class="section-label">推荐结果</p>
        <div v-for="(item, i) in recommendations" :key="`rec-${i}`" class="rec-card">
          <div class="rec-thumb" :style="{ background: recBg(item) }">{{ recGlyph(item) }}</div>
          <div class="rec-body">
            <p class="rec-name">{{ item.dish_name || item.merchant_name }}</p>
            <p class="rec-merchant">{{ item.merchant_name }}</p>
            <p class="rec-reason">{{ item.reason }}</p>
            <div class="rec-footer">
              <SoPrice :value="item.price" :size="15" />
            </div>
          </div>
        </div>
      </div>

      <!-- Comparisons -->
      <div v-if="comparisons.length && !loading" class="section-stack">
        <p class="section-label">对比结果</p>
        <div v-for="item in comparisons" :key="item.merchant_id" class="info-card">
          <p class="info-title">{{ item.merchant_name }}</p>
          <p class="info-body">{{ item.summary }}</p>
        </div>
      </div>

      <!-- Citations -->
      <div v-if="citations.length && !loading" class="section-stack">
        <p class="section-label">引用依据</p>
        <div v-for="item in citations" :key="`${item.source_type}-${item.source_id}`" class="info-card">
          <p class="info-title">{{ item.title }}</p>
          <p class="info-body">{{ item.snippet }}</p>
        </div>
      </div>

      <!-- Pending action -->
      <div v-if="pendingAction && !loading" class="section-stack">
        <p class="section-label">待确认操作</p>
        <div class="info-card">
          <p class="info-title">{{ pendingAction.summary }}</p>
          <p class="info-body">回复"确认"执行，或回复"取消"放弃。</p>
        </div>
      </div>

      <!-- Executed actions -->
      <div v-if="executedActions.length && !loading" class="section-stack">
        <p class="section-label">已完成操作</p>
        <div v-for="item in executedActions" :key="`${item.type}-${item.message}`" class="info-card">
          <p class="info-title">{{ item.message }}</p>
          <p class="info-body">{{ item.success ? '操作成功' : '操作失败' }}</p>
        </div>
      </div>

      <!-- Suggested actions -->
      <div v-if="suggestedActions.length && !loading" class="section-stack">
        <div class="chip-row">
          <span v-for="s in suggestedActions" :key="s" class="chip chip--orange" @click="fillDraft(s)">{{ s }}</span>
        </div>
      </div>

      <!-- Error -->
      <div v-if="errorMessage" class="error-text">{{ errorMessage }}</div>
    </div>

    <!-- Composer -->
    <div class="composer">
      <div class="composer-input-wrap">
        <input
          v-model="draft"
          placeholder="问问 AI 助手..."
          @keyup.enter="submit"
        />
      </div>
      <button class="send-btn" :disabled="loading || !draft.trim()" @click="submit">➤</button>
    </div>
  </aside>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { useAssistant } from '../../composables/useAssistant'
import SoPrice from '../shared/SoPrice.vue'

const {
  draft,
  loading,
  errorMessage,
  messages,
  lastResponseType,
  extractedConstraints,
  recommendations,
  comparisons,
  citations,
  suggestedActions,
  pendingAction,
  executedActions,
  submit,
} = useAssistant()

const props = defineProps({
  initialOpen: { type: Boolean, default: false },
})

const panelOpen = ref(props.initialOpen)
const scrollArea = ref(null)

const REC_PALETTE = [
  { glyph: '🍜', bg: 'linear-gradient(135deg,#fff3e0,#ffe0b2)' },
  { glyph: '🍛', bg: 'linear-gradient(135deg,#fff8e1,#ffecb3)' },
  { glyph: '🍲', bg: 'linear-gradient(135deg,#fce4ec,#f8bbd0)' },
  { glyph: '🍱', bg: 'linear-gradient(135deg,#e8f5e9,#c8e6c9)' },
  { glyph: '🥘', bg: 'linear-gradient(135deg,#fff3e0,#ffccbc)' },
]

const recGlyph = (item) => REC_PALETTE[((item.dish_id || 0) % REC_PALETTE.length)].glyph
const recBg = (item) => REC_PALETTE[((item.dish_id || 0) % REC_PALETTE.length)].bg

const fillDraft = (text) => {
  draft.value = text
}

watch(messages, () => {
  nextTick(() => {
    if (scrollArea.value) scrollArea.value.scrollTop = scrollArea.value.scrollHeight
  })
}, { deep: true })
</script>

<style scoped>
/* Launcher */
.launcher {
  position: fixed;
  right: 32px;
  bottom: 32px;
  z-index: 800;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, var(--so-yellow), var(--so-gold));
  box-shadow: 0 4px 16px rgba(255, 209, 0, 0.4);
  cursor: pointer;
  transition: transform 0.2s;
}

.launcher:hover { transform: scale(1.08); }

.launcher-icon {
  font-size: 18px;
  font-weight: 800;
  color: var(--so-ink-1);
}

/* Panel */
.assistant-panel {
  position: fixed;
  right: 32px;
  bottom: 32px;
  z-index: 800;
  width: 400px;
  height: 640px;
  max-height: calc(100vh - 80px);
  background: var(--so-surface);
  border-radius: var(--so-r-lg);
  box-shadow: var(--so-shadow-float);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: mt-slide-up 0.25s ease-out;
  font-family: var(--so-font-sans);
}

/* Header */
.panel-header {
  padding: 14px 18px;
  background: linear-gradient(135deg, var(--so-yellow), var(--so-gold));
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left { display: flex; align-items: center; gap: 10px; }

.ai-avatar-sm {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--so-ink-1); color: var(--so-yellow);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 800;
}

.header-title { margin: 0; font-size: 14px; font-weight: 700; color: var(--so-ink-1); }
.header-sub { margin: 2px 0 0; font-size: 11px; color: rgba(0, 0, 0, 0.55); }

.header-close {
  background: rgba(0, 0, 0, 0.08); border: none; cursor: pointer;
  width: 28px; height: 28px; border-radius: 50%;
  color: var(--so-ink-1); font-size: 16px;
  display: inline-flex; align-items: center; justify-content: center;
}

/* Messages area */
.panel-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: var(--so-page);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Bubbles */
.bubble-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.bubble-row.user { flex-direction: row-reverse; }

.bubble-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800;
}

.bubble-avatar.assistant { background: var(--so-ink-1); color: var(--so-yellow); }
.bubble-avatar.user { background: var(--so-ink-2); color: #fff; }

.bubble {
  max-width: 78%;
  padding: 10px 14px;
  font-size: 13.5px;
  line-height: 1.55;
  white-space: pre-line;
  color: var(--so-ink-1);
}

.bubble.assistant {
  background: var(--so-surface);
  border-radius: 4px 16px 16px 16px;
}

.bubble.user {
  background: var(--so-yellow);
  border-radius: 16px 4px 16px 16px;
}

/* Thinking */
.thinking {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--so-ink-4);
}

.thinking-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  border: 2px solid var(--so-ink-4);
  border-top-color: transparent;
  animation: mt-spin 0.8s linear infinite;
}

/* Section stacks */
.section-stack {
  margin-left: 36px;
  margin-bottom: 4px;
}

.section-label {
  margin: 0 0 6px;
  font-size: 11px;
  color: var(--so-ink-4);
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* Chips */
.chip-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.chip {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: var(--so-r-pill);
  font-size: 12px;
  font-weight: 500;
}

.chip--warm {
  background: var(--so-yellow-soft);
  color: #866a00;
}

.chip--orange {
  background: var(--so-orange-soft);
  color: var(--so-orange);
  cursor: pointer;
  transition: background 0.15s;
}

.chip--orange:hover { background: #ffe0d5; }

/* Recommendation card */
.rec-card {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: var(--so-surface);
  border-radius: var(--so-r-md);
  border: 1px solid var(--so-border-1);
  margin-bottom: 8px;
}

.rec-thumb {
  width: 56px; height: 56px; border-radius: var(--so-r-sm);
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
}

.rec-body { flex: 1; min-width: 0; }
.rec-name { margin: 0; font-size: 13px; font-weight: 700; color: var(--so-ink-1); }
.rec-merchant { margin: 2px 0; font-size: 11px; color: var(--so-ink-4); }
.rec-reason { margin: 0 0 4px; font-size: 11px; color: var(--so-ink-3); line-height: 1.4; }
.rec-footer { display: flex; align-items: center; justify-content: space-between; }

/* Info card (comparisons, citations, actions) */
.info-card {
  padding: 10px 12px;
  border-radius: var(--so-r-sm);
  background: var(--so-surface);
  border: 1px solid var(--so-border-1);
  margin-bottom: 6px;
}

.info-title { margin: 0; font-size: 13px; font-weight: 600; color: var(--so-ink-1); }
.info-body { margin: 3px 0 0; font-size: 12px; color: var(--so-ink-3); line-height: 1.45; }

.error-text { font-size: 12px; color: var(--so-red); margin-left: 36px; }

/* Composer */
.composer {
  padding: 12px 16px;
  background: var(--so-surface);
  border-top: 1px solid var(--so-border-1);
  display: flex;
  gap: 8px;
  align-items: center;
}

.composer-input-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 14px;
  height: 38px;
  background: var(--so-page);
  border-radius: var(--so-r-pill);
}

.composer-input-wrap input {
  flex: 1;
  height: 32px;
  background: transparent;
  border: none;
  outline: none;
  font-size: 13px;
  color: var(--so-ink-1);
  font-family: var(--so-font-sans);
}

.send-btn {
  width: 38px; height: 38px; border-radius: 50%;
  background: var(--so-orange); color: #fff;
  border: none;
  font-size: 16px; font-weight: 700;
  cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background 0.15s;
}

.send-btn:disabled {
  background: var(--so-ink-5);
  cursor: not-allowed;
}
</style>
