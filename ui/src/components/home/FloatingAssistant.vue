<template>
  <aside class="assistant-panel">
    <div class="assistant-header">
      <span>智能助手</span>
      <span class="status">在线</span>
    </div>
    <div class="assistant-message-row">
      <div class="assistant-avatar">AI</div>
      <div class="assistant-bubble">
        <p>你好，欢迎来到 smart_order。</p>
        <p>我可以根据你的口味、人数和预算，帮你推荐合适的商家和菜品，也可以协助你更快完成下单选择。</p>
      </div>
    </div>
    <el-input placeholder="输入问题…" />
  </aside>
</template>

<style scoped>
.assistant-panel {
  position: fixed;
  right: 32px;
  bottom: 24px;
  width: 380px;
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
  margin-bottom: 16px;
  font-weight: 600;
}

.status {
  color: #5b82ff;
  font-size: 13px;
}

.assistant-message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
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

.assistant-bubble p + p {
  margin-top: 8px;
}
</style>
