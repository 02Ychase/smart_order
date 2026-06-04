from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import requests

from data_pipeline.models import RawMerchant


AMAP_PLACE_TEXT_URL = "https://restapi.amap.com/v3/place/text"


def _first_string(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def _parse_rating(poi: dict[str, Any]) -> float | None:
    biz_ext = poi.get("biz_ext") or {}
    rating = biz_ext.get("rating")
    try:
        return float(rating)
    except (TypeError, ValueError):
        return None


def _parse_tags(poi: dict[str, Any]) -> list[str]:
    raw_tag = _first_string(poi.get("tag"))
    tags = [tag.strip() for tag in raw_tag.replace(";", ",").split(",") if tag.strip()]
    poi_type = _first_string(poi.get("type"))
    if poi_type:
        tags.extend(part.strip() for part in poi_type.split(";") if part.strip())
    return list(dict.fromkeys(tags))


def parse_amap_poi(poi: dict[str, Any]) -> RawMerchant:
    location = _first_string(poi.get("location"))
    longitude_text, latitude_text = (location.split(",", 1) + ["0"])[:2] if location else ("0", "0")
    return RawMerchant(
        source="amap",
        source_id=_first_string(poi.get("id")),
        name=_first_string(poi.get("name")),
        city=_first_string(poi.get("cityname")),
        district=_first_string(poi.get("adname")),
        address=_first_string(poi.get("address")),
        longitude=float(longitude_text or 0),
        latitude=float(latitude_text or 0),
        category=_first_string(poi.get("type")),
        phone=_first_string(poi.get("tel")),
        rating=_parse_rating(poi),
        tags=_parse_tags(poi),
        raw=poi,
    )


class AmapMerchantSource:
    def __init__(self, api_key: str, session=None, base_url: str = AMAP_PLACE_TEXT_URL) -> None:
        self.api_key = api_key
        self.session = session or requests.Session()
        self.base_url = base_url

    def fetch(
        self,
        *,
        city: str,
        keywords: Iterable[str],
        limit: int,
        page_size: int = 25,
    ) -> Iterable[RawMerchant]:
        if not self.api_key:
            raise RuntimeError("AMAP_API_KEY is required for merchant fetching")

        yielded = 0
        offset = min(max(page_size, 1), 25)
        for keyword in keywords:
            page = 1
            while yielded < limit:
                payload = self._fetch_page(city=city, keyword=keyword, page=page, offset=offset)
                pois = payload.get("pois") or []
                if not pois:
                    break
                for poi in pois:
                    if yielded >= limit:
                        break
                    merchant = parse_amap_poi(poi)
                    if merchant.name and merchant.source_id:
                        yielded += 1
                        yield merchant
                page += 1
            if yielded >= limit:
                break

    def _fetch_page(self, *, city: str, keyword: str, page: int, offset: int) -> dict[str, Any]:
        params = {
            "key": self.api_key,
            "keywords": keyword,
            "types": "050000",
            "city": city,
            "citylimit": "true",
            "offset": offset,
            "page": page,
            "extensions": "all",
            "output": "json",
        }
        response = self.session.get(self.base_url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "1":
            info = payload.get("info") or "unknown AMap error"
            raise RuntimeError(f"AMap merchant fetch failed: {info}")
        return payload
