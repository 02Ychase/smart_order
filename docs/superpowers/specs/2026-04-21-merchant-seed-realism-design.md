# Merchant Seed Realism Enhancement Design

**Date:** 2026-04-21
**Scope:** Make homepage merchant seed data and internal menu data feel more realistic, less templated, and more useful for later RAG retrieval.

## Goal

Upgrade the seeded merchant catalog from a profile-cloning dataset into a believable multi-merchant marketplace dataset: merchant names should feel like real stores, same-category merchants should have different positioning, and their menus should no longer be near-identical copies.

## Confirmed Product Decisions

1. Merchant names should **not contain numeric suffixes**.
2. Merchants in the same category should **not look mass-generated**.
3. Same-category merchants should have **meaningfully different internal menus**, not the exact same dishes.
4. Image assets may **continue to be reused by category**.
5. The purpose of this iteration is to improve the quality of later **RAG retrieval differentiation**, not to redesign the homepage UI.

## Existing State

- `database/seeds/merchant_seed_data.py` currently builds merchant data from `DISTRICT_POINTS × CUISINE_PROFILES`.
- Merchant names are generated with a numbered pattern like `"name": f"{district['district']}{profile['brand']}{profile_index}"`, which produces visibly synthetic names.
- Same-category merchants reuse the same `categories -> dishes` structure across districts, so menu semantics are almost identical.
- `tools/seed_catalog_data.py` already consumes the current seed payload shape and inserts merchants, dish categories, and dishes successfully.
- Existing tests mostly verify category coverage and payload counts, but they do not yet guard against templated naming or duplicated same-category menus.

## Recommended Approach

Adopt an **instance-first seed model**.

Instead of generating merchants by cloning a small set of cuisine profiles across all districts, define a curated list of merchant instances directly in `database/seeds/merchant_seed_data.py`. Each merchant instance will keep the current payload schema, but will own its own name, positioning copy, promo text, and menu composition.

This is the best fit because it directly solves the user-visible problems:
- no numeric suffixes,
- less template repetition,
- stronger semantic variation for RAG,
- no backend contract changes,
- no image pipeline changes.

## Alternatives Considered

### Option A — Recommended: Curated merchant instances
- Replace profile cloning with an explicit list of merchant payloads.
- Keep the current database seed payload shape unchanged.
- Hand-curate variation at the merchant level.

**Why recommended:** strongest realism improvement with the least ambiguity, and the generated data becomes easy to inspect and refine.

### Option B — Keep generation, add variation pools
- Preserve the generator, but add multiple naming pools, promo pools, and menu pools per category.

**Tradeoff:** less manual data entry, but still prone to “advanced template” repetition and harder to reason about when debugging retrieval quality.

### Option C — Minimal patch on current dataset
- Remove numeric suffixes and swap a subset of dish names.

**Tradeoff:** fastest, but too shallow to materially improve realism or retrieval differentiation.

## Design

### 1. Seed data model

The seed payload structure stays the same so the seeding pipeline does not need a schema rewrite. Each merchant will still provide:
- `name`
- `description`
- `city`
- `district`
- `address`
- `longitude`
- `latitude`
- `homepage_category`
- `promo_text`
- delivery and rating fields
- `categories`

The change is in authorship style: the file will define merchants as **merchant instances**, not as category templates expanded by nested loops.

### 2. Merchant identity design

Each merchant should read like a distinct store rather than a numbered clone.

Rules:
- no digits in merchant names,
- no repeated `{district}{brand}{index}` naming pattern,
- same-category merchants should vary in tone and business positioning,
- district names may appear in some stores, but not uniformly.

Examples of acceptable differentiation within one category:
- 湘菜 can split into home-style stir-fry, spicy rice bowls, claypot-heavy, and office-lunch quick meals.
- 轻食 can split into fitness bowls, brunch/light café, vegetarian fresh bowls, and wrap/salad combinations.
- 咖啡甜品 can split into espresso + baked goods, dessert-first afternoon tea, coconut/milk coffee trend shop, and community café.

### 3. Menu differentiation rules

Same-category merchants may share a few familiar dishes, but they must not share the same full menu.

Required differentiation dimensions:
- **category naming:** merchants can use different menu section names
- **signature dishes:** each merchant should have its own featured items
- **dish mix:** overlap is allowed, but the full menu signature must differ
- **descriptions and tags:** wording should reflect each merchant’s style, not reuse the same copy everywhere
- **price bands:** small price differences are encouraged so merchants do not all look machine-generated

Example:
- Two 湘菜 stores may both sell `辣椒炒肉`, but one can center on `现炒小碗菜` and another on `砂锅下饭菜`; the rest of their menus, descriptions, and pricing should differ.

### 4. Category-level coverage

Keep the broader homepage category coverage achieved in the prior iteration. The catalog should still cover at least the current core categories already used by the homepage:
- 湘菜
- 轻食
- 咖啡甜品
- 炸鸡汉堡
- 粥面
- 日韩料理
- 麻辣烫
- 披萨意面

The goal is not to add more homepage categories in this iteration. The goal is to make merchants inside those categories feel more believable and more distinct.

### 5. Data volume target

Keep a homepage-friendly catalog size of roughly the current scale so the demo remains rich on first load.

Target:
- about 40 merchants total,
- multiple districts retained,
- each merchant with at least 2 menu sections,
- each merchant with enough dishes to keep detail pages and retrieval useful.

This preserves breadth while increasing depth and semantic uniqueness.

### 6. File-level impact

Primary changes:
- `database/seeds/merchant_seed_data.py`
  - replace nested profile expansion with curated merchant instances,
  - rewrite merchant names, descriptions, promo text, and menus for realism,
  - keep payload keys compatible with existing seeding code.
- `tests/database/test_merchant_seed_data.py`
  - extend beyond category/count checks to cover realism constraints.
- `tests/test_seed_payload.py`
  - update stale merchant-count expectations and add stronger payload assertions.

No planned behavior changes to:
- `tools/seed_catalog_data.py`
- API schema/service code
- frontend image mapping

### 7. Testing and verification

Add or update automated checks for:
- merchant count remains at a demo-appropriate level,
- homepage category coverage is preserved,
- merchant names do not contain trailing numeric identity markers,
- same-category merchants do not all share identical menu signatures,
- every merchant still has valid menu sections and dish counts.

Manual verification after reseeding:
- homepage merchant list looks less repetitive,
- same-category cards have different names and selling points,
- merchant detail menus show obvious differences between same-category stores,
- existing category buttons and cover-image behavior still work unchanged.

## Non-Goals

- No new homepage layout changes.
- No remote image sourcing.
- No merchant image customization per store.
- No changes to backend API schema unless an unexpected incompatibility is found.
- No procedural content generation system in this iteration.

## Risks and Mitigations

- **Risk: the seed file becomes long and harder to scan.**  
  Mitigation: keep merchant instances grouped by homepage category with consistent field ordering.

- **Risk: manual curation introduces malformed payloads.**  
  Mitigation: strengthen tests around required fields, section counts, and dish counts.

- **Risk: same-category merchants still feel too similar despite renaming.**  
  Mitigation: test menu signatures and vary positioning, section names, and recommended dishes together rather than changing names only.

- **Risk: reseeding breaks the current demo flow.**  
  Mitigation: keep the payload contract unchanged so `tools/seed_catalog_data.py` continues to work as-is.
