<template>
  <aside class="assistant-panel">
    <div class="assistant-header">
      <span>智能助手</span>
      <span class="status">在线</span>
    </div>

    <el-scrollbar class="assistant-scroll">
      <div v-for="(message, index) in messages" :key="`${message.role}-${index}`" class="assistant-message-row" :class="`assistant-message-row--${message.role}`">
        <div class="assistant-avatar">{{ message.role === 'assistant' ? 'AI' : '我' }}</div>
        <div class="assistant-bubble">
          <p>{{ message.text }}</p>
        </div>
      </div>

      <div v-if="lastResponseType === 'clarification'" class="assistant-section assistant-clarification">
        <div class="assistant-section-title">需要更多信息</div>
        <div class="assistant-bubble assistant-bubble--clarification">
          <p>{{ messages[messages.length - 1]?.text }}</p>
        </div>
      </div>

      <div v-if="lastResponseType === 'action_pending'" class="assistant-section assistant-action-pending">
        <div class="assistant-section-title">功能预告</div>
        <div class="assistant-bubble assistant-bubble--pending">
          <p>{{ messages[messages.length - 1]?.text }}</p>
        </div>
      </div>

      <div v-if="lastResponseType === 'greeting'" class="assistant-section assistant-greeting">
        <div class="assistant-bubble assistant-bubble--greeting">
          <p>{{ messages[messages.length - 1]?.text }}</p>
        </div>
      </div>

      <div v-if="extractedConstraints.length && lastResponseType !== 'greeting'" class="assistant-section">
        <div class="assistant-section-title">已识别条件</div>
        <div class="assistant-tags">
          <el-tag v-for="item in extractedConstraints" :key="item" type="info">{{ item }}</el-tag>
        </div>
      </div>

      <div v-if="recommendations.length" class="assistant-section">
        <div class="assistant-section-title">推荐结果</div>
        <div v-for="item in recommendations" :key="`${item.source_type}-${item.dish_id ?? item.merchant_id}`" class="assistant-card">
          <div class="assistant-card-title">{{ item.dish_name || item.merchant_name }}</div>
          <div class="assistant-card-subtitle">{{ item.merchant_name }}</div>
          <div v-if="item.price !== null && item.price !== undefined" class="assistant-card-meta">¥{{ item.price }}</div>
          <div class="assistant-card-body">{{ item.reason }}</div>
        </div>
      </div>

      <div v-if="comparisons.length" class="assistant-section">
        <div class="assistant-section-title">对比结果</div>
        <div v-for="item in comparisons" :key="item.merchant_id" class="assistant-card">
          <div class="assistant-card-title">{{ item.merchant_name }}</div>
          <div class="assistant-card-body">{{ item.summary }}</div>
        </div>
      </div>

      <div v-if="citations.length" class="assistant-section">
        <div class="assistant-section-title">引用依据</div>
        <div v-for="item in citations" :key="`${item.source_type}-${item.source_id}`" class="assistant-citation">
          <div class="assistant-citation-title">{{ item.title }}</div>
          <div class="assistant-citation-body">{{ item.snippet }}</div>
        </div>
      </div>

      <div v-if="suggestedActions.length" class="assistant-section">
        <div class="assistant-section-title">建议操作</div>
        <div class="assistant-tags">
          <el-tag v-for="item in suggestedActions" :key="item">{{ item }}</el-tag>
        </div>
      </div>

      <div v-if="errorMessage" class="assistant-error">{{ errorMessage }}</div>
    </el-scrollbar>

    <div class="assistant-composer">
      <el-input v-model="draft" placeholder="输入问题…" />
      <el-button type="primary" @click="submit">{{ loading ? '发送中' : '发送' }}</el-button>
    </div>
  </aside>
</template>

<script setup>
import { useAssistant } from '../../composables/useAssistant'

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
  submit,
} = useAssistant()
</script>

<style scoped>
.assistant-panel {
  position: fixed;
  right: 32px;
  bottom: 24px;
  width: 380px;
  height: 640px;
  max-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 18px 40px rgba(50, 82, 136, 0.18);
  backdrop-filter: blur(14px);
}

.assistant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.status {
  color: #5b82ff;
  font-size: 13px;
}

.assistant-scroll {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.assistant-message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.assistant-message-row--user {
  flex-direction: row-reverse;
}

.assistant-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7196ff, #90d3ff);
  color: #fff;
  font-weight: 700;
  flex-shrink: 0;
}

.assistant-bubble {
  flex: 1;
  padding: 14px 16px;
  border-radius: 18px;
  background: #f4f8ff;
  color: #32445f;
}

.assistant-bubble p {
  margin: 0;
}

.assistant-section {
  margin-top: 12px;
}

.assistant-section-title {
  margin-bottom: 8px;
  color: #5a6f91;
  font-size: 13px;
  font-weight: 600;
}

.assistant-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.assistant-card,
.assistant-citation {
  padding: 12px;
  border-radius: 16px;
  background: #f7f9fc;
}

.assistant-card + .assistant-card,
.assistant-citation + .assistant-citation {
  margin-top: 8px;
}

.assistant-card-title,
.assistant-citation-title {
  font-weight: 600;
  color: #24364d;
}

.assistant-card-subtitle,
.assistant-card-meta,
.assistant-citation-body,
.assistant-card-body {
  margin-top: 4px;
  color: #53657d;
  font-size: 13px;
}

.assistant-error {
  color: #d14343;
  font-size: 13px;
}

.assistant-composer {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}
</style>

