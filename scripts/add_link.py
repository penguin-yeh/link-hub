#!/usr/bin/env python3
"""新增或更新每日連結總站的一筆連結。"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

CATEGORIES = ("新聞", "洞察", "X", "學習", "記帳", "省錢", "週末")
WEEKDAYS = "一二三四五六日"
ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data.json"
WINDOW_DAYS = 30


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期須為 YYYY-MM-DD") from exc


def weekday_label(day):
    return f"{day.isoformat()}（{WEEKDAYS[day.weekday()]}）"


def load_data():
    if not DATA_PATH.exists():
        return {"days": [], "history": []}
    with DATA_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("data.json 格式不正確")
    data.setdefault("days", [])
    data.setdefault("history", [])
    return data


def item_slot(item):
    """Dedupe slot for a plain item; missing or blank slot equals the category name."""
    slot = item.get("slot")
    if slot is None or not str(slot).strip():
        return item.get("category")
    return str(slot).strip()


def clean_item(item):
    if not isinstance(item, dict):
        return None
    href = item.get("href")
    if not isinstance(href, str) or not href.strip():
        return None
    cleaned = {
        "category": item.get("category"),
        "bot": item.get("bot"),
        "title": item.get("title"),
        "href": item.get("href"),
    }
    slot = item_slot(item)
    if slot and slot != cleaned["category"]:
        cleaned["slot"] = slot
    return cleaned


def canonical_items(items):
    """同一 (類別, slot) 的一般連結只留最後一筆。
    未指定 slot 時等同於類別名，因此沒加 --slot 的行為與以前相同。"""
    plain = {}
    extras = []
    for item in items:
        cleaned = clean_item(item)
        if cleaned is None:
            continue
        category = cleaned.get("category")
        if category in CATEGORIES:
            plain[(category, item_slot(cleaned))] = cleaned
        else:
            extras.append(cleaned)
    ordered = []
    for name in CATEGORIES:
        if (name, name) in plain:
            ordered.append(plain[(name, name)])
        for (category, slot), entry in plain.items():
            if category == name and slot != name:
                ordered.append(entry)
    ordered.extend(extras)
    return ordered


def normalize_day(bucket):
    date = bucket.get("date")
    if not isinstance(date, str):
        raise SystemExit("data.json 含有缺少日期的項目")
    day = parse_date(date)
    return {
        "date": day.isoformat(),
        "label": weekday_label(day),
        "items": canonical_items(bucket.get("items") or []),
    }


def merge_days(groups):
    merged = {}
    for bucket in groups:
        if not isinstance(bucket, dict) or "date" not in bucket:
            continue
        date = bucket["date"]
        if date not in merged:
            merged[date] = {
                "date": date,
                "label": bucket.get("label", date),
                "items": list(bucket.get("items") or []),
            }
        else:
            merged[date]["items"].extend(bucket.get("items") or [])
    return [normalize_day(bucket) for bucket in merged.values()]


def day_bucket(days, day):
    iso = day.isoformat()
    bucket = next((entry for entry in days if entry["date"] == iso), None)
    if bucket is None:
        bucket = {"date": iso, "label": weekday_label(day), "items": []}
        days.append(bucket)
    bucket["label"] = weekday_label(day)
    bucket["items"] = canonical_items(bucket.get("items") or [])
    return bucket


def upsert(days, day, category, bot, title, href, slot=None):
    bucket = day_bucket(days, day)
    slot = slot if slot is not None and str(slot).strip() else category
    bucket["items"] = [
        item for item in bucket["items"]
        if not (item.get("category") == category and item_slot(item) == slot)
    ]
    entry = {"category": category, "bot": bot, "title": title, "href": href}
    if slot != category:
        entry["slot"] = slot
    bucket["items"].append(entry)
    bucket["items"] = canonical_items(bucket["items"])


def partition(days):
    if not days:
        return [], []
    newest = max(datetime.strptime(entry["date"], "%Y-%m-%d").date() for entry in days)
    cutoff = newest - timedelta(days=WINDOW_DAYS)
    recent = []
    older = []
    for entry in days:
        when = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        if when < cutoff:
            older.append(entry)
        else:
            recent.append(entry)
    recent.sort(key=lambda entry: entry["date"], reverse=True)
    older.sort(key=lambda entry: entry["date"], reverse=True)
    return recent, older


def build_parser():
    parser = argparse.ArgumentParser(description="新增或更新每日連結總站的一筆連結")
    parser.add_argument("--date", required=True, type=parse_date, help="YYYY-MM-DD")
    parser.add_argument("--category", required=True, choices=CATEGORIES)
    parser.add_argument("--bot", required=True, help="來源 bot 名稱")
    parser.add_argument("--title", required=True, help="連結標題")
    parser.add_argument("--href", required=True, help="連結網址")
    parser.add_argument(
        "--slot",
        default=None,
        help="同一天、同一類別內的區分鍵。預設等於 --category，因此不加時行為與以前相同。"
             "例如 AI 爆紅精選用 --category X --slot ai-picks，才不會蓋掉當天的 X 早報／晚間整理。",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not str(args.bot).strip() or not str(args.title).strip() or not str(args.href).strip():
        parser.error("bot、title、href 不可為空白")
    if args.slot is not None and not str(args.slot).strip():
        parser.error("--slot 不可為空白")

    data = load_data()
    days = merge_days(list(data.get("days") or []) + list(data.get("history") or []))
    upsert(days, args.date, args.category, args.bot, args.title, args.href, slot=args.slot)
    recent, older = partition(days)
    payload = {"days": recent, "history": older}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    DATA_PATH.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
