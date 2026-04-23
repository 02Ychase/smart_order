import { defineComponent, h, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, test, vi } from 'vitest'

const loadMerchants = vi.fn()
const selectCategory = vi.fn()
const selectMerchant = vi.fn()
const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

afterEach(() => {
  consoleWarnSpy.mockClear()
})

vi.mock('../composables/useHomepage', () => ({
  useHomepage: () => ({
    loading: ref(false),
    errorMessage: ref(''),
    categories: ref(['全部', '湘菜', '轻食', '咖啡甜品']),
    selectedCategory: ref('全部'),
    filteredMerchants: ref([
      { id: 1, name: '静安川湘小馆1', homepage_category: '湘菜', rating: 4.7, delivery_fee: 4, promo_text: '经典川味', description: '下饭川湘家常菜' },
    ]),
    selectedMerchantId: ref(null),
    loadMerchants,
    selectCategory,
    selectMerchant,
  }),
}))

const LoginViewStub = defineComponent({
  emits: ['auth-success'],
  template: '<button data-test="login-success" @click="$emit(\'auth-success\')">success</button>',
})

const simpleStub = (name) => defineComponent({
  name,
  emits: ['open-login', 'open-cart', 'open-address', 'select-category', 'select-merchant'],
  props: ['categories', 'selectedCategory', 'merchants'],
  setup(props, { slots }) {
    return () => h('div', {}, slots.default ? slots.default() : [])
  },
})

import App from '../App.vue'

describe('homepage shell', () => {
  test('renders brand copy, top actions, category row, merchant area, and assistant welcome without unresolved component warnings', async () => {
    const wrapper = mount(App, {
      global: {
        stubs: {
          'el-dialog': { template: '<div><slot /></div>' },
          'el-drawer': { template: '<div><slot /></div>' },
          'el-button': { template: '<button><slot /></button>' },
          'el-input': { template: '<input />' },
          'el-empty': { template: '<div class="empty-state"></div>' },
          'el-tag': { template: '<span><slot /></span>' },
          'el-scrollbar': { template: '<div><slot /></div>' },
          HomeHeader: false,
          CategoryFilterBar: false,
          MerchantListView: false,
          FloatingAssistant: false,
          LoginView: simpleStub('LoginView'),
          CheckoutView: simpleStub('CheckoutView'),
          AddressView: simpleStub('AddressView'),
          MerchantDetailView: simpleStub('MerchantDetailView'),
        },
      },
    })

    await nextTick()

    expect(loadMerchants).toHaveBeenCalled()
    expect(wrapper.text()).toContain('smart_order 智能外卖平台')
    expect(wrapper.text()).toContain('登录')
    expect(wrapper.text()).toContain('购物车')
    expect(wrapper.text()).toContain('地址管理')
    expect(wrapper.text()).toContain('全部')
    expect(wrapper.text()).toContain('湘菜')
    expect(wrapper.text()).toContain('经典川味')
    expect(wrapper.text()).toContain('你好，欢迎来到 smart_order。')
    expect(wrapper.text()).toContain('我可以根据你的口味、人数和预算')
    expect(wrapper.text()).toContain('智能助手')
    expect(wrapper.text()).toContain('发送')
    expect(consoleWarnSpy).not.toHaveBeenCalled()
  })


  test('App opens the login dialog when MerchantDetailView requests login for add-to-cart', async () => {
    const MerchantDetailViewStub = defineComponent({
      emits: ['request-login'],
      template: '<button data-test="request-login" @click="$emit(\'request-login\')">request</button>',
    })

    const wrapper = mount(App, {
      global: {
        stubs: {
          'el-dialog': {
            props: ['modelValue'],
            template: '<div v-if="modelValue"><slot /></div>',
          },
          'el-drawer': { template: '<div><slot /></div>' },
          'el-button': { template: '<button><slot /></button>' },
          'el-input': { template: '<input />' },
          'el-empty': { template: '<div class="empty-state"></div>' },
          'el-tag': { template: '<span><slot /></span>' },
          'el-scrollbar': { template: '<div><slot /></div>' },
          HomeHeader: false,
          CategoryFilterBar: false,
          MerchantListView: {
            emits: ['select-merchant'],
            template: '<button data-test="open-merchant" @click="$emit(\'select-merchant\', 42)">merchant</button>',
          },
          FloatingAssistant: false,
          LoginView: LoginViewStub,
          CheckoutView: simpleStub('CheckoutView'),
          AddressView: simpleStub('AddressView'),
          MerchantDetailView: MerchantDetailViewStub,
        },
      },
    })

    await wrapper.find('[data-test="open-merchant"]').trigger('click')
    await nextTick()
    await wrapper.find('[data-test="request-login"]').trigger('click')
    await nextTick()

    expect(wrapper.find('[data-test="login-success"]').exists()).toBe(true)
  })
})


