import { computed, ref } from 'vue'
import { getCart } from '../api/cart'

const cart = ref({ items: [], goods_amount: 0 })
const cartLoading = ref(false)

export function useCart() {
  const refreshCart = async () => {
    cartLoading.value = true
    try {
      cart.value = await getCart()
    } finally {
      cartLoading.value = false
    }
  }

  const merchantGroups = computed(() => cart.value.items || [])

  return { cart, cartLoading, merchantGroups, refreshCart }
}
