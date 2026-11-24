#!/usr/bin/env python3
"""新增或更新每日連結總站的一筆連結。"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

CATEGORIES = ("新聞", "洞察", "X", "學習", "記帳", "週末")
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


def clean_link(link):
    if not isinstance(link, dict):
        return None
    title = str(link.get("title") or "").strip()
    href = str(link.get("href") or "").strip()
    note = str(link.get("note") or "").strip()
    if not title or not href:
        return None
    cleaned = {"title": title, "href": href}
    if note:
        cleaned["note"] = note
    return cleaned


def clean_item(item):
    if not isinstance(item, dict):
        return None
    tab = str(item.get("tab") or "").strip()
    if tab:
        links = []
        for link in item.get("links") or []:
            cleaned = clean_link(link)
            if cleaned:
                links.append(cleaned)
        if not links:
            return None
        return {
            "category": item.get("category"),
            "tab": tab,
            "bot": item.get("bot"),
            "links": links,
        }
    return {
        "category": item.get("category"),
        "bot": item.get("bot"),
        "title": item.get("title"),
        "href": item.get("href"),
    }


def canonical_items(items):
    """同一類別的一般連結只留最後一筆；帶 tab 的清單另計，不會互相覆蓋。"""
    plain = {}
    tabs = {}
    tab_order = []
    extras = []
    for item in items:
        cleaned = clean_item(item)
        if cleaned is None:
            continue
        category = cleaned.get("category")
        tab = cleaned.get("tab")
        if tab:
            key = (category, tab)
            if key not in tabs:
                tab_order.append(key)
            tabs[key] = cleaned
        elif category in CATEGORIES:
            plain[category] = cleaned
        else:
            extras.append(cleaned)
    ordered = []
    for name in CATEGORIES:
        if name in plain:
            ordered.append(plain[name])
        for key in tab_order:
            if key[0] == name:
                ordered.append(tabs[key])
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


def upsert(days, day, category, bot, title, href):
    bucket = day_bucket(days, day)
    bucket["items"] = [
        item for item in bucket["items"]
        if not (item.get("category") == category and not item.get("tab"))
    ]
    bucket["items"].append(
        {"category": category, "bot": bot, "title": title, "href": href}
    )
    bucket["items"] = canonical_items(bucket["items"])


def upsert_tab(days, day, category, tab, bot, links):
    bucket = day_bucket(days, day)
    bucket["items"] = [
        item for item in bucket["items"]
        if not (item.get("category") == category and item.get("tab") == tab)
    ]
    bucket["items"].append(
        {"category": category, "tab": tab, "bot": bot, "links": links}
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


def parse_link_arg(value):
    parts = str(value).split("|")
    if len(parts) < 3:
        raise argparse.ArgumentTypeError("連結須為 title|note|href")
    title = parts[0].strip()
    href = parts[-1].strip()
    note = "|".join(parts[1:-1]).strip()
    if not title or not href:
        raise argparse.ArgumentTypeError("連結的 title 與 href 不可為空白")
    cleaned = {"title": title, "href": href}
    if note:
        cleaned["note"] = note
    return cleaned


def load_links_json(path):
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise SystemExit("--links-json 必須是陣列")
    links = []
    for entry in payload:
        cleaned = clean_link(entry)
        if cleaned is None:
            raise SystemExit("--links-json 含有缺少 title 或 href 的項目")
        links.append(cleaned)
    return links


def build_parser():
    parser = argparse.ArgumentParser(description="新增或更新每日連結總站的一筆連結")
    parser.add_argument("--date", required=True, type=parse_date, help="YYYY-MM-DD")
    parser.add_argument("--category", required=True, choices=CATEGORIES)
    parser.add_argument("--bot", required=True, help="來源 bot 名稱")
    parser.add_argument("--title", help="連結標題")
    parser.add_argument("--href", help="連結網址")
    parser.add_argument("--tab", help="X 類別底下的分頁，例如 AI 免費額度")
    parser.add_argument(
        "--link",
        action="append",
        default=[],
        dest="links",
        type=parse_link_arg,
        help="分頁清單的一筆，格式 title|note|href，可重複",
    )
    parser.add_argument("--links-json", help="分頁清單 JSON 檔，內容為 [{title, note, href}, ...]")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not str(args.bot).strip():
        parser.error("bot 不可為空白")

    data = load_data()
    days = merge_days(list(data.get("days") or []) + list(data.get("history") or []))
    if args.tab:
        if args.category != "X":
            parser.error("--tab 只用於類別 X")
        links = []
        if args.links_json:
            links.extend(load_links_json(args.links_json))
        links.extend(args.links or [])
        if not links:
            parser.error("請用 --link 或 --links-json 提供清單")
        upsert_tab(days, args.date, args.category, args.tab.strip(), args.bot, links)
    else:
        if args.links or args.links_json:
            parser.error("沒有 --tab 時不要使用 --link 或 --links-json")
        if not str(args.title or "").strip() or not str(args.href or "").strip():
            parser.error("bot、title、href 不可為空白")
        upsert(days, args.date, args.category, args.bot, args.title, args.href)
    recent, older = partition(days)
    payload = {"days": recent, "history": older}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    DATA_PATH.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
