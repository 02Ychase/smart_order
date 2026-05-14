import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, test, vi } from 'vitest'

const { listMerchants, listMerchantDishes, listOrders, getOrderDetail } = vi.hoisted(() => ({
  listMerchants: vi.fn(),
  listMerchantDishes: vi.fn(),
  listOrders: vi.fn(),
  getOrderDetail: vi.fn(),
}))

const { register, login } = vi.hoisted(() => ({
  register: vi.fn(),
  login: vi.fn(),
}))

const { getCart, addCartItem, removeCartItem } = vi.hoisted(() => ({
  getCart: vi.fn(),
  addCartItem: vi.fn(),
  removeCartItem: vi.fn(),
}))

vi.mock('../api/catalog', () => ({
  listMerchants,
  listMerchantDishes,
}))

vi.mock('../api/orders', () => ({
  listOrders,
  getOrderDetail,
}))

vi.mock('../api/auth', () => ({
  register,
  login,
}))

vi.mock('../api/cart', () => ({
  getCart,
  addCartItem,
  removeCartItem,
}))

const {
  listAddresses,
  createAddress,
  updateAddress,
  setDefaultAddress,
  deleteAddress,
} = vi.hoisted(() => ({
  listAddresses: vi.fn(),
  createAddress: vi.fn(),
  updateAddress: vi.fn(),
  setDefaultAddress: vi.fn(),
  deleteAddress: vi.fn(),
}))

vi.mock('../api/address', () => ({
  listAddresses,
  createAddress,
  updateAddress,
  setDefaultAddress,
  deleteAddress,
}))

import AddressView from '../views/AddressView.vue'
import CheckoutView from '../views/CheckoutView.vue'
import HomeHeader from '../components/home/HomeHeader.vue'
import LoginView from '../views/LoginView.vue'
import MerchantDetailView from '../views/MerchantDetailView.vue'
import MerchantListView from '../views/MerchantListView.vue'
import OrderDetailView from '../views/OrderDetailView.vue'
import { useAuth } from '../composables/useAuth'

const global = {
  stubs: {
    'el-card': {
      template: '<section><header><slot name="header" /></header><div><slot /></div></section>',
    },
    'el-empty': {
      props: ['description'],
      template: '<div class="empty-state">{{ description }}</div>',
    },
    'el-tag': {
      template: '<span><slot /></span>',
    },
    'el-form': {
      template: '<form><slot /></form>',
    },
    'el-form-item': {
      props: ['label'],
      template: '<label><span>{{ label }}</span><slot /></label>',
    },
    'el-input': defineComponent({
      props: ['modelValue', 'type'],
      emits: ['update:modelValue'],
      template: `<input :type="type || 'text'" :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />`,
    }),
    'el-button': {
      props: ['dataTest', 'text', 'loading'],
      emits: ['click'],
      template: '<button :data-test="dataTest" @click="$emit(\'click\')"><slot /></button>',
    },
  },
}

const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
  await nextTick()
}

const deferred = () => {
  let resolve
  let reject

  const promise = new Promise((nextResolve, nextReject) => {
    resolve = nextResolve
    reject = nextReject
  })

  return { promise, resolve, reject }
}

describe('Task 11 guarded views', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    window.localStorage.clear()
    useAuth().logout()
  })

  test('MerchantDetailView keeps loading until dish data resolves and uses the fetched merchant id', async () => {
    const dishesRequest = deferred()
    listMerchantDishes.mockReturnValueOnce(dishesRequest.promise)

    const wrapper = mount(MerchantDetailView, {
      props: { merchantId: 42 },
      global,
    })

    expect(listMerchantDishes).toHaveBeenCalledWith(42)
    expect(wrapper.text()).toContain('加载中...')

    dishesRequest.resolve([
      { id: 7, name: '宫保鸡丁', description: '招牌微辣', price: 24 },
    ])
    await flushPromises()

    expect(wrapper.text()).toContain('宫保鸡丁')
    expect(wrapper.text()).toContain('招牌微辣')
    expect(wrapper.text()).toContain('¥24.00')
    expect(wrapper.text()).not.toContain('加载中...')
    expect(wrapper.text()).not.toContain('暂无菜品')
  })

  test('MerchantDetailView renders the thrown error message when loading fails', async () => {
    const dishesRequest = deferred()
    listMerchantDishes.mockReturnValueOnce(dishesRequest.promise)

    const wrapper = mount(MerchantDetailView, {
      props: { merchantId: 42 },
      global,
    })

    expect(listMerchantDishes).toHaveBeenCalledWith(42)
    expect(wrapper.text()).toContain('加载中...')

    dishesRequest.reject(new Error('商家加载失败'))
    await flushPromises()

    expect(wrapper.text()).toContain('商家加载失败')
    expect(wrapper.text()).not.toContain('加载中...')
  })

  test('OrderDetailView renders an empty state when no orders are available', async () => {
    const ordersRequest = deferred()
    listOrders.mockReturnValueOnce(ordersRequest.promise)

    const wrapper = mount(OrderDetailView, { global })

    expect(wrapper.text()).toContain('加载中...')

    ordersRequest.resolve([])
    await flushPromises()

    expect(getOrderDetail).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('暂无订单详情')
    expect(wrapper.text()).not.toContain('加载中...')
  })

  test('OrderDetailView loads the first fetched order detail instead of a hardcoded id', async () => {
    const ordersRequest = deferred()
    const detailRequest = deferred()
    listOrders.mockReturnValueOnce(ordersRequest.promise)
    getOrderDetail.mockReturnValueOnce(detailRequest.promise)

    const wrapper = mount(OrderDetailView, { global })

    expect(wrapper.text()).toContain('加载中...')

    ordersRequest.resolve([{ checkout_order_id: 88 }])
    await flushPromises()

    expect(getOrderDetail).toHaveBeenCalledWith(88)
    expect(wrapper.text()).toContain('加载中...')

    detailRequest.resolve({
      checkout_order_id: 88,
      order_status: 'paid',
      merchant_orders: [
        {
          merchant_order_id: 101,
          merchant_id: 5,
          order_status: 'delivering',
          items: [
            {
              dish_id: 9,
              dish_name: '红烧牛肉面',
              quantity: 2,
            },
          ],
        },
      ],
    })
    await flushPromises()

    expect(wrapper.text()).toContain('订单号：#88')
    expect(wrapper.text()).toContain('状态：已支付')
    expect(wrapper.text()).toContain('商家 5')
    expect(wrapper.text()).toContain('子单状态：配送中')
    expect(wrapper.text()).toContain('红烧牛肉面 × 2')
    expect(wrapper.text()).not.toContain('加载中...')
  })

  test('MerchantDetailView loads the merchant passed by prop instead of the first merchant in the list', async () => {
    listMerchantDishes.mockResolvedValueOnce([{ id: 7, name: '宫保鸡丁', description: '招牌微辣', price: 24 }])

    mount(MerchantDetailView, {
      props: { merchantId: 42 },
      global,
    })

    await flushPromises()

    expect(listMerchantDishes).toHaveBeenCalledWith(42)
  })

  test('MerchantListView renders a local cover image for mapped categories', () => {
    const wrapper = mount(MerchantListView, {
      props: {
        merchants: [
          {
            id: 1,
            name: '静安川湘小馆1',
            homepage_category: '湘菜',
            rating: 4.7,
            delivery_fee: 4,
            promo_text: '经典川味',
            district: '静安',
          },
        ],
      },
      global,
    })

    expect(wrapper.find('[data-test="merchant-cover-image"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('湘菜')
  })

  test('AddressView creates an address from the explicit create form', async () => {
    listAddresses
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: 2,
          label: '公司',
          contact_name: '演示用户',
          contact_phone: '13900000001',
          city: '上海',
          district: '长宁',
          detail_address: '延安西路 889 号',
          longitude: 121.41,
          latitude: 31.21,
          is_default: false,
        },
      ])
    createAddress.mockResolvedValueOnce({
      id: 2,
      label: '公司',
      contact_name: '演示用户',
      contact_phone: '13900000001',
      city: '上海',
      district: '长宁',
      detail_address: '延安西路 889 号',
      longitude: 121.41,
      latitude: 31.21,
      is_default: false,
    })

    const wrapper = mount(AddressView, { global })
    await flushPromises()

    const createButton = wrapper.find('[data-test="open-create-address"]')
    expect(createButton.exists()).toBe(true)

    await createButton.trigger('click')
    await wrapper.find('[data-test="address-label-input"]').setValue('公司')
    await wrapper.find('[data-test="address-contact-name-input"]').setValue('演示用户')
    await wrapper.find('[data-test="address-contact-phone-input"]').setValue('13900000001')
    await wrapper.find('[data-test="address-city-input"]').setValue('上海')
    await wrapper.find('[data-test="address-district-input"]').setValue('长宁')
    await wrapper.find('[data-test="address-detail-input"]').setValue('延安西路 889 号')
    await wrapper.find('[data-test="address-longitude-input"]').setValue('121.41')
    await wrapper.find('[data-test="address-latitude-input"]').setValue('31.21')
    await wrapper.find('[data-test="address-form"]').trigger('submit')
    await flushPromises()

    expect(createAddress).toHaveBeenCalledWith({
      label: '公司',
      contact_name: '演示用户',
      contact_phone: '13900000001',
      city: '上海',
      district: '长宁',
      detail_address: '延安西路 889 号',
      longitude: 121.41,
      latitude: 31.21,
      is_default: false,
    })
    expect(wrapper.text()).toContain('公司')
    expect(wrapper.text()).toContain('延安西路 889 号')
  })

  test('AddressView updates an address from the explicit edit form', async () => {
    listAddresses
      .mockResolvedValueOnce([
        {
          id: 1,
          label: '家',
          contact_name: '演示用户',
          contact_phone: '13800000000',
          city: '上海',
          district: '静安',
          detail_address: '南京西路 818 号',
          longitude: 121.45,
          latitude: 31.22,
          is_default: false,
        },
      ])
      .mockResolvedValueOnce([
        {
          id: 1,
          label: '公司',
          contact_name: '演示用户',
          contact_phone: '13800000000',
          city: '上海',
          district: '静安',
          detail_address: '南京西路 818 号 9 楼',
          longitude: 121.45,
          latitude: 31.22,
          is_default: false,
        },
      ])
    updateAddress.mockResolvedValueOnce({
      id: 1,
      label: '公司',
      contact_name: '演示用户',
      contact_phone: '13800000000',
      city: '上海',
      district: '静安',
      detail_address: '南京西路 818 号 9 楼',
      longitude: 121.45,
      latitude: 31.22,
      is_default: false,
    })

    const wrapper = mount(AddressView, { global })
    await flushPromises()

    await wrapper.find('[data-test="edit-address-1"]').trigger('click')
    await wrapper.find('[data-test="address-label-input"]').setValue('公司')
    await wrapper.find('[data-test="address-detail-input"]').setValue('南京西路 818 号 9 楼')
    await wrapper.find('[data-test="address-form"]').trigger('submit')
    await flushPromises()

    expect(updateAddress).toHaveBeenCalledWith(1, {
      label: '公司',
      contact_name: '演示用户',
      contact_phone: '13800000000',
      city: '上海',
      district: '静安',
      detail_address: '南京西路 818 号 9 楼',
      longitude: 121.45,
      latitude: 31.22,
      is_default: false,
    })
    expect(wrapper.text()).toContain('公司')
    expect(wrapper.text()).toContain('南京西路 818 号 9 楼')
  })

  test('AddressView can set an address as default from the dialog action area', async () => {
    listAddresses
      .mockResolvedValueOnce([
        {
          id: 1,
          label: '家',
          contact_name: '演示用户',
          contact_phone: '13800000000',
          city: '上海',
          district: '静安',
          detail_address: '南京西路 818 号',
          longitude: 121.45,
          latitude: 31.22,
          is_default: false,
        },
      ])
      .mockResolvedValueOnce([
        {
          id: 1,
          label: '家',
          contact_name: '演示用户',
          contact_phone: '13800000000',
          city: '上海',
          district: '静安',
          detail_address: '南京西路 818 号',
          longitude: 121.45,
          latitude: 31.22,
          is_default: true,
        },
      ])
    setDefaultAddress.mockResolvedValueOnce({ success: true, address_id: 1 })
    updateAddress.mockResolvedValueOnce({
      id: 1,
      label: '公司',
      contact_name: '演示用户',
      contact_phone: '13800000000',
      city: '上海',
      district: '静安',
      detail_address: '南京西路 818 号 9 楼',
      longitude: 121.45,
      latitude: 31.22,
      is_default: true,
    })

    const wrapper = mount(AddressView, { global })
    await flushPromises()

    await wrapper.find('[data-test="set-default-1"]').trigger('click')
    await flushPromises()

    expect(setDefaultAddress).toHaveBeenCalledWith(1)
  })

  test('CheckoutView deletes a cart row and refreshes grouped cart data', async () => {
    getCart
      .mockResolvedValueOnce({
        items: [
          {
            merchant_id: 5,
            merchant_name: '川湘小馆',
            items: [{ dish_id: 9, dish_name: '红烧牛肉面', quantity: 2, unit_price: 19 }],
            subtotal: 38,
          },
        ],
        goods_amount: 38,
      })
      .mockResolvedValueOnce({ items: [], goods_amount: 0 })
    removeCartItem.mockResolvedValueOnce({ success: true, dish_id: 9 })

    const wrapper = mount(CheckoutView, { global })
    await flushPromises()

    expect(wrapper.text()).toContain('川湘小馆')
    expect(wrapper.text()).toContain('红烧牛肉面')
    expect(wrapper.text()).toContain('¥19.00')

    await wrapper.find('[data-test="remove-cart-item-9"]').trigger('click')
    await flushPromises()

    expect(removeCartItem).toHaveBeenCalledWith(9)
    expect(getCart).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('购物车为空')
  })

  test('CheckoutView renders grouped cart rows, total, and disables checkout when empty', async () => {
    getCart.mockResolvedValueOnce({
      items: [
        {
          merchant_id: 5,
          merchant_name: '川湘小馆',
          items: [
            { dish_id: 9, dish_name: '红烧牛肉面', quantity: 2, unit_price: 19 },
            { dish_id: 10, dish_name: '宫保鸡丁', quantity: 1, unit_price: 24 },
          ],
          subtotal: 62,
        },
      ],
      goods_amount: 62,
    })

    const wrapper = mount(CheckoutView, { global })
    await flushPromises()

    expect(wrapper.text()).toContain('川湘小馆')
    expect(wrapper.text()).toContain('红烧牛肉面')
    expect(wrapper.text()).toContain('宫保鸡丁')
    expect(wrapper.text()).toContain('¥19.00')
    expect(wrapper.text()).toContain('¥24.00')
    expect(wrapper.text()).toContain('× 2')
    expect(wrapper.text()).toContain('小计 ¥62.00')
    expect(wrapper.text()).toContain('商品总价 ¥62.00')
  })

  test('MerchantDetailView adds a dish to the persisted cart when logged in', async () => {
    useAuth().currentUser.value = {
      id: 2,
      username: 'new_user',
      full_name: '新用户',
      phone: '13900000000',
    }
    listMerchantDishes.mockResolvedValueOnce([
      { id: 7, name: '宫保鸡丁', description: '招牌微辣', price: 24 },
    ])
    addCartItem.mockResolvedValueOnce({
      items: [
        {
          merchant_id: 42,
          merchant_name: '川湘小馆',
          items: [{ dish_id: 7, dish_name: '宫保鸡丁', quantity: 1, unit_price: 24 }],
          subtotal: 24,
        },
      ],
      goods_amount: 24,
    })

    const wrapper = mount(MerchantDetailView, {
      props: { merchantId: 42 },
      global,
    })
    await flushPromises()

    await wrapper.find('[data-test="add-cart-7"]').trigger('click')
    await flushPromises()

    expect(addCartItem).toHaveBeenCalledWith({ dish_id: 7, quantity: 1 })
  })

  test('MerchantDetailView emits request-login instead of adding to cart when logged out', async () => {
    useAuth().logout()
    listMerchantDishes.mockResolvedValueOnce([
      { id: 7, name: '宫保鸡丁', description: '招牌微辣', price: 24 },
    ])

    const wrapper = mount(MerchantDetailView, {
      props: { merchantId: 42 },
      global,
    })
    await flushPromises()

    await wrapper.find('[data-test="add-cart-7"]').trigger('click')

    expect(addCartItem).not.toHaveBeenCalled()
    expect(wrapper.emitted('request-login')).toBeTruthy()
  })

  test('LoginView consumes the register session directly and emits auth-success', async () => {
    register.mockResolvedValueOnce({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
      user: {
        id: 2,
        username: 'new_user',
        full_name: '新用户',
        phone: '13900000000',
      },
      addresses: [],
    })

    const wrapper = mount(LoginView, { global })

    await wrapper.find('[data-test="switch-to-register"]').trigger('click')
    await wrapper.find('[data-test="username-input"]').setValue('new_user')
    await wrapper.find('[data-test="password-input"]').setValue('strongpass')
    await wrapper.find('[data-test="full-name-input"]').setValue('新用户')
    await wrapper.find('[data-test="phone-input"]').setValue('13900000000')
    await wrapper.find('[data-test="register-submit"]').trigger('click')
    await flushPromises()

    expect(register).toHaveBeenCalledWith({
      username: 'new_user',
      password: 'strongpass',
      full_name: '新用户',
      phone: '13900000000',
    })
    expect(login).not.toHaveBeenCalled()
    expect(wrapper.emitted('auth-success')).toBeTruthy()
  })

  test('HomeHeader renders the Meituan-style current-user nav', () => {
    const wrapper = mount(HomeHeader, {
      props: {
        currentUser: {
          id: 2,
          username: 'new_user',
          full_name: '新用户',
          phone: '13900000000',
        },
      },
      global,
    })

    expect(wrapper.text()).toContain('smart_order')
    expect(wrapper.text()).toContain('上海')
    expect(wrapper.text()).toContain('我的订单')
    expect(wrapper.text()).toContain('收藏')
    expect(wrapper.text()).toContain('购物车')
    expect(wrapper.find('.avatar').text()).toBe('N')
  })
})

