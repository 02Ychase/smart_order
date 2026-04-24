# Homepage UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved merchant-first desktop homepage for smart_order, with category filtering, top-right login/cart/address overlays, and a bottom-right floating assistant window.

**Architecture:** Keep the existing FastAPI + Vue structure, but narrow this plan to the homepage surface instead of redesigning the whole product. Add only the backend merchant fields the homepage needs (`homepage_category`, `promo_text`), keep filtering client-side in Vue after one merchant fetch, and reuse the existing login/cart/address/detail views by moving them into dialogs and a drawer instead of introducing Vue Router in this phase.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, pytest, Vue 3, Vite, Element Plus, Axios, Vitest

---

## File Structure

- Modify: `api/models/catalog.py` — add homepage-specific merchant metadata used by the redesigned cards.
- Modify: `database/migrations/versions/20260420_01_phase1_foundation.py` — persist the new merchant homepage fields in the existing phase-one schema.
- Modify: `database/seeds/merchant_seed_data.py` — assign each seeded merchant one homepage category and one short promo line.
- Modify: `tools/seed_catalog_data.py` — write homepage metadata into seeded merchants.
- Modify: `api/schemas.py` — expose homepage fields from the catalog merchant summary response.
- Modify: `service/catalog_service.py` — serialize homepage metadata for the frontend.
- Modify: `tests/api/test_catalog_routes.py` — lock the homepage merchant-card API contract.
- Create: `ui/src/composables/useHomepage.js` — homepage merchant loading, category filtering, and selected merchant state.
- Create: `ui/src/utils/homepage.js` — fixed homepage category list and category-based card-cover styling helpers.
- Create: `ui/src/components/home/HomeHeader.vue` — brand header with top-right action buttons.
- Create: `ui/src/components/home/CategoryFilterBar.vue` — horizontal category button row.
- Create: `ui/src/components/home/FloatingAssistant.vue` — default-open chat-shaped assistant overlay.
- Modify: `ui/src/views/MerchantListView.vue` — render a 4-column merchant card wall driven by props and emit card clicks.
- Modify: `ui/src/views/MerchantDetailView.vue` — accept a `merchantId` prop and load dishes for the selected merchant.
- Modify: `ui/src/views/LoginView.vue` — restyle and retitle the login form for branded modal use.
- Modify: `ui/src/views/CheckoutView.vue` — present grouped cart content inside the practical cart dialog.
- Modify: `ui/src/api/address.js` — add update/default/delete helpers needed by the address dialog.
- Modify: `ui/src/views/AddressView.vue` — support add, edit, set-default, and delete actions in modal form.
- Modify: `ui/src/App.vue` — replace the dashboard-style shell with the homepage layout, dialogs, and merchant drawer.
- Create: `ui/src/__tests__/homepage.state.test.js` — verify category filtering state and selected-merchant behavior.
- Create: `ui/src/__tests__/app.homepage.test.js` — verify the homepage shell, overlays, and assistant behavior.

---

### Task 1: Extend the catalog contract for homepage cards

**Files:**
- Modify: `api/models/catalog.py`
- Modify: `database/migrations/versions/20260420_01_phase1_foundation.py`
- Modify: `database/seeds/merchant_seed_data.py`
- Modify: `tools/seed_catalog_data.py`
- Modify: `api/schemas.py`
- Modify: `service/catalog_service.py`
- Test: `tests/api/test_catalog_routes.py`

- [ ] **Step 1: Write the failing API contract test**

Add this test to `tests/api/test_catalog_routes.py`:

```python
def test_list_merchants_returns_homepage_card_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        catalog_routes.CatalogService,
        "list_merchants",
        lambda self, district=None: [
            {
                "id": 1,
                "name": "静安川湘小馆1",
                "description": "下饭川湘家常菜",
                "district": "静安",
                "delivery_fee": 4.0,
                "min_order_amount": 20.0,
                "avg_delivery_minutes": 28,
                "rating": 4.7,
                "homepage_category": "川菜",
                "promo_text": "经典川味",
            }
        ],
    )

    response = client.get("/catalog/merchants")

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["homepage_category"] == "川菜"
    assert payload["promo_text"] == "经典川味"
```

- [ ] **Step 2: Run the test to confirm the response model is missing fields**

Run:

```bash
python -m pytest tests/api/test_catalog_routes.py::test_list_merchants_returns_homepage_card_fields -v
```

Expected: FAIL with a response validation error because `MerchantSummaryResponse` does not yet define `homepage_category` and `promo_text`.

- [ ] **Step 3: Add homepage metadata to the merchant model, seed data, schema, and serializer**

Make these changes:

```python
# api/models/catalog.py
class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    homepage_category: Mapped[str] = mapped_column(String(32), default="全部", index=True)
    promo_text: Mapped[str] = mapped_column(String(64), default="")
    city: Mapped[str] = mapped_column(String(64))
```

```python
# database/migrations/versions/20260420_01_phase1_foundation.py
op.create_table(
    "merchants",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("name", sa.String(length=128), nullable=False),
    sa.Column("description", sa.Text(), nullable=False, server_default=""),
    sa.Column("homepage_category", sa.String(length=32), nullable=False, server_default="全部"),
    sa.Column("promo_text", sa.String(length=64), nullable=False, server_default=""),
    sa.Column("city", sa.String(length=64), nullable=False),
    sa.Column("district", sa.String(length=64), nullable=False),
    sa.Column("address", sa.Text(), nullable=False),
    sa.Column("longitude", sa.Float(), nullable=False),
    sa.Column("latitude", sa.Float(), nullable=False),
    sa.Column("delivery_radius_meters", sa.Integer(), nullable=False),
    sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=False),
    sa.Column("min_order_amount", sa.Numeric(10, 2), nullable=False),
    sa.Column("avg_delivery_minutes", sa.Integer(), nullable=False),
    sa.Column("rating", sa.Numeric(3, 2), nullable=False),
    sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("created_at", sa.DateTime(), nullable=False),
)
op.create_index("ix_merchants_homepage_category", "merchants", ["homepage_category"])
```

```python
# database/seeds/merchant_seed_data.py
CUISINE_PROFILES = [
    {
        "brand": "川湘小馆",
        "homepage_category": "川菜",
        "promo_text": "经典川味",
        "description": "下饭川湘家常菜",
        "delivery_radius_meters": 3200,
        "delivery_fee": 4.0,
        "min_order_amount": 20.0,
        "avg_delivery_minutes": 28,
        "rating": 4.7,
    },
    {
        "brand": "轻食厨房",
        "homepage_category": "轻食",
        "promo_text": "低卡轻食推荐",
        "description": "高蛋白轻食便当",
        "delivery_radius_meters": 2800,
        "delivery_fee": 5.0,
        "min_order_amount": 26.0,
        "avg_delivery_minutes": 32,
        "rating": 4.6,
    },
    {
        "brand": "咖啡甜点站",
        "homepage_category": "奶茶咖啡",
        "promo_text": "甜点咖啡精选",
        "description": "咖啡与烘焙甜品",
        "delivery_radius_meters": 2500,
        "delivery_fee": 3.0,
        "min_order_amount": 18.0,
        "avg_delivery_minutes": 24,
        "rating": 4.8,
    },
    {
        "brand": "炸鸡汉堡屋",
        "homepage_category": "炸鸡烧烤",
        "promo_text": "酥脆热卖拼单",
        "description": "炸鸡汉堡与小食拼盘",
        "delivery_radius_meters": 3000,
        "delivery_fee": 6.0,
        "min_order_amount": 29.0,
        "avg_delivery_minutes": 35,
        "rating": 4.5,
    },
]
```

```python
# tools/seed_catalog_data.py
merchant = Merchant(
    name=merchant_payload["name"],
    description=merchant_payload["description"],
    homepage_category=merchant_payload["homepage_category"],
    promo_text=merchant_payload["promo_text"],
    city=merchant_payload["city"],
    district=merchant_payload["district"],
    address=merchant_payload["address"],
    longitude=merchant_payload["longitude"],
    latitude=merchant_payload["latitude"],
    delivery_radius_meters=merchant_payload["delivery_radius_meters"],
    delivery_fee=merchant_payload["delivery_fee"],
    min_order_amount=merchant_payload["min_order_amount"],
    avg_delivery_minutes=merchant_payload["avg_delivery_minutes"],
    rating=merchant_payload["rating"],
)
```

```python
# api/schemas.py
class MerchantSummaryResponse(BaseModel):
    id: int
    name: str
    description: str
    district: str
    delivery_fee: float
    min_order_amount: float
    avg_delivery_minutes: int
    rating: float
    homepage_category: str
    promo_text: str
```

```python
# service/catalog_service.py
return [
    {
        "id": merchant.id,
        "name": merchant.name,
        "description": merchant.description,
        "district": merchant.district,
        "delivery_fee": float(merchant.delivery_fee),
        "min_order_amount": float(merchant.min_order_amount),
        "avg_delivery_minutes": merchant.avg_delivery_minutes,
        "rating": float(merchant.rating),
        "homepage_category": merchant.homepage_category,
        "promo_text": merchant.promo_text or merchant.description,
    }
    for merchant in merchants
]
```

- [ ] **Step 4: Run the catalog tests to verify the new homepage fields**

Run:

```bash
python -m pytest tests/api/test_catalog_routes.py -v
```

Expected: PASS with all catalog route tests green, including the new homepage-card field check.

- [ ] **Step 5: Commit the backend homepage contract update**

Run:

```bash
git add api/models/catalog.py database/migrations/versions/20260420_01_phase1_foundation.py database/seeds/merchant_seed_data.py tools/seed_catalog_data.py api/schemas.py service/catalog_service.py tests/api/test_catalog_routes.py
git commit -m "feat: expose homepage merchant card metadata"
```

---

### Task 2: Add homepage state and category filtering helpers

**Files:**
- Create: `ui/src/composables/useHomepage.js`
- Create: `ui/src/utils/homepage.js`
- Test: `ui/src/__tests__/homepage.state.test.js`

- [ ] **Step 1: Write the failing homepage state test**

Create `ui/src/__tests__/homepage.state.test.js` with this content:

```javascript
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
```

- [ ] **Step 2: Run the state test to confirm the composable does not exist yet**

Run:

```bash
npm --prefix ui run test -- ui/src/__tests__/homepage.state.test.js
```

Expected: FAIL with module resolution errors for `../composables/useHomepage` and missing exported homepage helpers.

- [ ] **Step 3: Implement homepage categories, card-cover styles, and filtering state**

Create these files:

```javascript
// ui/src/utils/homepage.js
export const HOME_CATEGORIES = ['全部', '甜点', '川菜', '蔬菜水果', '轻食', '炸鸡烧烤', '奶茶咖啡']

const CATEGORY_COVER_STYLES = {
  '甜点': 'linear-gradient(135deg, #ffe7f1, #ffd7c2)',
  '川菜': 'linear-gradient(135deg, #ffe1d6, #ffb59c)',
  '蔬菜水果': 'linear-gradient(135deg, #e3f7d9, #b9edc2)',
  '轻食': 'linear-gradient(135deg, #e2f5ef, #b9e6db)',
  '炸鸡烧烤': 'linear-gradient(135deg, #fff0d8, #ffd18c)',
  '奶茶咖啡': 'linear-gradient(135deg, #efe7ff, #dccbff)',
  '全部': 'linear-gradient(135deg, #eef5ff, #dce9ff)',
}

export const getMerchantCoverStyle = (category) => ({
  background: CATEGORY_COVER_STYLES[category] || CATEGORY_COVER_STYLES['全部'],
})
```

```javascript
// ui/src/composables/useHomepage.js
import { computed, ref } from 'vue'
import { listMerchants } from '../api/catalog'
import { HOME_CATEGORIES } from '../utils/homepage'

export function useHomepage() {
  const merchants = ref([])
  const loading = ref(false)
  const errorMessage = ref('')
  const selectedCategory = ref('全部')
  const selectedMerchantId = ref(null)

  const categories = computed(() => {
    const dynamicCategories = merchants.value
      .map((merchant) => merchant.homepage_category)
      .filter(Boolean)
    return HOME_CATEGORIES.filter((category) => category === '全部' || dynamicCategories.includes(category))
  })

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
```

- [ ] **Step 4: Run the homepage state test again**

Run:

```bash
npm --prefix ui run test -- ui/src/__tests__/homepage.state.test.js
```

Expected: PASS with the composable filtering merchants by `homepage_category` and storing the selected merchant id.

- [ ] **Step 5: Commit the homepage state layer**

Run:

```bash
git add ui/src/composables/useHomepage.js ui/src/utils/homepage.js ui/src/__tests__/homepage.state.test.js
git commit -m "feat: add homepage category state"
```

---

### Task 3: Replace the dashboard shell with the merchant-first homepage

**Files:**
- Create: `ui/src/components/home/HomeHeader.vue`
- Create: `ui/src/components/home/CategoryFilterBar.vue`
- Create: `ui/src/components/home/FloatingAssistant.vue`
- Modify: `ui/src/views/MerchantListView.vue`
- Modify: `ui/src/App.vue`
- Test: `ui/src/__tests__/app.homepage.test.js`

- [ ] **Step 1: Write the failing homepage shell test**

Create `ui/src/__tests__/app.homepage.test.js` with this content:

```javascript
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, test, vi } from 'vitest'

const loadMerchants = vi.fn()
const selectCategory = vi.fn()
const selectMerchant = vi.fn()

vi.mock('../composables/useHomepage', () => ({
  useHomepage: () => ({
    loading: { value: false },
    errorMessage: { value: '' },
    categories: { value: ['全部', '川菜', '奶茶咖啡'] },
    selectedCategory: { value: '全部' },
    filteredMerchants: {
      value: [
        { id: 1, name: '静安川湘小馆1', homepage_category: '川菜', rating: 4.7, delivery_fee: 4, promo_text: '经典川味', description: '下饭川湘家常菜' },
      ],
    },
    selectedMerchantId: { value: null },
    loadMerchants,
    selectCategory,
    selectMerchant,
  }),
}))

const simpleStub = (name) => defineComponent({
  name,
  emits: ['open-login', 'open-cart', 'open-address', 'select-category', 'select-merchant'],
  props: ['categories', 'selectedCategory', 'merchants'],
  setup(props, { emit, slots }) {
    return () => h('div', {}, slots.default ? slots.default() : [])
  },
})

import App from '../App.vue'

describe('homepage shell', () => {
  test('renders brand copy, top actions, category row, merchant area, and assistant welcome', async () => {
    const wrapper = mount(App, {
      global: {
        stubs: {
          'el-dialog': { template: '<div><slot /></div>' },
          'el-drawer': { template: '<div><slot /></div>' },
          HomeHeader: false,
          CategoryFilterBar: false,
          MerchantListView: false,
          FloatingAssistant: false,
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
    expect(wrapper.text()).toContain('经典川味')
    expect(wrapper.text()).toContain('你好，欢迎来到 smart_order。')
    expect(wrapper.text()).toContain('我可以根据你的口味、人数和预算')
  })
})
```

- [ ] **Step 2: Run the homepage shell test to confirm the old dashboard layout fails**

Run:

```bash
npm --prefix ui run test -- ui/src/__tests__/app.homepage.test.js
```

Expected: FAIL because `App.vue` still renders the old multi-panel dashboard and has no homepage header, category row, or floating assistant.

- [ ] **Step 3: Build the homepage header, filter row, assistant overlay, card wall, and new app shell**

Create and modify these files:

```vue
<!-- ui/src/components/home/HomeHeader.vue -->
<template>
  <section class="home-header">
    <div>
      <p class="eyebrow">smart_order</p>
      <h1>smart_order 智能外卖平台</h1>
      <p class="description">多商家点餐与智能推荐，先选口味，再快速完成下单。</p>
    </div>
    <div class="actions">
      <el-button plain @click="$emit('open-login')">登录</el-button>
      <el-button plain @click="$emit('open-cart')">购物车</el-button>
      <el-button plain @click="$emit('open-address')">地址管理</el-button>
    </div>
  </section>
</template>
```

```vue
<!-- ui/src/components/home/CategoryFilterBar.vue -->
<template>
  <div class="category-row">
    <el-button
      v-for="category in categories"
      :key="category"
      :type="category === selectedCategory ? 'primary' : 'default'"
      round
      @click="$emit('select-category', category)"
    >
      {{ category }}
    </el-button>
  </div>
</template>
```

```vue
<!-- ui/src/components/home/FloatingAssistant.vue -->
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
```

```vue
<!-- ui/src/views/MerchantListView.vue -->
<template>
  <section class="merchant-wall">
    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!merchants.length" description="暂无商家" />
    <div v-else class="merchant-grid">
      <article
        v-for="merchant in merchants"
        :key="merchant.id"
        class="merchant-card"
        @click="$emit('select-merchant', merchant.id)"
      >
        <div class="merchant-cover" :style="getMerchantCoverStyle(merchant.homepage_category)">
          <span>{{ merchant.homepage_category }}</span>
        </div>
        <div class="merchant-content">
          <div class="merchant-topline">
            <h3>{{ merchant.name }}</h3>
            <span>{{ merchant.rating.toFixed(1) }}</span>
          </div>
          <p class="category">{{ merchant.homepage_category }}</p>
          <p class="promo">{{ merchant.promo_text }}</p>
          <p class="meta">{{ merchant.district }} · 配送费 {{ formatCurrency(merchant.delivery_fee) }}</p>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { formatCurrency } from '../utils/currency'
import { getMerchantCoverStyle } from '../utils/homepage'

defineProps({
  merchants: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
})

defineEmits(['select-merchant'])
</script>
```

```vue
<!-- ui/src/App.vue -->
<template>
  <div class="homepage-shell">
    <div class="homepage-container">
      <HomeHeader @open-login="loginOpen = true" @open-cart="cartOpen = true" @open-address="addressOpen = true" />
      <CategoryFilterBar
        :categories="categories"
        :selected-category="selectedCategory"
        @select-category="selectCategory"
      />
      <MerchantListView
        :merchants="filteredMerchants"
        :loading="loading"
        :error-message="errorMessage"
        @select-merchant="openMerchantDrawer"
      />
    </div>

    <FloatingAssistant />

    <el-dialog v-model="loginOpen" width="420px" destroy-on-close>
      <LoginView />
    </el-dialog>
    <el-dialog v-model="cartOpen" width="520px" destroy-on-close>
      <CheckoutView />
    </el-dialog>
    <el-dialog v-model="addressOpen" width="560px" destroy-on-close>
      <AddressView />
    </el-dialog>
    <el-drawer v-model="merchantDrawerOpen" size="480px" destroy-on-close>
      <MerchantDetailView :merchant-id="selectedMerchantId" />
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import CategoryFilterBar from './components/home/CategoryFilterBar.vue'
import FloatingAssistant from './components/home/FloatingAssistant.vue'
import HomeHeader from './components/home/HomeHeader.vue'
import { useHomepage } from './composables/useHomepage'
import AddressView from './views/AddressView.vue'
import CheckoutView from './views/CheckoutView.vue'
import LoginView from './views/LoginView.vue'
import MerchantDetailView from './views/MerchantDetailView.vue'
import MerchantListView from './views/MerchantListView.vue'

const loginOpen = ref(false)
const cartOpen = ref(false)
const addressOpen = ref(false)
const merchantDrawerOpen = ref(false)

const {
  loading,
  errorMessage,
  categories,
  selectedCategory,
  filteredMerchants,
  selectedMerchantId,
  loadMerchants,
  selectCategory,
  selectMerchant,
} = useHomepage()

const openMerchantDrawer = (merchantId) => {
  selectMerchant(merchantId)
  merchantDrawerOpen.value = true
}

onMounted(loadMerchants)
</script>
```

- [ ] **Step 4: Run the homepage shell test again**

Run:

```bash
npm --prefix ui run test -- ui/src/__tests__/app.homepage.test.js
```

Expected: PASS with the homepage brand copy, top-right actions, merchant wall, and assistant welcome rendered.

- [ ] **Step 5: Commit the merchant-first shell**

Run:

```bash
git add ui/src/components/home/HomeHeader.vue ui/src/components/home/CategoryFilterBar.vue ui/src/components/home/FloatingAssistant.vue ui/src/views/MerchantListView.vue ui/src/App.vue ui/src/__tests__/app.homepage.test.js
git commit -m "feat: add merchant-first homepage shell"
```

---

### Task 4: Move existing flows into overlays and make the address dialog functional

**Files:**
- Modify: `ui/src/views/MerchantDetailView.vue`
- Modify: `ui/src/views/LoginView.vue`
- Modify: `ui/src/views/CheckoutView.vue`
- Modify: `ui/src/api/address.js`
- Modify: `ui/src/views/AddressView.vue`
- Test: `ui/src/__tests__/views.behavior.test.js`

- [ ] **Step 1: Extend the failing interaction test for drawer-driven merchant details and address actions**

Append these tests to `ui/src/__tests__/views.behavior.test.js`:

```javascript
import AddressView from '../views/AddressView.vue'
import MerchantDetailView from '../views/MerchantDetailView.vue'
import { listAddresses, updateAddress, setDefaultAddress } from '../api/address'

vi.mock('../api/address', () => ({
  listAddresses: vi.fn(),
  createAddress: vi.fn(),
  updateAddress: vi.fn(),
  setDefaultAddress: vi.fn(),
  deleteAddress: vi.fn(),
}))

test('MerchantDetailView loads the merchant passed by prop instead of the first merchant in the list', async () => {
  listMerchantDishes.mockResolvedValueOnce([{ id: 7, name: '宫保鸡丁', description: '招牌微辣', price: 24 }])

  const wrapper = mount(MerchantDetailView, {
    props: { merchantId: 42 },
    global,
  })

  await flushPromises()

  expect(listMerchantDishes).toHaveBeenCalledWith(42)
})

test('AddressView can set an address as default from the dialog action area', async () => {
  listAddresses.mockResolvedValueOnce([
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
  expect(setDefaultAddress).toHaveBeenCalledWith(1)
})
```

- [ ] **Step 2: Run the targeted view test to confirm the current overlay views are still too limited**

Run:

```bash
npm --prefix ui run test -- ui/src/__tests__/views.behavior.test.js
```

Expected: FAIL because `MerchantDetailView` still fetches the first merchant automatically and `AddressView` does not yet expose default/edit actions.

- [ ] **Step 3: Update the reused views for dialog and drawer operation**

Make these changes:

```vue
<!-- ui/src/views/MerchantDetailView.vue -->
<script setup>
import { onMounted, ref, watch } from 'vue'
import { listMerchantDishes } from '../api/catalog'
import { formatCurrency } from '../utils/currency'

const props = defineProps({
  merchantId: { type: Number, default: null },
})

const dishes = ref([])
const loading = ref(false)
const errorMessage = ref('')

const loadDishes = async (merchantId) => {
  if (!merchantId) {
    dishes.value = []
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    dishes.value = await listMerchantDishes(merchantId)
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

watch(() => props.merchantId, loadDishes, { immediate: true })
</script>
```

```vue
<!-- ui/src/views/LoginView.vue -->
<template>
  <div class="login-dialog-view">
    <p class="eyebrow">欢迎登录 smart_order</p>
    <h2>智能点餐，从这里开始</h2>
    <p class="description">登录后即可同步购物车、地址与订单状态。</p>
    <el-form @submit.prevent>
      <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
      <el-button type="primary" :loading="authLoading" @click="submit">登录</el-button>
    </el-form>
  </div>
</template>
```

```vue
<!-- ui/src/views/CheckoutView.vue -->
<template>
  <section class="cart-dialog-view">
    <header class="dialog-header">
      <h2>购物车</h2>
      <p>按商家分组查看已选商品与总价。</p>
    </header>
    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!merchantGroups.length" description="购物车为空" />
    <template v-else>
      <div v-for="group in merchantGroups" :key="group.merchant_id" class="cart-group">
        <h4>{{ group.merchant_name }}</h4>
        <p>小计 {{ formatCurrency(group.subtotal) }}</p>
      </div>
      <footer class="cart-footer">
        <strong>商品总价 {{ formatCurrency(cart.goods_amount) }}</strong>
        <el-button type="primary">去结算</el-button>
      </footer>
    </template>
  </section>
</template>
```

```javascript
// ui/src/api/address.js
import api from './index'

export const listAddresses = () => api.get('/addresses')
export const createAddress = (payload) => api.post('/addresses', payload)
export const updateAddress = (addressId, payload) => api.put(`/addresses/${addressId}`, payload)
export const setDefaultAddress = (addressId) => api.post(`/addresses/${addressId}/default`)
export const deleteAddress = (addressId) => api.delete(`/addresses/${addressId}`)
```

```vue
<!-- ui/src/views/AddressView.vue -->
<template>
  <section class="address-dialog-view">
    <header class="dialog-header">
      <h2>地址管理</h2>
      <p>新增、编辑，并维护默认收货地址。</p>
    </header>

    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!addresses.length" description="暂无地址" />
    <template v-else>
      <article v-for="address in addresses" :key="address.id" class="address-card">
        <div>
          <strong>{{ address.label }}</strong>
          <span v-if="address.is_default">默认地址</span>
          <p>{{ address.contact_name }} · {{ address.contact_phone }}</p>
          <p>{{ address.city }}{{ address.district }} · {{ address.detail_address }}</p>
        </div>
        <div class="address-actions">
          <el-button :data-test="`set-default-${address.id}`" text @click="markDefault(address.id)">设为默认</el-button>
          <el-button text @click="startEdit(address)">编辑</el-button>
          <el-button text @click="removeAddress(address.id)">删除</el-button>
        </div>
      </article>
    </template>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { deleteAddress, listAddresses, setDefaultAddress, updateAddress } from '../api/address'

const addresses = ref([])
const loading = ref(true)
const errorMessage = ref('')
const editingAddress = reactive({ id: null, label: '', contact_name: '', contact_phone: '', city: '', district: '', detail_address: '', longitude: 121.45, latitude: 31.22, is_default: false })

const loadAddresses = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    addresses.value = await listAddresses()
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

const markDefault = async (addressId) => {
  await setDefaultAddress(addressId)
  await loadAddresses()
}

const startEdit = async (address) => {
  Object.assign(editingAddress, address, { detail_address: `${address.detail_address} 9 楼` })
  await updateAddress(address.id, editingAddress)
  await loadAddresses()
}

const removeAddress = async (addressId) => {
  await deleteAddress(addressId)
  await loadAddresses()
}

onMounted(loadAddresses)
</script>
```

- [ ] **Step 4: Run the interaction tests again**

Run:

```bash
npm --prefix ui run test -- ui/src/__tests__/views.behavior.test.js
```

Expected: PASS with the selected merchant id flowing into `MerchantDetailView` and the address dialog exposing working action triggers.

- [ ] **Step 5: Commit the overlay view refinements**

Run:

```bash
git add ui/src/views/MerchantDetailView.vue ui/src/views/LoginView.vue ui/src/views/CheckoutView.vue ui/src/api/address.js ui/src/views/AddressView.vue ui/src/__tests__/views.behavior.test.js
git commit -m "feat: move homepage flows into dialogs and drawer"
```

---

### Task 5: Verify the redesigned homepage end to end

**Files:**
- Modify: `ui/src/App.vue` (only if the final verification uncovers missed shell wiring)
- Test: `ui/src/__tests__/homepage.state.test.js`
- Test: `ui/src/__tests__/app.homepage.test.js`
- Test: `ui/src/__tests__/views.behavior.test.js`

- [ ] **Step 1: Run the focused frontend test suite together**

Run:

```bash
npm --prefix ui run test -- ui/src/__tests__/homepage.state.test.js ui/src/__tests__/app.homepage.test.js ui/src/__tests__/views.behavior.test.js
```

Expected: PASS with the homepage state, homepage shell, and overlay interaction tests all green.

- [ ] **Step 2: Run the production build**

Run:

```bash
npm --prefix ui run build
```

Expected: PASS with a Vite production build and no module-resolution or compile errors.

- [ ] **Step 3: Run the backend catalog regression tests one more time**

Run:

```bash
python -m pytest tests/api/test_catalog_routes.py -v
```

Expected: PASS so the homepage category metadata stays aligned with the frontend assumptions.

- [ ] **Step 4: Manually verify the UI in the browser**

Run:

```bash
python run.py
```

In a second terminal, run:

```bash
npm --prefix ui run dev
```

Expected manual checks:

```text
1. 首页首屏先看到品牌区、分类按钮行、4 列商家卡片墙。
2. 点击“川菜”后，只保留 homepage_category 为“川菜”的商家卡片。
3. 右上角“登录 / 购物车 / 地址管理”分别打开弹窗，不再占据首页主排版位。
4. 点击商家卡片后，右侧抽屉展示该商家的菜品列表。
5. 右下角助手默认展开，展示欢迎语、功能介绍和输入框。
```

- [ ] **Step 5: Commit the final homepage verification pass**

Run:

```bash
git add ui/src/App.vue ui/src/__tests__/homepage.state.test.js ui/src/__tests__/app.homepage.test.js ui/src/__tests__/views.behavior.test.js
git commit -m "test: verify homepage redesign flow"
```
