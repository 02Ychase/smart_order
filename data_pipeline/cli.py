from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from api.db import SessionLocal
from data_pipeline.config import PipelineConfig
from data_pipeline.models import RawDish, RawMerchant
from data_pipeline.normalizers.dish_normalizer import normalize_dish
from data_pipeline.normalizers.menu_matcher import build_menu_assignments
from data_pipeline.normalizers.merchant_normalizer import normalize_merchant
from data_pipeline.sources.amap import AmapMerchantSource
from data_pipeline.sources.xiachufang import XiaChuFangDishSource
from data_pipeline.storage.catalog_writer import CatalogWriter
from data_pipeline.storage.dedupe import dedupe_dishes, dedupe_merchants
from data_pipeline.vector.sync import sync_catalog_vectors


def write_jsonl(path: str | Path, records) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            payload = asdict(record) if is_dataclass(record) else record
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path):
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _raw_merchant_from_dict(payload: dict[str, Any]) -> RawMerchant:
    return RawMerchant(**payload)


def _raw_dish_from_dict(payload: dict[str, Any]) -> RawDish:
    return RawDish(**payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m data_pipeline.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_merchants = subparsers.add_parser("fetch-merchants")
    fetch_merchants.add_argument("--city", default=None)
    fetch_merchants.add_argument("--keywords", default="restaurant,food")
    fetch_merchants.add_argument("--limit", type=int, default=None)
    fetch_merchants.add_argument("--output", required=True)

    fetch_dishes = subparsers.add_parser("fetch-dishes")
    fetch_dishes.add_argument("--source", choices=["xiachufang"], default="xiachufang")
    fetch_dishes.add_argument("--input", required=True)
    fetch_dishes.add_argument("--limit", type=int, default=None)
    fetch_dishes.add_argument("--output", required=True)

    load_db = subparsers.add_parser("load-db")
    load_db.add_argument("--merchants", required=True)
    load_db.add_argument("--dishes", required=True)
    load_db.add_argument("--dishes-per-merchant", type=int, default=20)
    load_db.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("sync-vector")

    run_all = subparsers.add_parser("run-all")
    run_all.add_argument("--city", default=None)
    run_all.add_argument("--merchant-limit", type=int, default=None)
    run_all.add_argument("--dish-limit", type=int, default=None)
    run_all.add_argument("--dish-input", required=True)
    run_all.add_argument("--work-dir", default=None)
    run_all.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    config = PipelineConfig.from_env()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch-merchants":
        source = AmapMerchantSource(api_key=config.amap_api_key)
        merchants = source.fetch(
            city=args.city or config.default_city,
            keywords=[item.strip() for item in args.keywords.split(",") if item.strip()],
            limit=args.limit or config.default_merchant_limit,
        )
        write_jsonl(args.output, merchants)
        print(f"wrote merchants to {args.output}")
        return 0

    if args.command == "fetch-dishes":
        source = XiaChuFangDishSource(args.input)
        dishes = source.fetch(limit=args.limit or config.default_dish_limit)
        write_jsonl(args.output, dishes)
        print(f"wrote dishes to {args.output}")
        return 0

    if args.command == "load-db":
        raw_merchants = [_raw_merchant_from_dict(payload) for payload in read_jsonl(args.merchants)]
        raw_dishes = [_raw_dish_from_dict(payload) for payload in read_jsonl(args.dishes)]
        merchants = dedupe_merchants([normalize_merchant(raw) for raw in raw_merchants])
        dishes = dedupe_dishes([normalize_dish(raw) for raw in raw_dishes])
        assignments = build_menu_assignments(merchants, dishes, dishes_per_merchant=args.dishes_per_merchant)
        if args.dry_run:
            print(f"dry-run merchants={len(merchants)} dishes={len(dishes)} assignments={len(assignments)}")
            return 0
        session = SessionLocal()
        try:
            summary = CatalogWriter(session).write(assignments)
            print(asdict(summary))
        finally:
            session.close()
        return 0

    if args.command == "sync-vector":
        session = SessionLocal()
        try:
            print(sync_catalog_vectors(session=session))
        finally:
            session.close()
        return 0

    if args.command == "run-all":
        work_dir = Path(args.work_dir or config.raw_dir)
        merchant_path = work_dir / "merchants.jsonl"
        dish_path = work_dir / "dishes.jsonl"
        main(["fetch-merchants", "--city", args.city or config.default_city, "--limit", str(args.merchant_limit or config.default_merchant_limit), "--output", str(merchant_path)])
        main(["fetch-dishes", "--source", "xiachufang", "--input", args.dish_input, "--limit", str(args.dish_limit or config.default_dish_limit), "--output", str(dish_path)])
        load_args = ["load-db", "--merchants", str(merchant_path), "--dishes", str(dish_path)]
        if args.dry_run:
            load_args.append("--dry-run")
        main(load_args)
        if not args.dry_run:
            main(["sync-vector"])
        return 0

    parser.error(f"unsupported command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
