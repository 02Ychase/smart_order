import { computed, ref } from 'vue'
import { listMerchants } from '../api/catalog'
import { buildHomepageCategories } from '../utils/homepage'

export function useHomepage() {
  const merchants = ref([])
  const loading = ref(false)
  const errorMessage = ref('')
  const selectedCategory = ref('全部')
  const selectedMerchantId = ref(null)

  const categories = computed(() => buildHomepageCategories(merchants.value))

  const filteredMerchants = computed(() => {
    if (selectedCategory.value === '全部') {
      return merchants.value
    }

    return merchants.value.filter((merchant) => merchant.homepage_category === selectedCategory.value)
  })

  const loadMerchants = async () => {
    loading.value = true
    errorMessage.value = ''

    try {
      merchants.value = await listMerchants()
    } catch (error) {
      errorMessage.value = error?.message || '加载失败，请稍后再试'
    } finally {
      loading.value = false
    }
  }

  const selectCategory = (category) => {
    selectedCategory.value = category
  }

  const selectMerchant = (merchantId) => {
    selectedMerchantId.value = merchantId
  }

  return {
    merchants,
    loading,
    errorMessage,
    categories,
    selectedCategory,
    filteredMerchants,
    selectedMerchantId,
    loadMerchants,
    selectCategory,
    selectMerchant,
  }
}
