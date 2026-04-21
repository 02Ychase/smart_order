import { beforeEach, describe, expect, test, vi } from 'vitest'
import { useHomepage } from '../composables/useHomepage'

const { listMerchants } = vi.hoisted(() => ({
  listMerchants: vi.fn(),
}))

vi.mock('../api/catalog', () => ({
  listMerchants,
}))

describe('homepage state', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('filters merchants by homepage category and keeps the selected merchant id', async () => {
    listMerchants.mockResolvedValueOnce([
      { id: 1, name: '静安川湘小馆1', homepage_category: '川菜', promo_text: '经典川味', rating: 4.7, delivery_fee: 4 },
      { id: 2, name: '静安咖啡甜点站1', homepage_category: '奶茶咖啡', promo_text: '甜点咖啡精选', rating: 4.8, delivery_fee: 3 },
    ])

    const homepage = useHomepage()
    await homepage.loadMerchants()

    expect(homepage.categories.value).toContain('全部')
    expect(homepage.categories.value).toContain('川菜')
    expect(homepage.filteredMerchants.value).toHaveLength(2)

    homepage.selectCategory('川菜')
    expect(homepage.filteredMerchants.value.map((merchant) => merchant.id)).toEqual([1])

    homepage.selectMerchant(2)
    expect(homepage.selectedMerchantId.value).toBe(2)
  })
})
