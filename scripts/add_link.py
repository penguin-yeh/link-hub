#!/usr/bin/env python3
"""新增或更新每日連結總站的一筆連結。"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

CATEGORIES = ("新聞", "洞察", "X", "技術精讀", "週末")
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


def canonical_items(items):
    """同一類別只留最後一筆，並依固定類別順序排列。"""
    by_category = {}
    extras = []
    for item in items:
        cleaned = {
            "category": item.get("category"),
            "bot": item.get("bot"),
            "title": item.get("title"),
            "href": item.get("href"),
        }
        category = cleaned["category"]
        if category in CATEGORIES:
            by_category[category] = cleaned
        else:
            extras.append(cleaned)
    ordered = [by_category[name] for name in CATEGORIES if name in by_category]
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


def upsert(days, day, category, bot, title, href):
    iso = day.isoformat()
    bucket = next((entry for entry in days if entry["date"] == iso), None)
    if bucket is None:
        bucket = {"date": iso, "label": weekday_label(day), "items": []}
        days.append(bucket)
    bucket["label"] = weekday_label(day)
    bucket["items"] = canonical_items(bucket["items"])
    bucket["items"] = [item for item in bucket["items"] if item.get("category") != category]
    bucket["items"].append(
        {"category": category, "bot": bot, "title": title, "href": href}
    )
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
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not str(args.bot).strip() or not str(args.title).strip() or not str(args.href).strip():
        parser.error("bot、title、href 不可為空白")

    data = load_data()
    days = merge_days(list(data.get("days") or []) + list(data.get("history") or []))
    upsert(days, args.date, args.category, args.bot, args.title, args.href)
    recent, older = partition(days)
    payload = {"days": recent, "history": older}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    DATA_PATH.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
