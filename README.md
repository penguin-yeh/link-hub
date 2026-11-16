# 每日連結總站

各個 bot 每天交來的連結，整理在同一頁。GitHub Pages 從 `main` 根目錄提供這個網站：<https://penguin-yeh.github.io/link-hub/>

最近 30 天排在上方，一天一區，類別順序為新聞、洞察、X、技術精讀、學習、週末。更早的日期收在摺疊的「歷史」。

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

`--category` 只接受 `新聞`、`洞察`、`X`、`技術精讀`、`學習`、`週末`。同一天的同一類別會取代舊項目；日期不存在時會補上星期標籤，例如 `2026-11-07（六）`。寫入後 `days` 由新到舊排列，相對最新一天超過 30 天的日期會移進 `history`。

**修改頁面或新增類別前，請先讀 [STYLE.md](STYLE.md)（「報社總編桌」風格與新增類別步驟）。**

## 常駐看板（board.html）

<https://penguin-yeh.github.io/link-hub/board.html> 是給外接螢幕常駐用的看板：不用互動，每 20 秒自動換一則，內容直接從各網站的最新頁面抓（新聞、X、洞察、學習、週末），相鄰兩則一定來自不同來源。

- 參數：`?t=30` 改每則停留秒數；`?src=news,x` 只看部分來源（`news`、`x`、`insight`、`learn`、`weekend`）。
- 每 20 分鐘自動重抓；23:00–07:00 自動調暗；支援的瀏覽器會阻止螢幕休眠。
- 鍵盤（選用）：`→` 下一則、空白鍵暫停、`F` 全螢幕；點畫面會開啟該則原文。
- 它靠解析各網站的 HTML 取內容，**各網站改版面結構時要同步檢查 `board.html` 裡對應的 `loadXxx()`**。只在同網域（github.io）下運作，本機預覽需把各 repo 放在同一層資料夾一起架站。
