# Persistent Cart UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a database-backed cart UX where logged-in users can add dishes from merchant detail, view persisted cart contents grouped by merchant, remove rows, and see a styled checkout button placeholder.

**Architecture:** Reuse the existing `/cart` backend surface as the single source of truth and extend the current frontend `useCart()` composable into the shared cart state boundary. Keep `MerchantDetailView.vue` responsible for add-to-cart intent, `CheckoutView.vue` responsible for rendering and deletion, and `App.vue` responsible for opening the login dialog when unauthenticated add-to-cart is attempted.

**Tech Stack:** Vue 3, Vitest, Vue Test Utils, Element Plus, Axios, FastAPI, SQLAlchemy, pytest

---

## File Map

- Modify: `repository/cart_repository.py`
  - Fix repeated add-to-cart so quantity increments instead of being overwritten.
- Modify: `tests/api/test_cart_routes.py`
  - Lock the backend repeated-add behavior with a real persistence regression test.
- Modify: `ui/src/api/cart.js`
  - Add add-item and remove-item cart API helpers.
- Modify: `ui/src/composables/useCart.js`
  - Add shared cart mutation methods and derived state.
- Modify: `ui/src/views/MerchantDetailView.vue`
  - Add add-to-cart button, authenticated mutation path, and unauthenticated login-request event.
- Modify: `ui/src/views/CheckoutView.vue`
  - Render grouped dish rows, delete buttons, empty-state checkout disabling, and placeholder checkout action.
- Modify: `ui/src/App.vue`
  - Wire merchant-detail login request upward to the existing login dialog.
- Modify: `ui/src/__tests__/views.behavior.test.js`
  - Add focused frontend behavior coverage for merchant detail and checkout cart flows.
- Modify: `ui/src/__tests__/app.homepage.test.js`
  - Add App-level regression coverage that merchant detail can request the login dialog.

---

### Task 1: Fix repeated add-to-cart persistence in the backend

**Files:**
- Modify: `repository/cart_repository.py:41-65`
- Modify: `tests/api/test_cart_routes.py`
- Test: `tests/api/test_cart_routes.py`

- [ ] **Step 1: Write the failing backend regression test**

Add this test to `tests/api/test_cart_routes.py` after the existing cart route tests:

```python
def test_adding_same_dish_twice_increments_quantity(monkeypatch) -> None:
    from api.models.cart import CartItem
    from api.models.catalog import Dish, DishCategory, Merchant
    from api.models.user import User
    from sqlalchemy.orm import Session

    User.__table__.create(bind=engine, checkfirst=True)
    Merchant.__table__.create(bind=engine, checkfirst=True)
    DishCategory.__table__.create(bind=engine, checkfirst=True)
    Dish.__table__.create(bind=engine, checkfirst=True)
    CartItem.__table__.create(bind=engine, checkfirst=True)

    with Session(engine) as session:
        user = User(username="cart_user", password_hash="secret", full_name="购物车用户", phone="13900000000")
        session.add(user)
        session.flush()

        merchant = Merchant(
            name="川湘小馆",
            description="下饭家常菜",
            city="上海",
            district="静安",
            address="南京西路 100 号",
            longitude=121.45,
            latitude=31.23,
        )
        session.add(merchant)
        session.flush()

        category = DishCategory(merchant_id=merchant.id, name="招牌菜", sort_order=1)
        session.add(category)
        session.flush()

        dish = Dish(
            merchant_id=merchant.id,
            category_id=category.id,
            name="鱼香肉丝",
            description="酸甜开胃",
            price=28,
        )
        session.add(dish)
        session.commit()
        user_id = user.id
        dish_id = dish.id

    app.dependency_overrides[cart_routes.get_current_user] = lambda: type("User", (), {"id": user_id})()
    try:
        first_response = client.post("/cart/items", json={"dish_id": dish_id, "quantity": 1})
        second_response = client.post("/cart/items", json={"dish_id": dish_id, "quantity": 1})
        cart_response = client.get("/cart")

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert second_response.json() == {"success": True, "dish_id": dish_id, "quantity": 2}
        assert cart_response.status_code == 200
        assert cart_response.json()["items"][0]["items"] == [
            {"dish_id": dish_id, "dish_name": "鱼香肉丝", "quantity": 2, "unit_price": 28.0}
        ]
        assert cart_response.json()["goods_amount"] == 56.0
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run the backend test to verify it fails**

Run:

```bash
pytest tests/api/test_cart_routes.py::test_adding_same_dish_twice_increments_quantity -v
```

Expected: FAIL because the second add still returns quantity `1` and the cart total remains `28.0`.

- [ ] **Step 3: Write the minimal backend fix**

Update `repository/cart_repository.py` so an existing row increments quantity instead of replacing it:

```python
    def upsert_item(self, user_id: int, dish_id: int, quantity: int) -> CartItem:
        cart = self.get_or_create_cart(user_id)
        statement = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.dish_id == dish_id)
        item = self.session.scalar(statement)
        dish = self.get_dish(dish_id)
        if dish is None:
            raise ValueError("dish not found")

        if item is None:
            item = CartItem(
                cart_id=cart.id,
                user_id=user_id,
                merchant_id=dish.merchant_id,
                dish_id=dish.id,
                quantity=quantity,
                unit_price_snapshot=dish.price,
            )
            self.session.add(item)
        else:
            item.quantity += quantity
            item.unit_price_snapshot = dish.price

        self.session.commit()
        self.session.refresh(item)
        return item
```

- [ ] **Step 4: Run the backend test to verify it passes**

Run:

```bash
pytest tests/api/test_cart_routes.py::test_adding_same_dish_twice_increments_quantity -v
```

Expected: PASS.

- [ ] **Step 5: Re-run the existing cart route file**

Run:

```bash
pytest tests/api/test_cart_routes.py -v
```

Expected: PASS with the earlier empty-cart and delete-missing-cart tests still green.

- [ ] **Step 6: Commit the backend cart fix**

```bash
git add tests/api/test_cart_routes.py repository/cart_repository.py
git commit -m "fix: increment persisted cart quantities"
```

---

### Task 2: Extend the shared frontend cart API and composable

**Files:**
- Modify: `ui/src/api/cart.js`
- Modify: `ui/src/composables/useCart.js`
- Test: `ui/src/__tests__/views.behavior.test.js`

- [ ] **Step 1: Write the failing frontend composable behavior test**

In `ui/src/__tests__/views.behavior.test.js`, hoist and mock the cart API alongside the existing mocks:

```javascript
const { getCart, addCartItem, removeCartItem } = vi.hoisted(() => ({
  getCart: vi.fn(),
  addCartItem: vi.fn(),
  removeCartItem: vi.fn(),
}))

vi.mock('../api/cart', () => ({
  getCart,
  addCartItem,
  removeCartItem,
}))
```

Then add a CheckoutView-focused test that proves delete should refresh cart state with the backend result:

```javascript
import CheckoutView from '../views/CheckoutView.vue'

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
```

- [ ] **Step 2: Run the focused frontend test to verify it fails**

Run:

```bash
npm --prefix "D:/projects/smart_order/.worktrees/phase1-foundation/ui" test -- src/__tests__/views.behavior.test.js --run
```

Expected: FAIL because `CheckoutView` does not yet render dish rows, delete controls, or use a remove cart mutation path.

- [ ] **Step 3: Add the cart API helpers**

Update `ui/src/api/cart.js` to expose all cart operations used by the composable:

```javascript
import api from './index'

export const getCart = () => api.get('/cart')
export const addCartItem = (payload) => api.post('/cart/items', payload)
export const removeCartItem = (dishId) => api.delete(`/cart/items/${dishId}`)
```

- [ ] **Step 4: Expand `useCart()` into the shared mutation boundary**

Update `ui/src/composables/useCart.js`:

```javascript
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
```

- [ ] **Step 5: Re-run the focused frontend test to verify the shared cart layer supports the view**

Run:

```bash
npm --prefix "D:/projects/smart_order/.worktrees/phase1-foundation/ui" test -- src/__tests__/views.behavior.test.js --run
```

Expected: still FAIL, but now only for missing `CheckoutView` UI elements rather than missing API/composable methods.

- [ ] **Step 6: Commit the shared cart layer work**

```bash
git add ui/src/api/cart.js ui/src/composables/useCart.js ui/src/__tests__/views.behavior.test.js
git commit -m "feat: add shared cart mutation helpers"
```

---

### Task 3: Add merchant-detail add-to-cart and login-request wiring

**Files:**
- Modify: `ui/src/views/MerchantDetailView.vue`
- Modify: `ui/src/App.vue`
- Modify: `ui/src/__tests__/views.behavior.test.js`
- Modify: `ui/src/__tests__/app.homepage.test.js`
- Test: `ui/src/__tests__/views.behavior.test.js`
- Test: `ui/src/__tests__/app.homepage.test.js`

- [ ] **Step 1: Write the failing merchant-detail interaction tests**

Add these tests to `ui/src/__tests__/views.behavior.test.js`:

```javascript
import { useAuth } from '../composables/useAuth'

test('MerchantDetailView adds a dish to the persisted cart when logged in', async () => {
  useAuth().currentUser.value = { id: 2, username: 'new_user', full_name: '新用户', phone: '13900000000' }
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

  expect(addCartItem).toHaveBeenCalledWith(7)
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
```

Add this App-level regression to `ui/src/__tests__/app.homepage.test.js`:

```javascript
test('App opens the login dialog when MerchantDetailView requests login for add-to-cart', async () => {
  const MerchantDetailViewStub = defineComponent({
    emits: ['request-login'],
    template: '<button data-test="request-login" @click="$emit(\'request-login\')">request</button>',
  })

  const wrapper = mount(App, {
    global: {
      stubs: {
        'el-dialog': { template: '<div><slot /></div>' },
        'el-drawer': { template: '<div><slot /></div>' },
        'el-button': { template: '<button><slot /></button>' },
        'el-input': { template: '<input />' },
        'el-empty': { template: '<div class="empty-state"></div>' },
        HomeHeader: false,
        CategoryFilterBar: false,
        MerchantListView: false,
        FloatingAssistant: false,
        LoginView: LoginViewStub,
        CheckoutView: simpleStub('CheckoutView'),
        AddressView: simpleStub('AddressView'),
        MerchantDetailView: MerchantDetailViewStub,
      },
    },
  })

  await wrapper.find('[data-test="request-login"]').trigger('click')
  await nextTick()

  expect(wrapper.find('[data-test="login-success"]').exists()).toBe(true)
})
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run:

```bash
npm --prefix "D:/projects/smart_order/.worktrees/phase1-foundation/ui" test -- src/__tests__/views.behavior.test.js src/__tests__/app.homepage.test.js --run
```

Expected: FAIL because merchant detail has no add-to-cart button and App does not listen for `request-login` from the drawer view.

- [ ] **Step 3: Implement merchant-detail add-to-cart behavior**

Update `ui/src/views/MerchantDetailView.vue` like this:

```vue
<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { listMerchantDishes } from '../api/catalog'
import { useAuth } from '../composables/useAuth'
import { useCart } from '../composables/useCart'
import { formatCurrency } from '../utils/currency'

const emit = defineEmits(['request-login'])
const props = defineProps({
  merchantId: { type: Number, default: null },
})

const { currentUser } = useAuth()
const { addCartItem } = useCart()
const dishes = ref([])
const loading = ref(false)
const errorMessage = ref('')
const addingDishId = ref(null)

const addDishToCart = async (dishId) => {
  if (!currentUser.value) {
    emit('request-login')
    return
  }

  addingDishId.value = dishId
  try {
    await addCartItem(dishId)
    ElMessage.success('已加入购物车')
  } catch (error) {
    errorMessage.value = error?.message || '加入购物车失败，请稍后再试'
  } finally {
    addingDishId.value = null
  }
}
```

And update the dish row template block:

```vue
      <div v-for="dish in dishes" :key="dish.id" class="dish-card">
        <h4>{{ dish.name }}</h4>
        <p>{{ dish.description }}</p>
        <div class="dish-footer">
          <p>{{ formatCurrency(dish.price) }}</p>
          <el-button :data-test="`add-cart-${dish.id}`" type="primary" :loading="addingDishId === dish.id" @click="addDishToCart(dish.id)">
            加入购物车
          </el-button>
        </div>
      </div>
```

- [ ] **Step 4: Implement App-level login dialog orchestration**

Update the merchant drawer usage in `ui/src/App.vue`:

```vue
    <el-drawer v-model="merchantDrawerOpen" size="480px" destroy-on-close>
      <MerchantDetailView :merchant-id="selectedMerchantId" @request-login="loginOpen = true" />
    </el-drawer>
```

- [ ] **Step 5: Run the frontend tests to verify they pass**

Run:

```bash
npm --prefix "D:/projects/smart_order/.worktrees/phase1-foundation/ui" test -- src/__tests__/views.behavior.test.js src/__tests__/app.homepage.test.js --run
```

Expected: PASS for the new add-to-cart/login-request behaviors plus the earlier homepage auth regressions.

- [ ] **Step 6: Commit the merchant-detail cart interaction work**

```bash
git add ui/src/views/MerchantDetailView.vue ui/src/App.vue ui/src/__tests__/views.behavior.test.js ui/src/__tests__/app.homepage.test.js
git commit -m "feat: add merchant detail cart actions"
```

---

### Task 4: Render full cart rows, deletion, and checkout placeholder UI

**Files:**
- Modify: `ui/src/views/CheckoutView.vue`
- Modify: `ui/src/__tests__/views.behavior.test.js`
- Test: `ui/src/__tests__/views.behavior.test.js`

- [ ] **Step 1: Write the failing checkout rendering test**

Add this focused test to `ui/src/__tests__/views.behavior.test.js`:

```javascript
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
```

- [ ] **Step 2: Run the focused checkout test to verify it fails**

Run:

```bash
npm --prefix "D:/projects/smart_order/.worktrees/phase1-foundation/ui" test -- src/__tests__/views.behavior.test.js --run
```

Expected: FAIL because `CheckoutView` currently renders only merchant name and subtotal.

- [ ] **Step 3: Implement the full checkout cart UI**

Update `ui/src/views/CheckoutView.vue`:

```vue
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
        <div v-for="item in group.items" :key="item.dish_id" class="cart-row">
          <div>
            <strong>{{ item.dish_name }}</strong>
            <p>{{ formatCurrency(item.unit_price) }} × {{ item.quantity }}</p>
          </div>
          <el-button :data-test="`remove-cart-item-${item.dish_id}`" text @click="deleteItem(item.dish_id)">
            删除
          </el-button>
        </div>
        <p>小计 {{ formatCurrency(group.subtotal) }}</p>
      </div>
    </template>
    <footer class="cart-footer">
      <strong>商品总价 {{ formatCurrency(goodsAmount) }}</strong>
      <el-button type="primary" :disabled="!merchantGroups.length" @click="showCheckoutPlaceholder">
        去结算
      </el-button>
    </footer>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useCart } from '../composables/useCart'
import { formatCurrency } from '../utils/currency'

const { merchantGroups, goodsAmount, refreshCart, removeCartItem } = useCart()
const loading = ref(true)
const errorMessage = ref('')

const deleteItem = async (dishId) => {
  try {
    await removeCartItem(dishId)
  } catch (error) {
    errorMessage.value = error?.message || '删除失败，请稍后再试'
  }
}

const showCheckoutPlaceholder = () => {
  ElMessage.info('结算功能暂未开放')
}

onMounted(async () => {
  try {
    await refreshCart()
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 4: Re-run the checkout-focused test to verify it passes**

Run:

```bash
npm --prefix "D:/projects/smart_order/.worktrees/phase1-foundation/ui" test -- src/__tests__/views.behavior.test.js --run
```

Expected: PASS with the new checkout row rendering and deletion flow.

- [ ] **Step 5: Run both focused frontend suites together**

Run:

```bash
npm --prefix "D:/projects/smart_order/.worktrees/phase1-foundation/ui" test -- src/__tests__/views.behavior.test.js src/__tests__/app.homepage.test.js --run
```

Expected: PASS.

- [ ] **Step 6: Commit the checkout cart UI work**

```bash
git add ui/src/views/CheckoutView.vue ui/src/__tests__/views.behavior.test.js
git commit -m "feat: render persistent cart details"
```

---

## Self-Review Checklist

- Spec coverage:
  - backend persistence is covered in Task 1
  - shared frontend cart state is covered in Task 2
  - merchant-detail add-to-cart and unauthenticated login request are covered in Task 3
  - checkout rendering, deletion, total, empty-state disable, and placeholder checkout action are covered in Task 4
- Placeholder scan:
  - no `TODO`, `TBD`, or "similar to Task N" shortcuts remain
  - every test and command is concrete
- Type consistency:
  - cart API helper names stay `getCart`, `addCartItem`, `removeCartItem`
  - composable names stay `refreshCart`, `addCartItem`, `removeCartItem`, `goodsAmount`, `merchantGroups`
  - unauthenticated merchant-detail event name stays `request-login`
