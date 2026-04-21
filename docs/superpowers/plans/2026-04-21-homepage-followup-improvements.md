# Homepage Follow-up Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the homepage feel like a real delivery marketplace by showing real merchant category filters, real local merchant card images, auto-login after registration with dialog close, and a more diverse seeded merchant catalog.

**Architecture:** Keep the existing backend contract lean by reusing `homepage_category` as the concrete merchant-facing category field, then derive homepage filters directly from fetched merchant data. Move merchant card covers from gradient-only styling to local static SVG assets resolved through a small homepage helper, and reuse the existing `loginWithPassword` token flow after registration so registration success becomes a login success path instead of a separate state.

**Tech Stack:** Vue 3, Vite, Vitest, Element Plus, FastAPI, SQLAlchemy, pytest

---

### Task 1: Expand merchant seed data into concrete homepage categories

**Files:**
- Create: `tests/database/test_merchant_seed_data.py`
- Modify: `database/seeds/merchant_seed_data.py`
- Verify with: `tools/seed_catalog_data.py`

- [ ] **Step 1: Write the failing seed-data test**

```python
from database.seeds.merchant_seed_data import MERCHANT_SEED_DATA


def test_merchant_seed_data_contains_diverse_homepage_categories() -> None:
    categories = {merchant["homepage_category"] for merchant in MERCHANT_SEED_DATA}

    assert {"湘菜", "轻食", "咖啡甜品", "炸鸡汉堡", "粥面", "日韩料理", "麻辣烫", "披萨意面"}.issubset(categories)
    assert len(categories) >= 8
    assert len(MERCHANT_SEED_DATA) >= 40
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation && pytest tests/database/test_merchant_seed_data.py -q
```

Expected: FAIL because `merchant_seed_data.py` only defines four homepage categories and twenty merchants.

- [ ] **Step 3: Expand the cuisine profile list with concrete merchant categories**

Update `database/seeds/merchant_seed_data.py` so `CUISINE_PROFILES` uses concrete categories instead of promo-style labels and includes more distinct merchant types.

```python
CUISINE_PROFILES = [
    {
        "brand": "川湘小馆",
        "description": "下饭川湘家常菜",
        "homepage_category": "湘菜",
        "promo_text": "满39减12，招牌热菜限时折扣",
        ...
    },
    {
        "brand": "轻食厨房",
        "description": "高蛋白轻食便当",
        "homepage_category": "轻食",
        "promo_text": "双人轻食套餐立减10元",
        ...
    },
    {
        "brand": "咖啡甜点站",
        "description": "咖啡与烘焙甜品",
        "homepage_category": "咖啡甜品",
        "promo_text": "咖啡甜点组合 8 折起",
        ...
    },
    {
        "brand": "炸鸡汉堡屋",
        "description": "炸鸡汉堡与小食拼盘",
        "homepage_category": "炸鸡汉堡",
        "promo_text": "第二份半价，小食拼盘限时优惠",
        ...
    },
    {
        "brand": "老上海粥面铺",
        "description": "粥面馄饨暖胃快餐",
        "homepage_category": "粥面",
        "promo_text": "早点夜宵都能点，满25减6",
        ...
    },
    {
        "brand": "元气日料屋",
        "description": "寿司盖饭与日式小食",
        "homepage_category": "日韩料理",
        "promo_text": "双人定食 88 元起",
        ...
    },
    {
        "brand": "热辣麻辣烫",
        "description": "麻辣烫与冒菜自由选",
        "homepage_category": "麻辣烫",
        "promo_text": "荤素自由配，第二份半价",
        ...
    },
    {
        "brand": "意站披萨馆",
        "description": "披萨意面与焗饭",
        "homepage_category": "披萨意面",
        "promo_text": "工作日午餐焗饭立减8元",
        ...
    },
]
```

Keep the current `build_merchant_seed_data()` shape unchanged so the existing seeding pipeline still works.

- [ ] **Step 4: Run the seed-data test to verify it passes**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation && pytest tests/database/test_merchant_seed_data.py -q
```

Expected: PASS.

- [ ] **Step 5: Re-seed the local catalog and verify a varied merchant set exists**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation && python tools/seed_demo_data.py
```

Expected: output like `Seeded 40 merchants and one demo user` or higher, with the new category mix coming from the expanded profile list.

- [ ] **Step 6: Commit**

```bash
git add database/seeds/merchant_seed_data.py tests/database/test_merchant_seed_data.py
git commit -m "test: expand merchant seed category coverage"
```

### Task 2: Derive homepage category buttons from merchant data

**Files:**
- Create: `ui/src/__tests__/useHomepage.test.js`
- Modify: `ui/src/composables/useHomepage.js`
- Modify: `ui/src/utils/homepage.js`

- [ ] **Step 1: Write the failing composable test**

```javascript
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/useHomepage.test.js
```

Expected: FAIL because `useHomepage.js` still filters through `HOME_CATEGORIES` and does not own a direct category-builder helper.

- [ ] **Step 3: Move category derivation to data-driven helpers and update the composable**

Replace the hardcoded homepage category list with a helper that preserves fetch order, keeps `全部` first, and deduplicates concrete categories.

```javascript
export const buildHomepageCategories = (merchants) => {
  const uniqueCategories = []

  merchants.forEach((merchant) => {
    if (merchant.homepage_category && !uniqueCategories.includes(merchant.homepage_category)) {
      uniqueCategories.push(merchant.homepage_category)
    }
  })

  return ['全部', ...uniqueCategories]
}
```

```javascript
import { buildHomepageCategories } from '../utils/homepage'

const categories = computed(() => buildHomepageCategories(merchants.value))

const filteredMerchants = computed(() => {
  if (selectedCategory.value === '全部') {
    return merchants.value
  }

  return merchants.value.filter((merchant) => merchant.homepage_category === selectedCategory.value)
})
```

Remove the old `HOME_CATEGORIES` export from `ui/src/utils/homepage.js` once nothing imports it.

- [ ] **Step 4: Run the composable test to verify it passes**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/useHomepage.test.js
```

Expected: PASS.

- [ ] **Step 5: Update the homepage shell test to reflect concrete category labels**

Adjust `ui/src/__tests__/app.homepage.test.js` so the mocked homepage categories and merchant payloads match the new concrete category vocabulary.

```javascript
categories: ref(['全部', '湘菜', '轻食', '咖啡甜品']),
filteredMerchants: ref([
  {
    id: 1,
    name: '静安川湘小馆1',
    homepage_category: '湘菜',
    rating: 4.7,
    delivery_fee: 4,
    promo_text: '经典川味',
    description: '下饭川湘家常菜',
  },
]),
```

- [ ] **Step 6: Run the homepage shell test**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/app.homepage.test.js
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/src/composables/useHomepage.js ui/src/utils/homepage.js ui/src/__tests__/useHomepage.test.js ui/src/__tests__/app.homepage.test.js
git commit -m "test: derive homepage filters from merchant data"
```

### Task 3: Replace merchant card gradients with local static images and fallback

**Files:**
- Create: `ui/src/assets/home-covers/xiangcai.svg`
- Create: `ui/src/assets/home-covers/light-meal.svg`
- Create: `ui/src/assets/home-covers/coffee-dessert.svg`
- Create: `ui/src/assets/home-covers/fried-burger.svg`
- Create: `ui/src/assets/home-covers/noodles.svg`
- Create: `ui/src/assets/home-covers/jk-food.svg`
- Create: `ui/src/assets/home-covers/malatang.svg`
- Create: `ui/src/assets/home-covers/pizza-pasta.svg`
- Modify: `ui/src/utils/homepage.js`
- Modify: `ui/src/views/MerchantListView.vue`
- Modify: `ui/src/__tests__/views.behavior.test.js`

- [ ] **Step 1: Write the failing merchant-card image test**

Add a focused component test in `ui/src/__tests__/views.behavior.test.js`.

```javascript
import MerchantListView from '../views/MerchantListView.vue'

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
```

- [ ] **Step 2: Run the view test to verify it fails**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/views.behavior.test.js
```

Expected: FAIL because `MerchantListView.vue` only renders a gradient cover `<div>` and no image element.

- [ ] **Step 3: Add local SVG cover assets and homepage image helpers**

Create the SVG files in `ui/src/assets/home-covers/` and expose them through a single helper map.

```javascript
const CATEGORY_COVER_IMAGES = {
  '湘菜': new URL('../assets/home-covers/xiangcai.svg', import.meta.url).href,
  '轻食': new URL('../assets/home-covers/light-meal.svg', import.meta.url).href,
  '咖啡甜品': new URL('../assets/home-covers/coffee-dessert.svg', import.meta.url).href,
  '炸鸡汉堡': new URL('../assets/home-covers/fried-burger.svg', import.meta.url).href,
  '粥面': new URL('../assets/home-covers/noodles.svg', import.meta.url).href,
  '日韩料理': new URL('../assets/home-covers/jk-food.svg', import.meta.url).href,
  '麻辣烫': new URL('../assets/home-covers/malatang.svg', import.meta.url).href,
  '披萨意面': new URL('../assets/home-covers/pizza-pasta.svg', import.meta.url).href,
}

export const getMerchantCover = (category) => ({
  imageSrc: CATEGORY_COVER_IMAGES[category] || '',
  gradientStyle: getMerchantCoverStyle(category),
})
```

- [ ] **Step 4: Render image-first covers with gradient fallback in the merchant card**

Update `ui/src/views/MerchantListView.vue` so it renders an image when a mapping exists and keeps the current gradient-only path as fallback.

```vue
<div class="merchant-cover" :style="merchantCover(merchant).imageSrc ? undefined : merchantCover(merchant).gradientStyle">
  <img
    v-if="merchantCover(merchant).imageSrc"
    :src="merchantCover(merchant).imageSrc"
    :alt="`${merchant.name} 封面图`"
    data-test="merchant-cover-image"
  />
  <span class="cover-badge">{{ merchant.homepage_category }}</span>
</div>
```

```javascript
import { getMerchantCover } from '../utils/homepage'

const merchantCover = (merchant) => getMerchantCover(merchant.homepage_category)
```

- [ ] **Step 5: Run the focused view test to verify it passes**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/views.behavior.test.js
```

Expected: PASS.

- [ ] **Step 6: Re-run the homepage shell test so the homepage card wall stays green**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/app.homepage.test.js
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/src/assets/home-covers/*.svg ui/src/utils/homepage.js ui/src/views/MerchantListView.vue ui/src/__tests__/views.behavior.test.js ui/src/__tests__/app.homepage.test.js
git commit -m "feat: add local merchant card covers"
```

### Task 4: Auto-login after registration and close the login dialog on auth success

**Files:**
- Modify: `ui/src/views/LoginView.vue`
- Modify: `ui/src/composables/useAuth.js`
- Modify: `ui/src/App.vue`
- Modify: `ui/src/__tests__/views.behavior.test.js`
- Modify: `ui/src/__tests__/app.homepage.test.js`

- [ ] **Step 1: Rewrite the registration view test to describe the new success path**

Replace the current success expectation in `ui/src/__tests__/views.behavior.test.js`.

```javascript
test('LoginView auto-logins after register success and emits auth-success', async () => {
  register.mockResolvedValueOnce({
    id: 2,
    username: 'new_user',
    full_name: '新用户',
    phone: '13900000000',
  })
  login.mockResolvedValueOnce({
    access_token: 'access-token',
    refresh_token: 'refresh-token',
    token_type: 'bearer',
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
  expect(login).toHaveBeenCalledWith({ username: 'new_user', password: 'strongpass' })
  expect(wrapper.emitted('auth-success')).toBeTruthy()
})
```

- [ ] **Step 2: Add the failing dialog-close test at the app level**

In `ui/src/__tests__/app.homepage.test.js`, use a dialog stub that respects `modelValue` and a `LoginView` stub that can emit `auth-success`.

```javascript
const LoginViewStub = defineComponent({
  emits: ['auth-success'],
  template: '<button data-test="login-success" @click="$emit(\'auth-success\')">success</button>',
})

test('App closes the login dialog after LoginView emits auth-success', async () => {
  const wrapper = mount(App, {
    global: {
      stubs: {
        'el-dialog': {
          props: ['modelValue'],
          template: '<div v-if="modelValue"><slot /></div>',
        },
        HomeHeader: {
          emits: ['open-login'],
          template: '<button data-test="open-login" @click="$emit(\'open-login\')">open</button>',
        },
        LoginView: LoginViewStub,
        ...
      },
    },
  })

  await wrapper.find('[data-test="open-login"]').trigger('click')
  expect(wrapper.find('[data-test="login-success"]').exists()).toBe(true)

  await wrapper.find('[data-test="login-success"]').trigger('click')
  await nextTick()

  expect(wrapper.find('[data-test="login-success"]').exists()).toBe(false)
})
```

- [ ] **Step 3: Run the auth-focused frontend tests to verify they fail**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/views.behavior.test.js src/__tests__/app.homepage.test.js
```

Expected: FAIL because `LoginView.vue` still stops at `注册成功，请登录` and `App.vue` does not listen for a success event.

- [ ] **Step 4: Reuse the existing login flow after registration and emit auth success**

Update `ui/src/views/LoginView.vue` to emit success after either login or register-then-login.

```vue
<script setup>
import { reactive, ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits(['auth-success'])
const { authLoading, loginWithPassword, registerWithPassword } = useAuth()

const submitLogin = async () => {
  successMessage.value = ''
  errorMessage.value = ''
  try {
    await loginWithPassword({ username: form.username, password: form.password })
    emit('auth-success')
  } catch (error) {
    errorMessage.value = error?.message || '登录失败，请稍后再试'
  }
}

const submitRegister = async () => {
  successMessage.value = ''
  errorMessage.value = ''
  try {
    await registerWithPassword({
      username: form.username,
      password: form.password,
      full_name: form.full_name,
      phone: form.phone,
    })
    await loginWithPassword({ username: form.username, password: form.password })
    emit('auth-success')
  } catch (error) {
    errorMessage.value = error?.message || '注册失败，请稍后再试'
  }
}
</script>
```

`ui/src/composables/useAuth.js` should keep token persistence exactly where it is now; only touch it if the tests show the current login helper needs to return something additional.

- [ ] **Step 5: Wire the dialog close behavior in the app shell**

Update `ui/src/App.vue`.

```vue
<el-dialog v-model="loginOpen" width="420px" destroy-on-close>
  <LoginView @auth-success="loginOpen = false" />
</el-dialog>
```

- [ ] **Step 6: Run the auth-focused frontend tests to verify they pass**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/views.behavior.test.js src/__tests__/app.homepage.test.js
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/src/views/LoginView.vue ui/src/composables/useAuth.js ui/src/App.vue ui/src/__tests__/views.behavior.test.js ui/src/__tests__/app.homepage.test.js
git commit -m "feat: auto-login after registration"
```

### Task 5: Run the full verification and manual homepage smoke check

**Files:**
- No code changes expected.

- [ ] **Step 1: Run the focused frontend suite together**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run test -- --run src/__tests__/useHomepage.test.js src/__tests__/app.homepage.test.js src/__tests__/views.behavior.test.js
```

Expected: PASS.

- [ ] **Step 2: Run the backend coverage for merchant summaries and seed data**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation && pytest tests/api/test_catalog_routes.py tests/database/test_merchant_seed_data.py -q
```

Expected: PASS.

- [ ] **Step 3: Re-seed and start the local app for manual verification**

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation && python tools/seed_demo_data.py
```

Run:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation && PYTHONIOENCODING=utf-8 python run.py
```

Run in another terminal:
```bash
cd D:/projects/smart_order/.worktrees/phase1-foundation/ui && npm run dev
```

Expected: backend on `http://127.0.0.1:8000`, frontend on the Vite dev URL.

- [ ] **Step 4: Manually verify the homepage golden path**

Check these exact behaviors:

```text
1. Homepage shows multiple concrete category buttons such as 湘菜 / 轻食 / 咖啡甜品 / 炸鸡汉堡.
2. Clicking a category filters the merchant card wall.
3. Merchant cards show local static cover images instead of only gradients.
4. Registration creates a user, immediately logs in, stores tokens, and closes the dialog.
5. The first viewport shows visibly mixed merchant types rather than near-identical cards.
```

- [ ] **Step 5: Commit the final verification-only changes if any test snapshots or fixture updates were required**

```bash
git status --short
```

Expected: either clean working tree or only intentional tracked changes from the previous tasks.
