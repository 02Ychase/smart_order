# Data Pipeline

This package collects real merchant data and large-scale real dish data for Smart Order.

## Sources

- Merchants: AMap POI search, configured by `AMAP_API_KEY`.
- Dishes: XiaChuFang recipe corpus as a large Chinese dish source. The pipeline reads a local JSON or JSONL export and writes normalized dish records.
- Optional dish helpers: MenuStat CSV exports and TheMealDB records.

The first version does not claim that a XiaChuFang dish is verified as sold by a specific AMap merchant. It uses real dish records and assigns them to matching merchant categories.

## Environment

```powershell
$env:AMAP_API_KEY="your-amap-key"
$env:DATABASE_URL="mysql+mysqlconnector://root:password@localhost:3306/smart_order"
$env:PINECONE_API_KEY="your-pinecone-key"
$env:DASHSCOPE_API_KEY="your-dashscope-key"
```

## Commands

```powershell
python -m data_pipeline.cli fetch-merchants --city Shanghai --keywords restaurant,food --limit 500 --output tmp/data_pipeline/merchants.jsonl
python -m data_pipeline.cli fetch-dishes --source xiachufang --input D:\datasets\xiachufang\recipes.jsonl --limit 5000 --output tmp/data_pipeline/dishes.jsonl
python -m data_pipeline.cli load-db --merchants tmp/data_pipeline/merchants.jsonl --dishes tmp/data_pipeline/dishes.jsonl --dry-run
python -m data_pipeline.cli load-db --merchants tmp/data_pipeline/merchants.jsonl --dishes tmp/data_pipeline/dishes.jsonl
python -m data_pipeline.cli sync-vector
python -m data_pipeline.cli run-all --city Shanghai --merchant-limit 500 --dish-limit 5000 --dish-input D:\datasets\xiachufang\recipes.jsonl
```

## Validation

Run focused tests:

```powershell
pytest tests/data_pipeline -v
```

Run the existing vector index test:

```powershell
pytest tests/service/test_indexing_pipeline.py -v
```

## Data Hygiene

Raw dataset files stay under `tmp/data_pipeline/` or an external dataset directory. Do not commit large raw datasets.
