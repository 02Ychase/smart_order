import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, test, vi } from 'vitest'

const { chatWithAssistant } = vi.hoisted(() => ({
  chatWithAssistant: vi.fn(),
}))

vi.mock('../api/assistant', () => ({
  chatWithAssistant,
}))

import FloatingAssistant from '../components/home/FloatingAssistant.vue'

describe('FloatingAssistant', () => {
  test('submits a user message and renders the clarification question', async () => {
    chatWithAssistant.mockResolvedValueOnce({
      session_id: 'session-1',
      message: '请告诉我这顿大概几个人吃、预算多少？',
      needs_clarification: true,
      clarification_question: '请告诉我这顿大概几个人吃、预算多少？',
      extracted_constraints: {
        query_type: 'recommendation',
        cuisine_types: ['川菜'],
        budget_max: null,
        party_size: null,
        exclude_allergens: [],
        comparison_targets: [],
      },
      recommendations: [],
      comparisons: [],
      citations: [],
      suggested_actions: [],
    })

    const wrapper = mount(FloatingAssistant, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          'el-button': {
            emits: ['click'],
            template: '<button @click="$emit(\'click\')"><slot /></button>',
          },
          'el-tag': { template: '<span><slot /></span>' },
          'el-scrollbar': { template: '<div><slot /></div>' },
        },
      },
    })

    await wrapper.find('input').setValue('推荐几种川菜')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(chatWithAssistant).toHaveBeenCalledWith({
      message: '推荐几种川菜',
      session_id: null,
    })
    expect(wrapper.text()).toContain('请告诉我这顿大概几个人吃、预算多少？')
    expect(wrapper.text()).toContain('川菜')
  })

  test('renders recommendation cards and citations from the assistant response', async () => {
    chatWithAssistant.mockResolvedValueOnce({
      session_id: 'session-1',
      message: '我根据你提供的条件整理了更匹配的选项。',
      needs_clarification: false,
      clarification_question: null,
      extracted_constraints: {
        query_type: 'recommendation',
        cuisine_types: ['川菜'],
        budget_max: 100,
        party_size: 2,
        exclude_allergens: ['花生'],
        comparison_targets: [],
      },
      recommendations: [
        {
          source_type: 'dish',
          merchant_id: 1,
          merchant_name: '兰姨小炒',
          dish_id: 11,
          dish_name: '鱼香肉丝',
          price: 28,
          reason: '匹配川菜偏好，单价 28 元，且未命中花生过敏原。',
        },
      ],
      comparisons: [],
      citations: [
        {
          source_type: 'dish',
          source_id: 11,
          title: '鱼香肉丝｜兰姨小炒',
          snippet: '川菜；酸甜微辣；配料为猪里脊、木耳、胡萝卜、青椒',
        },
      ],
      suggested_actions: ['查看商家详情'],
    })

    const wrapper = mount(FloatingAssistant, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          'el-button': {
            emits: ['click'],
            template: '<button @click="$emit(\'click\')"><slot /></button>',
          },
          'el-tag': { template: '<span><slot /></span>' },
          'el-scrollbar': { template: '<div><slot /></div>' },
        },
      },
    })

    await wrapper.find('input').setValue('推荐几种川菜，2个人吃，100元以内，不要花生')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('鱼香肉丝')
    expect(wrapper.text()).toContain('兰姨小炒')
    expect(wrapper.text()).toContain('匹配川菜偏好')
    expect(wrapper.text()).toContain('鱼香肉丝｜兰姨小炒')
  })

  test('renders pending action confirmation', async () => {
    chatWithAssistant.mockResolvedValueOnce({
      session_id: 's1',
      message: '是否加入购物车？',
      response_type: 'confirmation_required',
      recommendations: [],
      comparisons: [],
      citations: [],
      suggested_actions: [],
      pending_action: {
        action_id: 'pa_1',
        type: 'cart_add',
        summary: '将 1 道菜加入购物车',
        items: [{ dish_id: 11, quantity: 1 }],
      },
      executed_actions: [],
    })

    const wrapper = mount(FloatingAssistant, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          'el-button': {
            emits: ['click'],
            template: '<button @click="$emit(\'click\')"><slot /></button>',
          },
          'el-tag': { template: '<span><slot /></span>' },
          'el-scrollbar': { template: '<div><slot /></div>' },
        },
      },
    })

    await wrapper.find('input').setValue('推荐川菜并加入购物车')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('待确认操作')
    expect(wrapper.text()).toContain('将 1 道菜加入购物车')
  })
})
