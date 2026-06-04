from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from data_pipeline.models import RawDish


def _first_text(record: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = record.get(key)
        if not value:
            continue
        if isinstance(value, list):
            return "; ".join(str(item).strip() for item in value[:5] if str(item).strip())
        return str(value).strip()
    return ""


def _list_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        separators = ["\n", ",", ";", " "]
        items = [value]
        for separator in separators:
            if separator in value:
                items = value.split(separator)
                break
        return [item.strip() for item in items if item.strip()]
    return []


def _clean_name(name: str) -> str:
    """Extract core dish name, remove marketing language and descriptions."""
    import re

    # Remove emoji
    name = re.sub(r"[\U0001f300-\U0001f9ff\U00002700-\U000027bf\U0000fe00-\U0000fe0f\U0000200d]", "", name)
    # Remove bracket symbols but keep content inside
    name = re.sub(r"[【】『』「」\[\]]", "", name)
    # Remove parenthetical content entirely (usually version/method notes)
    name = re.sub(r"[（(][^）)]*[）)]", "", name)
    # Remove marketing words anywhere in the name
    marketing_words = [
        "懒人版", "懒人", "万能", "零失败", "超好吃的", "超好吃", "超简单",
        "新手必学", "简易版", "家庭版", "自制", "秘制", "独家", "私房",
        "外焦里嫩", "入口即化", "好吃到哭", "绝绝子", "巨好吃",
        "成功率超高", "真的绝", "超过瘾", "秒杀外面", "完胜饭店",
        "比外面好吃", "一学就会", "一看就会", "手把手教你",
        "快手", "成功率", "超高的", "免揉面", "美颜补血", "隔壁邻居都知道",
        "成功率", "超高的", "免揉面", "美颜补血", "隔壁邻居都知道",
        "简单美味", "简单快手", "好吃不贵", "经济实惠", "特香",
        "的家常做法", "的详细做法", "的最正宗做法", "怎么做", "的做法",
    ]
    for word in marketing_words:
        name = name.replace(word, "")
    # Split by common separators and take the first meaningful part
    # e.g., "特香碌鹅-鼓油鹅-酱油鹅" -> "碌鹅"
    parts = re.split(r"[-—、，,]", name)
    if len(parts) > 1:
        # Take the shortest part that's >= 2 chars (likely the core name)
        candidates = [p.strip() for p in parts if len(p.strip()) >= 2]
        if candidates:
            name = min(candidates, key=len)
    # Remove leading adjectives and particles
    name = re.sub(r"^[超特最很非常]+[好吃香嫩脆酥鲜甜辣的]+", "", name)
    name = re.sub(r"^的+", "", name)
    # Remove remaining special chars
    name = re.sub(r"[～~—\-·•！!？?+＋\s]+", " ", name).strip()
    # Remove leading/trailing punctuation
    name = name.strip("，。、；：""''「」『』（）()【】[]的")
    # If name is too short after cleaning, return empty (skip this dish)
    if len(name) < 2:
        return ""
    return name[:12]


def _clean_description(desc: str) -> str:
    """Truncate and clean description, remove personal stories and marketing."""
    if not desc:
        return ""
    import re

    # Remove URLs
    desc = re.sub(r"https?://\S+", "", desc)
    # Remove WeChat/公众号 references
    desc = re.sub(r"微信公众号\S+", "", desc)
    desc = re.sub(r"关注\S+公众号", "", desc)
    # Remove personal narratives
    personal_patterns = [
        r"儿子.{0,20}(不|想|爱|喜)", r"老公.{0,20}(加班|出差|不)",
        r"老婆.{0,10}说", r"爸爸.{0,10}(做|煮|炒)", r"妈妈.{0,10}(做|教|说)",
        r"孩子.{0,10}(不|爱|喜|想)", r"闺蜜.{0,10}(推荐|说|分享)",
        r"室友.{0,10}(说|尝)", r"同事.{0,10}(说|尝|问)",
        r"男朋友.{0,10}", r"女朋友.{0,10}",
        r"家人.{0,10}(秘方|最爱|喜欢)", r"全家.{0,10}(都|一)",
        r"第一次发", r"有点小激动", r"甚是想念",
        r"疫情宅家", r"在家无聊", r"周末在家",
    ]
    for pattern in personal_patterns:
        desc = re.sub(pattern, "", desc)
    # Remove marketing language
    marketing_in_desc = [
        "小白易学", "一学就会", "零失败", "超好吃", "绝绝子",
        "好吃到哭", "超过瘾", "秒杀外面", "完胜饭店",
        "巨好吃", "真的绝", "强烈推荐", "必做",
    ]
    for phrase in marketing_in_desc:
        desc = desc.replace(phrase, "")
    # Truncate at sentence boundary near 80 chars
    desc = desc.strip()
    if len(desc) > 80:
        cut = desc[:80]
        for sep in ["。", "！", "；", ".", "!", ";"]:
            last = cut.rfind(sep)
            if last > 30:
                cut = cut[: last + 1]
                break
        desc = cut
    return desc.strip()


def _clean_ingredients(ingredients: list[str]) -> list[str]:
    """Remove section headers and clean ingredient names."""
    import re
    cleaned = []
    for item in ingredients:
        item = item.strip()
        # Skip section headers
        if item.startswith("#") or re.match(r"^[主辅]\s*料", item):
            continue
        if item.startswith("【") and item.endswith("】"):
            continue
        # Skip empty or very short items
        if len(item) < 2:
            continue
        # Skip items that are just punctuation or numbers
        if re.match(r"^[\d\s\.\-\/]+$", item):
            continue
        cleaned.append(item)
    return cleaned[:12]


def _clean_tags(tags: list[str], name: str) -> list[str]:
    """Remove auto-generated and generic tags."""
    skip_tags = {
        "做法", "家常菜", "快手菜", "下饭菜", "家常", "简单",
        "详细做法", "正宗做法", "自制", "懒人", "快手",
    }
    cleaned = []
    for tag in tags:
        tag = tag.strip()
        if not tag or len(tag) > 8 or len(tag) < 2:
            continue
        if tag in skip_tags:
            continue
        # Skip tags containing marketing or auto-generated words
        if any(w in tag for w in ["做法", "家常", "懒人", "快手", "简单", "详细", "怎么做", "正宗"]):
            continue
        cleaned.append(tag)
    return cleaned[:3]


def extract_xiachufang_record(record: dict[str, Any]) -> RawDish | None:
    name = _first_text(record, ("name", "title", "recipe_name", "dish_name"))
    if not name:
        return None
    name = _clean_name(name)
    if not name:
        return None
    source_id = _first_text(record, ("id", "recipe_id", "url")) or name
    ingredients = _clean_ingredients(_list_text(
        record.get("ingredients")
        or record.get("ingredient")
        or record.get("recipeIngredient")
        or record.get("ings")
    ))
    if not ingredients:
        return None
    description = _first_text(record, ("desc", "description", "steps", "instruction", "instructions", "recipeInstructions"))
    if not description:
        steps = record.get("recipeInstructions")
        if isinstance(steps, list):
            description = "; ".join(str(s) for s in steps[:5])
    description = _clean_description(description)
    tags = _clean_tags(
        _list_text(record.get("tags") or record.get("category") or record.get("categories") or record.get("keywords")),
        name,
    )
    return RawDish(
        source="xiachufang",
        source_id=source_id,
        name=name,
        description=description,
        ingredients=ingredients,
        tags=tags,
        cuisine_type="",
        price=None,
        raw=record,
    )


def iter_json_records(path: Path) -> Iterable[dict[str, Any]]:
    """Stream-read JSONL line by line; fall back to full parse for JSON arrays."""
    with path.open("r", encoding="utf-8-sig") as handle:
        first_char = ""
        while True:
            chunk = handle.read(1)
            if not chunk:
                return
            if not chunk.isspace():
                first_char = chunk
                break

        if first_char == "[":
            handle.seek(0)
            for item in json.loads(handle.read()):
                if isinstance(item, dict):
                    yield item
            return

        handle.seek(0)
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            item = json.loads(stripped)
            if isinstance(item, dict):
                yield item


class XiaChuFangDishSource:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def fetch(self, *, limit: int) -> Iterable[RawDish]:
        if not self.path.exists():
            raise RuntimeError(f"XiaChuFang dataset file not found: {self.path}")
        yielded = 0
        for record in iter_json_records(self.path):
            dish = extract_xiachufang_record(record)
            if dish is None:
                continue
            yielded += 1
            yield dish
            if yielded >= limit:
                break
