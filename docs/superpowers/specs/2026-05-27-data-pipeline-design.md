# Data Pipeline Design

Date: 2026-05-27

## Goal

Build a dedicated `data_pipeline/` package that can collect real merchant data and large-scale real dish data, normalize it into the existing Smart Order catalog schema, store it in the relational database, and sync the resulting catalog into the existing Pinecone vector database.

The first implementation targets:

- Real merchant data from AMap POI search.
- Large-scale real dish data from open recipe/menu datasets, with XiaChuFang as the primary Chinese dish source.
- Reuse of the current `Merchant`, `DishCategory`, and `Dish` SQLAlchemy models.
- Reuse of the current `IndexingPipeline` and `AssistantVectorStore` for vector sync.

## Context

The current project already has:

- Catalog ORM models in `api/models/catalog.py`.
- Catalog seed insertion in `tools/seed_catalog_data.py`.
- Catalog read APIs through `CatalogService`.
- Vector indexing in `tools/indexing_pipeline.py`.
- Pinecone integration in `tools/assistant_vector_store.py`.

The new package should not duplicate the assistant vector-store logic. It should prepare database records, then invoke the existing indexer.

## Data Sources

### Merchants

AMap POI search is the default merchant source. It provides restaurant POI fields such as name, type, address, location, telephone, district, and related POI metadata.

The pipeline will use configurable city, district, and restaurant keywords/type codes. The default target is Shanghai because current seed data and delivery assumptions are Shanghai-oriented.

### Dishes

The default dish source is XiaChuFang Recipe Corpus because it is Chinese, large, and contains enough dish names and recipe text for realistic catalog construction. Public dataset metadata reports about 1,520,327 Chinese recipes and 30,060 dishes.

Additional source adapters can be added without changing storage:

- MenuStat for chain restaurant menu/nutrition data.
- TheMealDB and OpenRecipes for international dishes.
- OpenMenu or Documenu for commercial menu APIs when API keys are available.

The first version treats dishes as real dish records but not necessarily as verified menu items of each AMap merchant. Matching dishes to merchants is heuristic by cuisine/category unless a source provides a direct restaurant-menu relationship.

## Package Layout

```text
data_pipeline/
  __init__.py
  cli.py
  config.py
  models.py
  sources/
    __init__.py
    amap.py
    xiachufang.py
    menustat.py
    themealdb.py
  normalizers/
    __init__.py
    merchant_normalizer.py
    dish_normalizer.py
    menu_matcher.py
  storage/
    __init__.py
    catalog_writer.py
    dedupe.py
  vector/
    __init__.py
    sync.py
  README.md
```

`models.py` will contain lightweight dataclasses for raw and normalized records. These are separate from ORM models to keep fetching and cleaning independent from database writes.

## Data Flow

1. Fetch merchant candidates from AMap.
2. Normalize merchant records into the existing merchant fields.
3. Fetch or load dish records from dataset/API sources.
4. Normalize dishes into project fields: name, description, price, tags, cuisine type, flavor profile, ingredients, allergens, cooking method, and recommendation flag.
5. Match normalized dishes to merchants by category/cuisine and create dish categories.
6. Upsert merchants, categories, and dishes into MySQL through SQLAlchemy.
7. Run the existing catalog indexing pipeline to upsert merchant and dish vectors to Pinecone.

## Database Mapping

Merchant records map to `Merchant`:

- `name`: AMap POI name.
- `description`: generated from POI category, address, and tags.
- `city`, `district`, `address`, `longitude`, `latitude`: from AMap.
- `homepage_category`: mapped from POI type or keyword group.
- `promo_text`: concise generated merchant summary.
- `delivery_radius_meters`, `delivery_fee`, `min_order_amount`, `avg_delivery_minutes`: deterministic defaults by merchant category and distance profile.
- `rating`: AMap rating when present, otherwise bounded deterministic default.
- `phone`, `business_hours`, `detailed_address`, `address_note`, `merchant_tags`: source fields plus normalized defaults.

Dish records map to `Dish`:

- `name`: real dish/recipe/menu item name.
- `description`: dataset description or generated concise dish summary from recipe text.
- `price`: inferred by cuisine/category price bands when the source has no price.
- `tags`: comma-separated normalized tags.
- `cuisine_type`: inferred from dish source, merchant category, or rule tables.
- `flavor_profile`: inferred from dish name, ingredients, and recipe text.
- `ingredients`: parsed ingredient list.
- `allergens`: inferred from ingredients using a small rule table.
- `cooking_method`: inferred from dish name and recipe text.
- `is_recommended`: deterministic score based on dish completeness and category balance.

## CLI

The package will expose a module CLI:

```powershell
python -m data_pipeline.cli fetch-merchants --city 上海 --limit 500 --output tmp/data_pipeline/merchants.jsonl
python -m data_pipeline.cli fetch-dishes --source xiachufang --limit 5000 --output tmp/data_pipeline/dishes.jsonl
python -m data_pipeline.cli load-db --merchants tmp/data_pipeline/merchants.jsonl --dishes tmp/data_pipeline/dishes.jsonl
python -m data_pipeline.cli sync-vector
python -m data_pipeline.cli run-all --city 上海 --merchant-limit 500 --dish-limit 5000
```

All raw or large intermediate files should go under `tmp/data_pipeline/` by default, not into tracked source files.

## Configuration

Configuration comes from environment variables and CLI options:

- `AMAP_API_KEY`: required for merchant fetching.
- `DATABASE_URL`: required for relational storage.
- `PINECONE_API_KEY`: required for vector sync.
- `PINECONE_ASSISTANT_INDEX`: optional, defaults to existing assistant index.
- `DASHSCOPE_API_KEY`: required by the existing embedding service when syncing vectors.

The package will also support dry-run mode so collection and normalization can be tested without writing to MySQL or Pinecone.

## Error Handling

- API calls use retries with backoff and clear rate-limit logging.
- Source adapters return partial results when one page fails, but record failures in the summary.
- Database writes are transactional per merchant batch.
- Duplicate merchants are detected by normalized name plus district/address, and optionally by source POI ID.
- Duplicate dishes are detected by normalized name plus cuisine/type.
- Vector sync is skipped with a clear summary if Pinecone is not configured, matching current project behavior.

## Testing

Focused tests will cover:

- AMap response parsing with fixture JSON.
- Dish dataset parsing with small fixture files.
- Normalization for merchant and dish required fields.
- Deduplication rules.
- Database writer behavior against an in-memory or test database session.
- Vector sync wrapper behavior using a fake vector store or fake `IndexingPipeline`.
- CLI dry-run command paths.

Network calls will not be made in tests. Tests use fixtures and fake clients.

## Non-Goals

- Do not bypass anti-bot systems, login walls, CAPTCHAs, or private app APIs.
- Do not claim AMap merchants and open dataset dishes are verified real menus for the same store unless a source provides that relation.
- Do not commit large raw datasets into git.
- Do not replace the existing catalog service or vector-store implementation.

## Approval

The approved first approach is: AMap merchant data plus large-scale real dish data from open datasets, stored into MySQL and synced to Pinecone using existing project infrastructure.
