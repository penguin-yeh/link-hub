#!/usr/bin/env python3
"""新增或更新每日連結總站的一筆連結。"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

CATEGORIES = ("新聞", "洞察", "X", "學習", "記帳", "省錢", "週末")
WEEKDAYS = "一二三四五六日"
ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data.json"
SAVINGS_DIR = ROOT / "savings"
SAVINGS_PUBLIC = "https://penguin-yeh.github.io/link-hub/savings"
WINDOW_DAYS = 30
GATE_SALT = "mv24FYlAQXqzWPt+kNbhdw=="
GATE_ITERATIONS = 200000
GATE_HASH = "3xAExdNY8/ArB2V6OVaNLkCIqCfvftk81PIMvdj9sIM="
GATE_KEY = "link-hub-gate"


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
    section = str(link.get("section") or "").strip()
    title = str(link.get("title") or "").strip()
    href = str(link.get("href") or "").strip()
    note = str(link.get("note") or "").strip()
    if not section or not title or not href:
        return None
    cleaned = {"section": section, "title": title, "href": href}
    if note:
        cleaned["note"] = note
    return cleaned


def item_slot(item):
    """Dedupe slot for a plain item; missing or blank slot equals the category name."""
    slot = item.get("slot")
    if slot is None or not str(slot).strip():
        return item.get("category")
    return str(slot).strip()


def clean_item(item):
    if not isinstance(item, dict):
        return None
    if isinstance(item.get("links"), list) and not str(item.get("href") or "").strip():
        return None
    if str(item.get("tab") or "").strip():
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


NOTE_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def render_note(note):
    if not note:
        return ""
    pieces = []
    cursor = 0
    for match in NOTE_LINK.finditer(note):
        pieces.append(html.escape(note[cursor:match.start()]))
        text = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        pieces.append(f'<a href="{url}" rel="noopener noreferrer">{text}</a>')
        cursor = match.end()
    pieces.append(html.escape(note[cursor:]))
    return "".join(pieces)


def group_sections(links):
    order = []
    groups = {}
    for link in links:
        name = link["section"]
        if name not in groups:
            order.append(name)
            groups[name] = []
        groups[name].append(link)
    return [(name, groups[name]) for name in order]


def write_savings_page(day, bot, links, page_title):
    label = weekday_label(day)
    esc = html.escape
    sections = []
    for name, entries in group_sections(links):
        rows = []
        for link in entries:
            note = link.get("note") or ""
            note_html = f'<p class="note">{render_note(note)}</p>' if note else ""
            rows.append(
                "<li>"
                f'<a href="{esc(link["href"], quote=True)}" rel="noopener noreferrer">{esc(link["title"])}</a>'
                f"{note_html}"
                "</li>"
            )
        sections.append(
            '<section class="group">'
            f"<h2>{esc(name)}</h2>"
            '<ul class="links">'
            + "\n          ".join(rows)
            + "</ul></section>"
        )
    items_html = "\n        ".join(sections)
    page = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>{esc(page_title)} · {esc(label)}</title>
  <link rel="icon" href="../favicon.svg" type="image/svg+xml">
  <link rel="icon" href="../favicon-32.png" type="image/png" sizes="32x32">
  <link rel="apple-touch-icon" href="../apple-touch-icon.png">
  <style>
    :root {{
      color-scheme: light;
      --bg: #efe6d8;
      --fg: #1c1915;
      --muted: #6f655b;
      --paper: #fbf7f1;
      --line: #e3d5c2;
      --mast: #1a1815;
      --mast-fg: #f8f2e8;
      --gold: #e2b15a;
      --fill: #e3f3f6;
      --ink: #0e3c48;
      --soft: #3d6b76;
      --mark: #0e7490;
      --serif: "Iowan Old Style", Palatino, "Palatino Linotype", "Songti TC", "Noto Serif TC", "PMingLiU", serif;
      --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        color-scheme: dark;
        --bg: #100f0d;
        --fg: #f4efe6;
        --muted: #b7ab9c;
        --paper: #1b1a17;
        --line: #34302a;
        --mast: #070706;
        --mast-fg: #f7f2ea;
        --gold: #e2b15a;
        --fill: #143038;
        --ink: #dff6f8;
        --soft: #a9d4db;
        --mark: #7fd3e4;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: var(--sans);
      line-height: 1.5;
    }}
    .masthead {{ background: var(--mast); color: var(--mast-fg); padding: 2.1rem 1.2rem 1.6rem; }}
    .wrap {{ width: min(40rem, 100%); margin: 0 auto; padding: 0 1.2rem; }}
    .kicker {{ margin: 0 0 0.45rem; color: var(--gold); font-size: 0.74rem; font-weight: 700; letter-spacing: 0.18em; }}
    h1 {{ margin: 0; font-family: var(--serif); font-size: clamp(1.8rem, 6vw, 2.6rem); font-weight: 600; letter-spacing: -0.03em; }}
    .dek {{ margin: 0.7rem 0 0; color: #c9baa6; }}
    .back {{ color: var(--gold); }}
    main {{ padding: 1.25rem 0 3rem; }}
    .gate {{ margin: 0 auto 1.25rem; max-width: 22rem; }}
    .gate[hidden] {{ display: none; }}
    .gate form {{ background: var(--paper); border: 1px solid var(--line); border-radius: 1.35rem; padding: 1.15rem; }}
    .gate h2 {{ margin: 0 0 0.85rem; font-family: var(--serif); font-size: 1.35rem; font-weight: 600; }}
    .gate label {{ display: block; margin-bottom: 0.4rem; font-size: 0.88rem; color: var(--muted); }}
    .gate input {{
      width: 100%; min-height: 2.75rem; padding: 0.55rem 0.75rem;
      border: 1px solid var(--line); border-radius: 0.7rem;
      background: var(--bg); color: var(--fg); font: inherit;
    }}
    .gate button {{
      width: 100%; min-height: 2.75rem; margin-top: 0.7rem; border: 0; border-radius: 999px;
      background: var(--mast); color: var(--mast-fg); font: inherit; font-weight: 700; cursor: pointer;
    }}
    .gate button:disabled {{ opacity: 0.6; cursor: default; }}
    .gate input:focus-visible, .gate button:focus-visible, .links a:focus-visible {{
      outline: 2px solid var(--gold); outline-offset: 2px;
    }}
    .gate-error {{ margin: 0.7rem 0 0; color: #8d2f2f; }}
    @media (prefers-color-scheme: dark) {{ .gate-error {{ color: #f0b4b4; }} }}
    .group {{ margin: 0 0 1.5rem; }}
    .group h2 {{
      margin: 0 0 0.65rem; padding-bottom: 0.35rem;
      border-bottom: 1px solid var(--line);
      font-family: var(--serif); font-size: 1.2rem; font-weight: 600;
    }}
    .links {{ list-style: none; margin: 0; padding: 0; }}
    .links li {{
      background: var(--fill); color: var(--ink); border-radius: 1rem;
      padding: 0.9rem 1rem; margin: 0 0 0.65rem;
    }}
    .links > li > a {{ color: var(--ink); font-weight: 700; text-decoration: none; overflow-wrap: anywhere; }}
    .links > li > a:hover {{ text-decoration: underline; text-underline-offset: 0.18em; }}
    .note {{ margin: 0.4rem 0 0; color: var(--soft); overflow-wrap: anywhere; }}
    .note a {{ color: var(--mark); font-weight: 600; text-underline-offset: 0.15em; }}
  </style>
</head>
<body>
  <header class="masthead">
    <div class="wrap">
      <p class="kicker">省錢</p>
      <h1>{esc(page_title)}</h1>
      <p class="dek">{esc(label)} · {esc(bot)} · <a class="back" href="../index.html">返回總站</a></p>
    </div>
  </header>
  <main>
    <div class="wrap">
      <section id="gate" class="gate">
        <form id="gate-form">
          <h2>輸入密碼</h2>
          <label for="gate-password">密碼</label>
          <input id="gate-password" type="password" name="password" autocomplete="current-password" required>
          <button type="submit">進入</button>
          <p id="gate-error" class="gate-error" hidden>密碼不對</p>
        </form>
      </section>
      <div id="desk" hidden>
        {items_html}
      </div>
    </div>
  </main>
  <script>
    const GATE_SALT = {json.dumps(GATE_SALT)};
    const GATE_ITERATIONS = {GATE_ITERATIONS};
    const GATE_HASH = {json.dumps(GATE_HASH)};
    const GATE_KEY = {json.dumps(GATE_KEY)};
    function gateBytes(b64) {{
      const bin = atob(b64);
      const out = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
      return out;
    }}
    function remembered() {{
      try {{ return localStorage.getItem(GATE_KEY) === GATE_HASH; }}
      catch (error) {{ return false; }}
    }}
    function remember() {{
      try {{ localStorage.setItem(GATE_KEY, GATE_HASH); }}
      catch (error) {{ /* 私密模式就每次再問 */ }}
    }}
    async function passwordMatches(password) {{
      const material = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
      const bits = await crypto.subtle.deriveBits({{
        name: "PBKDF2", salt: gateBytes(GATE_SALT), iterations: GATE_ITERATIONS, hash: "SHA-256"
      }}, material, 256);
      const got = new Uint8Array(bits);
      const expected = gateBytes(GATE_HASH);
      if (got.length !== expected.length) return false;
      let diff = 0;
      for (let i = 0; i < got.length; i += 1) diff |= got[i] ^ expected[i];
      return diff === 0;
    }}
    function openDesk() {{
      document.getElementById("gate").hidden = true;
      document.getElementById("desk").hidden = false;
    }}
    document.getElementById("gate-form").addEventListener("submit", async (event) => {{
      event.preventDefault();
      const input = document.getElementById("gate-password");
      const error = document.getElementById("gate-error");
      const button = event.currentTarget.querySelector("button");
      error.hidden = true;
      button.disabled = true;
      try {{
        const ok = await passwordMatches(input.value);
        if (!ok) {{ error.hidden = false; input.focus(); return; }}
        input.value = "";
        remember();
        openDesk();
      }} catch (gateError) {{
        error.hidden = false;
      }} finally {{
        button.disabled = false;
      }}
    }});
    if (remembered()) openDesk();
  </script>
</body>
</html>
"""
    SAVINGS_DIR.mkdir(parents=True, exist_ok=True)
    (SAVINGS_DIR / f"{day.isoformat()}.html").write_text(page, encoding="utf-8")


def upsert_list(days, day, category, bot, links, title=None):
    page_title = title.strip() if title and str(title).strip() else f"省錢情報（{len(links)} 則）"
    write_savings_page(day, bot, links, page_title)
    upsert(
        days,
        day,
        category,
        bot,
        page_title,
        f"{SAVINGS_PUBLIC}/{day.isoformat()}.html",
    )


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
    if len(parts) < 4:
        raise argparse.ArgumentTypeError("連結須為 section|title|note|href")
    section = parts[0].strip()
    title = parts[1].strip()
    href = parts[-1].strip()
    note = "|".join(parts[2:-1]).strip()
    if not section or not title or not href:
        raise argparse.ArgumentTypeError("連結的 section、title 與 href 不可為空白")
    cleaned = {"section": section, "title": title, "href": href}
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
            raise SystemExit("--links-json 含有缺少 section、title 或 href 的項目")
        links.append(cleaned)
    return links


def build_parser():
    parser = argparse.ArgumentParser(description="新增或更新每日連結總站的一筆連結")
    parser.add_argument("--date", required=True, type=parse_date, help="YYYY-MM-DD")
    parser.add_argument("--category", required=True, choices=CATEGORIES)
    parser.add_argument("--bot", required=True, help="來源 bot 名稱")
    parser.add_argument("--title", help="連結標題")
    parser.add_argument("--href", help="連結網址")
    parser.add_argument(
        "--slot",
        default=None,
        help="同一天、同一類別內一般連結的區分鍵。預設等於 --category，因此不加時行為與以前相同。"
             "例如 AI 爆紅精選用 --category X --slot ai-picks，才不會蓋掉當天的 X 早報／晚間整理。",
    )
    parser.add_argument(
        "--link",
        action="append",
        default=[],
        dest="links",
        type=parse_link_arg,
        help="省錢清單的一筆，格式 section|title|note|href，可重複",
    )
    parser.add_argument("--links-json", help="省錢清單 JSON 檔，內容為 [{section, title, note, href}, ...]")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not str(args.bot).strip():
        parser.error("bot 不可為空白")
    if args.slot is not None and not str(args.slot).strip():
        parser.error("--slot 不可為空白")

    data = load_data()
    days = merge_days(list(data.get("days") or []) + list(data.get("history") or []))
    if args.category == "省錢":
        if args.slot:
            parser.error("--slot 不適用於省錢")
        links = []
        if args.links_json:
            links.extend(load_links_json(args.links_json))
        links.extend(args.links or [])
        if not links:
            parser.error("省錢請用 --link 或 --links-json 提供清單")
        if str(args.href or "").strip():
            parser.error("省錢的網址由產生的頁面決定，不要用 --href")
        upsert_list(days, args.date, args.category, args.bot, links, title=args.title)
    else:
        if args.links or args.links_json:
            parser.error("只有省錢可以使用 --link 或 --links-json")
        if not str(args.title or "").strip() or not str(args.href or "").strip():
            parser.error("bot、title、href 不可為空白")
        upsert(days, args.date, args.category, args.bot, args.title, args.href, slot=args.slot)
    recent, older = partition(days)
    payload = {"days": recent, "history": older}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    DATA_PATH.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
