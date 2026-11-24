# 每日連結總站風格規範：「報社總編桌」

> 給負責修改本 repo 頁面或新增類別的 bot（Grok bot）：**改 `index.html` 之前，先完整讀完這份文件並遵守。**
>
> 這份文件**描述現有設計並把它固定下來**，不是改版。目標是讓日後新增類別、調整版面時風格不會跑掉。連結資料的新增與更新請用 `scripts/add_link.py`，不要手改 `data.json`（見 README）。置頂的「今日提醒」由 Apple 小秘書寫入 `reminders.json`，其他 bot 不要改那個檔，也不要把它加進 `add_link.py` 的類別清單。

## 0. 設計方向

這一頁是各個 bot 交件的「總編桌」：深色報頭（masthead）加上一天一區的紙張卡片，每個類別有自己的一塊顏色。風格是**報社感**：襯線標題、暖米色紙、金色細節；類別靠顏色與圖示一眼分辨。

## 1. 硬性規則

1. 單檔自含：`index.html` 內含 CSS 與 JS。連結資料由同目錄的 `data.json` 載入；置頂的今日提醒由 `reminders.json` 載入。不載外部字型、CSS、CDN。
2. 淺色與深色都要有（`prefers-color-scheme`），每個類別的顏色兩種模式都要定義。
3. 不准：漸層、`box-shadow`、`backdrop-filter`。圓角維持現有大小，不要自己放大。
4. 手機（約 390px）優先，不可橫向捲動。
5. 類別只能出現在 `scripts/add_link.py` 的 `CATEGORIES` 裡；前端清單（`CATEGORIES` 陣列）與它要同步。
6. 外部連結維持純 `<a href rel="noopener noreferrer">`，不加 `target`。

## 2. 整體 token（`:root`）

| 用途 | 淺色 | 深色 |
|---|---|---|
| 背景 `--bg` | `#efe6d8` | `#100f0d` |
| 文字 `--fg` | `#1c1915` | `#f4efe6` |
| 次要文字 `--muted` | `#6f655b` | `#b7ab9c` |
| 紙張 `--paper` | `#fbf7f1` | `#1b1a17` |
| 分隔線 `--line` | `#e3d5c2` | `#34302a` |
| 報頭底 `--mast` | `#1a1815` | `#070706` |
| 報頭字 `--mast-fg` | `#f8f2e8` | `#f7f2ea` |
| 金色 `--gold` | `#e2b15a` | `#e2b15a` |

字型：標題用 `--serif`（Iowan Old Style / Palatino / Songti TC / Noto Serif TC），內文用 `--sans`（系統字型）。

## 3. 類別色

每個類別用一組六個變數，**淺色與深色各一組**，掛在 `.cat-xxx` 上：

```css
.cat-xxx{--fill:…;--ink:…;--soft:…;--mark:…;--mark-ink:…;--hairline:…}
```

- `--fill`：卡片底色；`--ink`：標題文字；`--soft`：次要文字；
- `--mark`：圖示底色與小標記；`--mark-ink`：圖示上的顏色；`--hairline`：卡片內分隔線。

現有類別與主色（淺色 `--mark`）：

| 類別 | class | 主色 |
|---|---|---|
| 新聞 | `cat-news` | 藍 `#1d4f92` |
| 洞察 | `cat-insight` | 琥珀 `#a15c12` |
| X | `cat-x` | 黑白 `#f6f6f6` 反相 |
| 學習 | `cat-learn` | 靛紫 `#5240a8` |
| 記帳 | `cat-expense` | 玫瑰 `#9b2f55` |
| 週末 | `cat-weekend` | 橘 `#d15a2c` |
| 今日提醒（非連結類別，Apple 小秘書） | `cat-remind` | 松綠 `#2f6b45` |

新類別必須選一個**與以上都拉得開的色相**，並維持「淺色底深色字、深色底淺色字」的對比（內文對比至少 4.5:1）。

## 4. 新增類別的完整步驟

缺任何一步都會讓頁面壞掉或顏色不一致：

1. `scripts/add_link.py` 的 `CATEGORIES` 加上名稱（決定每天卡片的順序）。
2. `index.html` 的 `CATEGORIES` 陣列加一筆：`{ name, className: "cat-xxx", icon: "icon-xxx" }`，順序與第 1 步一致。
3. 在淺色區塊加 `.cat-xxx { … }`，並在 `@media (prefers-color-scheme: dark)` 區塊加深色版。
4. 在 SVG sprite 加 `<symbol id="icon-xxx" viewBox="0 0 24 24">`：單色線條、`stroke="currentColor"`、`stroke-width="1.7"`、圓角線頭，與現有圖示一致。
5. README 的類別清單同步。
6. 用 `python3 -m http.server` 開頁面，淺色與深色各截圖檢查一次，並確認手機寬度無橫向捲動。

## 5. 檢查清單

- [ ] 新增或修改的顏色都用 `.cat-*` 的六個變數，沒有直接寫死在元件裡。
- [ ] 淺色與深色都有定義，且文字對比足夠。
- [ ] 圖示是單色線條，風格與其他圖示一致。
- [ ] `add_link.py` 與前端的類別清單、順序一致。
- [ ] 390px 寬度無橫向捲動；頁面沒有載入任何外部資源。

## 6. 常駐看板（`board.html`）

給外接螢幕常駐的輪播看板，沿用本文件的深色 token 與類別色（深色版 `--mark`），規則另外加三條：

1. **一次只放一則**、字要大到兩三公尺外讀得到；標題最多三行、摘要最多五行，超過就截斷，不准縮小字級塞內容。
2. **不需要互動**：不准加必須點擊或捲動才能看到的內容；輪播順序由 `PATTERN` 決定，相鄰兩則不同來源。
3. 新增來源時：在 `SOURCES` 加一筆（名稱、類別色、網址、`loadXxx()` 解析函式）並放進 `PATTERN`；圖片只用該則原有的圖，載入失敗就不顯示。**不要**把 `reminders.json` 或今日提醒加進看板輪播。

## 7. 置頂的今日提醒

解鎖後，`index.html` 在消費儀表板與類別 chips 上方釘一張紙張卡片（沿用 `.day` / `.block` 與 `cat-remind` 松綠色票，勿與 `cat-expense` 的玫瑰衝突），從 `reminders.json` 讀當天的早上／傍晚內容。它不是 `scripts/add_link.py` 的類別，不要把它寫進 `CATEGORIES`。卡片的互動只有「早上／傍晚」切換；日期不是今天時改顯示「今天的提醒還沒更新」。
