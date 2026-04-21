# Homepage Follow-up Improvements Design

**Date:** 2026-04-21
**Scope:** Homepage category buttons, registration success flow, merchant card imagery, and broader merchant seed data.

## Goal

Polish the current homepage so it feels like a real delivery marketplace: users can filter by concrete merchant categories, merchant cards show real images instead of plain color blocks, registration immediately signs the user in and closes the dialog, and the seeded catalog looks more diverse on first load.

## Confirmed Product Decisions

1. Homepage category buttons should show **real merchant categories** such as 湘菜、轻食、咖啡甜品、炸鸡汉堡等, not only `全部` or abstract运营标签.
2. Registration success should **auto-login** the new user, persist the tokens, and **close the login dialog**.
3. Homepage merchant cards should show **real images**.
4. Seed data should include **more varied merchant types** so the homepage does not render multiple near-identical cards in the first viewport.

## Existing State

- `ui/src/components/home/CategoryFilterBar.vue` already renders a dynamic button list correctly.
- `ui/src/views/MerchantListView.vue` currently renders a colored cover area based on category style instead of an actual image.
- `ui/src/views/LoginView.vue` already supports switching to registration mode and submitting registration, but it stops at a success message.
- `ui/src/composables/useAuth.js` already exposes `registerWithPassword` and `loginWithPassword`.
- `database/seeds/merchant_seed_data.py` currently generates merchants from a small set of cuisine profiles, so the homepage can still feel repetitive.

## Recommended Approach

Use **real business categories as the homepage filter source**, **front-end local static images keyed by merchant category**, and **expanded seed data with more cuisine profiles**.

This is the best fit because it keeps the changes small and deterministic:
- category filtering stays simple and transparent,
- homepage images do not depend on external services,
- the backend contract can stay minimal,
- registration auto-login can reuse the existing login/token flow instead of inventing a second authentication path.

## Alternatives Considered

### Option 1 — Recommended: Real categories + local static images + expanded seed data
- Buttons are generated from concrete merchant categories.
- Card images come from front-end static assets via a category/image mapping.
- Registration calls register, then login, then closes the dialog.
- Seed data is expanded to more cuisines and districts.

**Why recommended:** smallest reliable change set, no new infra, matches the user request directly.

### Option 2 — Add a second layer of homepage filters
- Keep current homepage promo tags and add a second row for real categories.

**Tradeoff:** richer IA, but heavier UI and state complexity than needed right now.

### Option 3 — Only rename current homepage categories
- Change visible labels without changing data semantics.

**Tradeoff:** fastest, but misleading and likely to require later rework.

## Design

### 1. Homepage category behavior

The homepage category row will be generated from the current merchant result set:
- always prepend `全部`,
- then append the unique concrete merchant categories in stable display order,
- selecting a category filters the merchant card list by that category.

The data source should be a concrete merchant-facing category field, not the existing broad homepage promo label when those two differ in meaning.

If the current backend summary payload does not already expose a concrete category distinct from `homepage_category`, the backend will be updated with one lightweight field so the front end can render and filter correctly.

### 2. Merchant card images

Merchant cards will display a real image in the top cover area.

Implementation strategy:
- place curated local images in the front-end static asset area,
- map each merchant category to an image key,
- render the mapped image as the merchant card cover,
- overlay the category text as a small badge/label,
- fall back to the current gradient/color cover only when a mapping is missing.

This keeps the experience visually richer without making the homepage depend on remote assets or a database image pipeline.

### 3. Registration success flow

Registration will become a two-step success flow inside the current login dialog:
1. submit registration to `/auth/register`,
2. if registration succeeds, immediately call the existing login flow with the same username/password,
3. persist tokens exactly as the login flow already does,
4. update the local auth state,
5. close the login dialog from the parent container.

The login dialog should no longer stop at a passive “注册成功，请登录” message in the success path.

Error behavior should remain simple:
- registration failure shows the registration error,
- auto-login failure after a successful registration shows a clear login failure message and keeps the dialog open.

### 4. Seed data expansion

The seed catalog will be expanded beyond the current small cuisine set.

Target direction:
- keep the existing profiles,
- add more distinct merchant types such as 粥面、日韩料理、麻辣烫、烤肉饭、沙县/小吃、披萨意面、健康早餐、果切饮品等,
- ensure the first-page ordering naturally surfaces a more mixed set of merchants,
- keep generated merchant names/district coverage deterministic.

The goal is not to create a huge catalog, but to make the homepage immediately look varied and believable.

## File-Level Impact

### Frontend
- `ui/src/composables/useHomepage.js`
  - derive real category buttons from merchant data,
  - filter by the concrete merchant category field.
- `ui/src/components/home/CategoryFilterBar.vue`
  - no responsibility change; may only need light style adjustment if the button count grows.
- `ui/src/views/MerchantListView.vue`
  - replace plain color cover with image-first rendering and fallback behavior.
- `ui/src/views/LoginView.vue`
  - change registration success behavior to auto-login.
- `ui/src/App.vue`
  - close the login dialog when login/register success is emitted.
- `ui/src/__tests__/app.homepage.test.js`
  - verify concrete category buttons render.
- `ui/src/__tests__/views.behavior.test.js`
  - verify registration auto-login and close behavior,
  - verify merchant card image rendering if tested at component level.

### Backend / data
- `database/seeds/merchant_seed_data.py`
  - add more cuisine profiles and image/category metadata if needed.
- `tools/seed_catalog_data.py`
  - continue consuming seed definitions; only update if new fields are required.
- `service/catalog_service.py`, `api/schemas.py`, and related model/repository code
  - only touch these if a new merchant summary field is needed for concrete category or image key.

## Testing and Verification

### Automated
- Add/adjust frontend tests for:
  - concrete category button rendering,
  - category filtering using concrete merchant categories,
  - registration success auto-login path,
  - dialog close behavior after successful registration.
- Re-run the existing homepage shell and guarded view tests.

### Manual
- Refresh the running homepage and confirm:
  - multiple real category buttons are visible,
  - clicking a category filters cards,
  - cards display actual images,
  - registration creates a user, signs in automatically, and closes the dialog,
  - the first screen shows more varied merchant types.

## Non-Goals

- No remote image fetching pipeline.
- No user-uploaded merchant images.
- No multi-layer homepage information architecture in this iteration.
- No auth system redesign beyond reusing the existing login flow after registration.

## Risks and Mitigations

- **Too many category buttons** → keep order stable and allow wrapping; do not invent a second filter layer yet.
- **Missing image mappings** → keep the current gradient fallback.
- **Registration succeeds but auto-login fails** → surface the failure and keep the dialog open.
- **Seed data grows but homepage still looks repetitive** → adjust default ordering to mix categories earlier.
