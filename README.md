# 每日連結總站

各個 bot 每天交來的連結，整理在同一頁。GitHub Pages 從 `main` 根目錄提供這個網站：<https://penguin-yeh.github.io/link-hub/>

最近 30 天排在上方，一天一區，類別順序為新聞、洞察、X、技術精讀、週末。更早的日期收在摺疊的「歷史」。

## 本機預覽

```bash
python3 -m http.server 8080
```

打開 <http://127.0.0.1:8080/>。

## 新增或更新一筆連結

```bash
python3 scripts/add_link.py \
  --date 2026-11-07 \
  --category 新聞 \
  --bot "每天發生的事" \
  --title "今日新聞統整" \
  --href "https://example.com/news"
```

`--category` 只接受 `新聞`、`洞察`、`X`、`技術精讀`、`週末`。同一天的同一類別會取代舊項目；日期不存在時會補上星期標籤，例如 `2026-11-07（六）`。寫入後 `days` 由新到舊排列，相對最新一天超過 30 天的日期會移進 `history`。
