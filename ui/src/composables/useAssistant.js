import { ref } from 'vue'
import { chatWithAssistant } from '../api/assistant'

export function useAssistant() {
  const sessionId = ref(null)
  const draft = ref('')
  const loading = ref(false)
  const errorMessage = ref('')
  const messages = ref([
    { role: 'assistant', text: '你好，欢迎来到 smart_order。' },
    {
      role: 'assistant',
      text: '我可以根据你的口味、人数和预算，帮你推荐合适的商家和菜品，也可以协助你更快完成下单选择。',
    },
  ])
  const lastResponseType = ref(null)
  const extractedConstraints = ref([])
  const recommendations = ref([])
  const comparisons = ref([])
  const citations = ref([])
  const suggestedActions = ref([])

  const submit = async () => {
    const question = draft.value.trim()
    if (!question || loading.value) {
      return
    }

    messages.value.push({ role: 'user', text: question })
    draft.value = ''
    loading.value = true
    errorMessage.value = ''

    // Clear previous structured data before new request
    lastResponseType.value = null
    extractedConstraints.value = []
    recommendations.value = []
    comparisons.value = []
    citations.value = []
    suggestedActions.value = []

    try {
      const response = await chatWithAssistant({
        message: question,
        session_id: sessionId.value,
      })
      sessionId.value = response.session_id
      lastResponseType.value = response.response_type
      messages.value.push({ role: 'assistant', text: response.message })

      const constraints = response.extracted_constraints
      if (constraints) {
        extractedConstraints.value = [
          ...(constraints.cuisine_types || []),
          ...(constraints.party_size ? [`${constraints.party_size}人`] : []),
          ...(constraints.budget_max ? [`${constraints.budget_max}元内`] : []),
          ...(constraints.exclude_allergens || []),
        ]
      }
      recommendations.value = response.recommendations || []
      comparisons.value = response.comparisons || []
      citations.value = response.citations || []
      suggestedActions.value = response.suggested_actions || []
    } catch (error) {
      errorMessage.value = error?.message || '智能助手暂时不可用，请稍后再试'
    } finally {
      loading.value = false
    }
  }

  return {
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
  }
}
