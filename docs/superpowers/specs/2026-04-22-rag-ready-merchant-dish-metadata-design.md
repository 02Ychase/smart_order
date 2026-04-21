# RAG-Ready Merchant & Dish Metadata Design

**Date:** 2026-04-22
**Scope:** Expand merchant and dish seed data, database schema, and catalog API responses so the demo dataset carries retrieval-friendly structured restaurant metadata rather than only lightweight homepage fields.

## Goal

Upgrade the current merchant catalog from homepage-oriented demo data into a richer structured dataset that supports later RAG retrieval, comparison, and filtering. Merchant records should include more precise location and contact context; dish records should include richer structured culinary metadata such as ingredients, allergens, flavor profile, and cooking method.

## Confirmed Product Decisions

1. This iteration is **backend-first**. The main output is richer database records and API payloads; frontend display is not the primary scope.
2. Structured list fields such as `ingredients` and `allergens` should be modeled as **arrays**, not comma-joined strings.
3. The new metadata should be exposed through the existing catalog API so downstream consumers can use it immediately.
4. Merchant and dish demo data may be treated as **rebuildable seed data**. Migration plus reseed is acceptable; old merchant/dish demo rows do not need compatibility preservation.
5. The purpose of this iteration is to improve **RAG retrieval quality and semantic differentiation**, not to redesign the homepage UI.

## Existing State

- `api/models/catalog.py` currently stores only lightweight merchant fields (`name`, `description`, `district`, `address`, `longitude`, `latitude`, delivery metadata, rating) and lightweight dish fields (`name`, `description`, `price`, `tags`, recommendation flags).
- `api/schemas.py` mirrors this lightweight shape. Merchant summary and dish responses do not expose contact details, business hours, or structured culinary metadata.
- `database/seeds/merchant_seed_data.py` now contains curated merchants and differentiated menus, but the dish payload still only carries the minimal fields required by the existing schema.
- `tools/seed_catalog_data.py` seeds merchants, dish categories, and dishes into the database from the current seed payload.
- The running backend reads from MySQL via `.env`, so reseeding the active database is required for runtime changes to appear.

## Recommended Approach

Adopt a **structured field expansion** approach on the existing `Merchant` and `Dish` models.

This means extending the existing catalog tables with retrieval-friendly first-class columns rather than creating side tables or hiding the new data in freeform text. The seed file remains the single source of truth. The seeding pipeline continues to ingest merchant and dish payloads, but those payloads become richer and more explicit.

This is the best fit because:
- RAG benefits from clearly separable fields rather than only long descriptions,
- the current codebase is small enough that direct model expansion is simpler than metadata side tables,
- existing catalog routes can expose the new fields with modest service/schema changes,
- the user explicitly wants realistic, structured business and dish information for retrieval.

## Alternatives Considered

### Option A — Recommended: Expand existing `Merchant` and `Dish` tables
- Add new merchant and dish columns directly to the current schema.
- Extend seed payloads and API schemas accordingly.

**Why recommended:** simplest runtime model, easiest querying, clearest retrieval semantics, and lowest long-term complexity for this codebase.

### Option B — Add separate metadata tables
- Keep core merchant/dish tables mostly unchanged.
- Store additional detail in `merchant_metadata` and `dish_metadata` tables.

**Tradeoff:** reduces direct changes to the existing tables, but introduces more joins, more files, and unnecessary modeling overhead for a demo-focused project.

### Option C — Keep schema minimal and pack detail into text fields
- Store most new attributes inside `description` or `tags`.

**Tradeoff:** fastest short-term path, but poor for later retrieval, filtering, reasoning, and explicit API contracts. This does not meet the stated RAG goal well.

## Design

### 1. Merchant metadata model

Extend `Merchant` with richer operational and retrieval-oriented fields while preserving current delivery and location fields.

New merchant attributes should include:
- `phone`
- `business_hours`
- `detailed_address`
- `address_note`
- `merchant_tags`

Field intent:
- `phone`: stable contact number for retrieval and operational realism.
- `business_hours`: human-readable schedule such as `10:00-21:30` or `09:30-14:00, 16:30-22:00`.
- `detailed_address`: more precise address than the current district-level anchor, including building/shop detail where appropriate.
- `address_note`: landmark or locality hints such as near a metro exit, office tower, or mall block.
- `merchant_tags`: structured labels that help retrieval differentiate stores beyond homepage category, e.g. `['写字楼午餐', '现炒', '夜宵']`.

Existing `longitude` and `latitude` remain required and should be made more precise in seed data rather than treated as placeholders.

### 2. Dish metadata model

Extend `Dish` with structured culinary attributes instead of relying on description and tags alone.

New dish attributes should include:
- `cuisine_type`
- `flavor_profile`
- `ingredients`
- `allergens`
- `cooking_method`

Field intent:
- `cuisine_type`: broad cuisine/classification such as `川菜`, `湘菜`, `日料`, `轻食`, `咖啡甜品`.
- `flavor_profile`: compact taste descriptor such as `酸甜微辣`, `香辣`, `咸鲜`, `奶香`.
- `ingredients`: structured array of major ingredients.
- `allergens`: structured array of allergen warnings.
- `cooking_method`: preparation style such as `爆炒`, `炙烤`, `油炸`, `焗烤`, `炖煮`.

`description` remains as the natural-language summary. The structured fields do not replace it; they complement it.

### 3. Schema storage choices

At the ORM and API boundary, `ingredients`, `allergens`, and `merchant_tags` should behave as `list[str]`.

At the database layer, implementation should prefer a JSON-capable column type if the current MySQL environment supports it cleanly. If project compatibility or tooling makes JSON awkward, storing JSON-encoded text is acceptable as long as:
- ORM read/write logic preserves `list[str]` semantics,
- API responses expose actual arrays,
- seed validation ensures the data remains structured rather than ad hoc strings.

This keeps the public contract stable even if storage details vary.

### 4. Seed data authoring

`database/seeds/merchant_seed_data.py` remains the only authored source for merchant and dish metadata.

Merchant seed entries should be expanded to include:
- more precise addresses,
- more realistic per-store longitude/latitude offsets,
- business hours,
- phone numbers,
- retrieval-friendly tags,
- address notes.

Dish seed entries should be expanded so each dish includes:
- natural-language description,
- cuisine type,
- flavor profile,
- ingredients array,
- allergens array,
- cooking method.

The seed authoring style should continue to favor **curated merchant instances** and differentiated menu variants. The new structure should make dishes from same-category merchants meaningfully distinct not only by name, but also by ingredients, flavor, method, and allergen metadata.

### 5. Seed pipeline changes

`tools/seed_catalog_data.py` should remain the sole catalog seeding entrypoint, but it must be updated to write the richer merchant and dish fields into the expanded schema.

The pipeline should continue to:
- clear catalog tables,
- insert merchants,
- insert dish categories,
- insert dishes.

The difference is that merchant and dish inserts will now include the new structured attributes. The pipeline should not add extra transformation layers beyond what is needed to persist arrays consistently.

### 6. API surface changes

Expose the new metadata through the existing catalog API instead of creating a separate RAG-only API.

Planned API changes:
- `/catalog/merchants` should return current summary fields plus merchant contact/location/operational metadata needed downstream.
- the existing merchant dishes endpoint should return the richer dish metadata fields alongside current fields.

Because this is a backend-first iteration, frontend screens do not need to immediately render every new field. But the API contract should already make the data available for later UI expansion, retrieval experiments, or downstream indexing.

### 7. Migration and reseed strategy

This iteration should use a **migration + reseed** workflow.

Process:
1. Add the new merchant and dish columns through the project’s schema migration path.
2. Reseed merchant and dish data from the updated seed payload.
3. Leave unrelated business data outside merchant/dish scope alone unless catalog table clearing already affects them indirectly.

Because the user approved rebuildable merchant/dish seed data, preserving legacy merchant IDs, names, or dish rows is not a requirement.

### 8. Testing and verification

Automated verification should cover both data shape and API exposure.

Required checks:
- seed payload tests confirm every merchant contains richer address/contact/operational fields,
- seed payload tests confirm every dish includes the new structured metadata fields,
- API tests verify merchant responses serialize the new merchant fields,
- API tests verify dish responses serialize the new dish fields with arrays, not flattened strings,
- targeted reseed verification confirms the active runtime database shows the new metadata through `/catalog/merchants` and merchant dish endpoints.

Manual verification after reseeding:
- sample merchants have realistic phone numbers and business hours,
- sample merchants within the same homepage category still differ meaningfully,
- sample dishes in related categories differ in ingredients/flavor/method metadata,
- API responses are suitable for later indexing without needing text scraping.

## Non-Goals

- No homepage layout redesign.
- No dedicated RAG pipeline, embedding job, or vector database in this iteration.
- No attempt to model full nutrition, calories, or supply-chain provenance.
- No expansion into order history or user preference retrieval.
- No separate merchant-admin editing workflow.

## Risks and Mitigations

- **Risk: metadata becomes verbose but still templated.**  
  Mitigation: enforce variation at both merchant and dish level, not just field presence.

- **Risk: array storage becomes awkward across ORM, migration, and API layers.**  
  Mitigation: standardize on `list[str]` at the schema boundary and encapsulate storage conversion in one place if needed.

- **Risk: active runtime DB still serves stale data after code changes.**  
  Mitigation: include reseed verification against the live configured database, not just unit tests.

- **Risk: scope drifts into frontend redesign.**  
  Mitigation: keep this iteration backend-first; frontend only needs to remain compatible.
