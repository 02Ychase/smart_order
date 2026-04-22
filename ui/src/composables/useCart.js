import { computed, ref } from 'vue'
import { addCartItem as postCartItem, getCart, removeCartItem as deleteCartItem } from '../api/cart'

const cart = ref({ items: [], goods_amount: 0 })
const cartLoading = ref(false)
const cartMutating = ref(false)

export function useCart() {
  const refreshCart = async () => {
    cartLoading.value = true
    try {
      cart.value = await getCart()
      return cart.value
    } finally {
      cartLoading.value = false
    }
  }

  const addCartItem = async (dishId) => {
    cartMutating.value = true
    try {
      await postCartItem({ dish_id: dishId, quantity: 1 })
      return await refreshCart()
    } finally {
      cartMutating.value = false
    }
  }

  const removeCartItem = async (dishId) => {
    cartMutating.value = true
    try {
      await deleteCartItem(dishId)
      return await refreshCart()
    } finally {
      cartMutating.value = false
    }
  }

  const merchantGroups = computed(() => cart.value.items || [])
  const goodsAmount = computed(() => cart.value.goods_amount || 0)
  const cartItemCount = computed(() => merchantGroups.value.reduce(
    (sum, group) => sum + group.items.reduce((groupSum, item) => groupSum + item.quantity, 0),
    0,
  ))

  return { cart, cartLoading, cartMutating, merchantGroups, goodsAmount, cartItemCount, refreshCart, addCartItem, removeCartItem }
}
