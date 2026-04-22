# Persistent Cart UX Design

**Date:** 2026-04-22
**Scope:** smart_order existing-codebase cart UX follow-up

## Goal

Add a usable database-backed cart flow to the existing smart_order frontend so that users can add dishes from merchant detail, view all persisted cart items grouped by merchant, remove items, and see a styled checkout button without implementing real payment.

## Current Context

The codebase already has the core backend cart persistence and API surface:

- `GET /cart` returns grouped cart data with merchant name, grouped items, subtotal, and total goods amount.
- `POST /cart/items` upserts cart items by `dish_id` and `quantity`.
- `DELETE /cart/items/{dish_id}` removes a cart item row.
- Cart data is tied to the authenticated user, so items persist across logout/login.

The frontend currently has partial read-only cart support:

- `ui/src/composables/useCart.js` only refreshes cart state.
- `ui/src/views/CheckoutView.vue` only shows merchant-level subtotals and total goods amount.
- `ui/src/views/MerchantDetailView.vue` lists dishes but has no add-to-cart action.
- `ui/src/App.vue` already controls the login dialog and cart dialog.

## Decisions

### 1. Single source of truth

The backend `/cart` API remains the only source of truth for cart contents.

The frontend will not maintain a separate temporary cart model. After every successful add/remove mutation, the frontend refreshes cart state from the backend.

### 2. Authentication behavior

If an unauthenticated user clicks “加入购物车”, the frontend opens the existing login dialog immediately.

The feature does not support guest carts or later cart merge in this scope.

### 3. Repeated add behavior

If the user clicks “加入购物车” multiple times for the same dish, quantity increases by 1 each time through the existing backend upsert behavior.

The frontend does not create duplicate visual rows for the same dish.

### 4. Remove behavior

Cart removal is row-level only in this scope.

The cart UI will provide a delete action that removes the whole dish row. Quantity decrement controls are explicitly out of scope.

### 5. Checkout behavior

The checkout button is visual-only for now.

It should be visible, styled, and disabled when the cart is empty. When the cart contains items, clicking it should show a frontend-only “功能暂未开放” style message instead of entering a real payment or order flow.

## UI / State Design

### `ui/src/composables/useCart.js`

Expand the shared cart composable into the cart state boundary for the frontend.

Responsibilities:

- keep the shared reactive `cart`
- expose `merchantGroups`
- expose derived total information from `cart.goods_amount`
- add `addCartItem(dishId)`
- add `removeCartItem(dishId)`
- keep `refreshCart()`
- expose mutation/loading state needed by views

Behavior:

- `addCartItem(dishId)` calls `POST /cart/items` with `{ dish_id, quantity: 1 }`, then `refreshCart()`
- `removeCartItem(dishId)` calls `DELETE /cart/items/{dish_id}`, then `refreshCart()`
- errors bubble to the caller so the view can show user-facing feedback

### `ui/src/views/MerchantDetailView.vue`

Each dish card gets an “加入购物车” button.

Behavior:

- when the user is logged in, clicking the button adds the dish to the persisted cart and shows a lightweight success reaction
- when the user is not logged in, the view emits a request-login event upward instead of mutating cart data

The merchant detail view remains focused on dish presentation plus add-to-cart action. It should not own login modal state.

### `ui/src/views/CheckoutView.vue`

Upgrade the cart dialog from summary-only to full cart detail rendering.

For each merchant group, render:

- merchant name
- each dish row under that merchant
- dish name
- unit price
- quantity
- row delete action
- merchant subtotal

At the bottom of the dialog, render:

- goods total
- checkout button

Empty-cart behavior:

- keep the existing empty state
- disable checkout button when no items exist

Checkout click behavior:

- show a non-persistent frontend message that checkout is not available yet

### `ui/src/App.vue`

Keep App as the dialog orchestration layer.

Add support for the merchant detail view to request login when unauthenticated add-to-cart is attempted.

Expected flow:

- user opens merchant drawer
- user clicks add-to-cart on a dish
- if not logged in, merchant detail emits upward
- App opens the existing login dialog
- after login succeeds, the user can retry add-to-cart

This scope does not auto-replay the last blocked add-to-cart intent after login.

## Data Expectations

The frontend design assumes the existing grouped cart payload shape remains stable:

```json
{
  "items": [
    {
      "merchant_id": 1,
      "merchant_name": "川湘小馆",
      "items": [
        {
          "dish_id": 11,
          "dish_name": "鱼香肉丝",
          "quantity": 2,
          "unit_price": 28.0
        }
      ],
      "subtotal": 56.0
    }
  ],
  "goods_amount": 56.0
}
```

No guest-cart schema or cart-merge schema is introduced.

## Test Plan

### Frontend tests

Add or update focused behavior tests for:

1. `MerchantDetailView`
   - logged-in add-to-cart calls the cart mutation path
   - unauthenticated add-to-cart emits a login request event instead of mutating cart

2. `CheckoutView`
   - renders merchant source, dish name, price, quantity, subtotal, and total
   - delete action removes a row through the cart API path
   - empty cart renders empty state and disables checkout button

3. `App.vue`
   - merchant detail login-request event opens the login dialog

### Backend regression tests

Use existing cart route coverage as the base. Only add coverage if needed to lock response shape relied on by the frontend, especially:

- merchant group includes `merchant_name`
- dish rows include `dish_name`, `quantity`, and `unit_price`
- total still uses `goods_amount`

## Out of Scope

The following are explicitly not part of this change:

- real checkout or payment
- quantity increment/decrement controls inside the cart
- guest cart storage
- auto-merging guest cart to account cart
- cart badge in the header
- automatic replay of blocked add-to-cart after login
- cross-device live sync messaging

## Implementation Notes

Prefer the smallest change set that closes the loop between existing backend cart persistence and the current frontend UI.

Follow the existing composable + view pattern already used for auth and homepage state instead of introducing a heavier new store abstraction for this scope.
