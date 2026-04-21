import { describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

const { listMerchants } = vi.hoisted(() => ({
  listMerchants: vi.fn(),
}))

vi.mock('../api/catalog', () => ({ listMerchants }))

import { useHomepage } from '../composables/useHomepage'

describe('useHomepage', () => {
  test('builds concrete category buttons from merchant data and filters by the selected category', async () => {
    listMerchants.mockResolvedValueOnce([
      { id: 1, name: '静安川湘小馆1', homepage_category: '湘菜' },
      { id: 2, name: '静安轻食厨房2', homepage_category: '轻食' },
      { id: 3, name: '静安川湘小馆3', homepage_category: '湘菜' },
      { id: 4, name: '静安咖啡甜点站4', homepage_category: '咖啡甜品' },
    ])

    const homepage = useHomepage()
    await homepage.loadMerchants()
    await nextTick()

    expect(homepage.categories.value).toEqual(['全部', '湘菜', '轻食', '咖啡甜品'])

    homepage.selectCategory('轻食')
    expect(homepage.filteredMerchants.value.map((merchant) => merchant.name)).toEqual(['静安轻食厨房2'])
  })
})
