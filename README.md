# 每日連結總站

各個 bot 每天交來的連結，整理在同一頁。GitHub Pages 從 `main` 根目錄提供這個網站：<https://penguin-yeh.github.io/link-hub/>

最近 30 天排在上方，一天一區，類別順序為新聞、洞察、X、學習、記帳、週末。更早的日期收在摺疊的「歷史」。

解鎖後，頁面最上方釘一張「今日提醒」卡，資料在 `reminders.json`，由 **Apple 小秘書** 更新（只保留當天，早上／傍晚各一筆）。其他 bot 請不要改這個檔，也不要用 `scripts/add_link.py` 寫入。其下是固定的「消費儀表板」（記帳小幫手）連結，再來才是類別 chips。常駐看板 `board.html` **不會**輪播或顯示今日提醒。

## 本機預覽

```bash
python3 -m http.server 8080
```

打開 <http://127.0.0.1:8080/>。

## 密碼

首頁和看板會先問密碼，通過後把比對用的 hash 記在這台瀏覽器，下次（包含加到 iPhone 主畫面）就不用再輸入。密碼本身不會存下來。這只擋一下隨便點進來的人，`data.json` 和 `reminders.json` 仍然公開、可以直接抓，所以今日提醒在發布前會先淨化敏感內容。

要換成新密碼，用下面這段產生 salt 與 hash，再同時換掉 `index.html` 和 `board.html` 裡的 `GATE_SALT`、`GATE_ITERATIONS`、`GATE_HASH`：

```python
import os, base64, hashlib
password = "新密碼"
salt = os.urandom(16)
digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000, dklen=32)
print("salt_b64 =", base64.b64encode(salt).decode())
print("iterations = 200000")
print("hash_b64 =", base64.b64encode(digest).decode())
```

## 新增或更新一筆連結

```bash
python3 scripts/add_link.py \
  --date 2026-11-07 \
  --category 新聞 \
  --bot "每天發生的事" \
  --title "今日新聞統整" \
  --href "https://example.com/news"
```

`--category` 只接受 `新聞`、`洞察`、`X`、`學習`、`記帳`、`週末`。同一天的同一類別、同一 `--slot` 會取代舊項目；未指定 `--slot` 時，slot 等於類別名稱，因此行為與以前相同（例如晚間的「X 晚間整理」會蓋掉當天的「X 早報」）。日期不存在時會補上星期標籤，例如 `2026-11-07（六）`。寫入後 `days` 由新到舊排列，相對最新一天超過 30 天的日期會移進 `history`。

同一類別若要並存兩筆（例如 X 分類同時放早報／晚間整理和 AI 爆紅精選），加上不同的 `--slot`。自訂 slot 會寫進 `data.json` 的 `slot` 欄位；預設 slot 不會多寫這個欄位。前端會列出同一類別的多筆連結。

```bash
python3 scripts/add_link.py \
  --date 2026-11-25 \
  --category X \
  --slot ai-picks \
  --bot "X Researcher" \
  --title "AI 爆紅精選" \
  --href "https://penguin-yeh.github.io/x-trends/?v=202611251440#ai"
```

這不會蓋掉同一天 `--category X` 且未指定 `--slot` 的「X 早報」或「X 晚間整理」，也不會動到 `--tab` 分頁。同一天重複跑 `--slot ai-picks` 只會更新這一筆。`--slot` 與 `--tab` 不要一起用：`--slot` 是同一類別的另一筆一般連結（title／href）；`--tab` 是 X 底下帶清單的分頁。

X 底下可以有分頁。`--tab` 只用於類別 `X`，同一天的該分頁會整份換掉，不會動到當天的 X 早報或晚間整理；反過來更新早報或晚間也不會清掉分頁。清單用可重複的 `--link '標題|說明|網址'`，或 `--links-json` 指向一個 `[{title, note, href}, ...]` 檔案。

```bash
python3 scripts/add_link.py \
  --date 2026-11-25 \
  --category X \
  --bot "X Free Credits Finder" \
  --tab "AI 免費額度" \
  --link 'Renoise $200 額度抽 2 人|追蹤 @renoiseai 並轉推（官方帳號，AI 影片）|https://x.com/renoiseai/status/2125263159816827176' \
  --link 'Spiral 免費額度|轉推並留言（官方帳號，沒寫額度多少）|https://x.com/spiraldotai/status/2125273409848533178'
```

**修改頁面或新增類別前，請先讀 [STYLE.md](STYLE.md)（「報社總編桌」風格與新增類別步驟）。**

## 今日提醒（Apple 小秘書）

置頂卡從同目錄的 `reminders.json` 載入，不經過 `data.json`。檔案只保留一個日期；若日期不是今天（Asia/Taipei），頁面會顯示一行「今天的提醒還沒更新」。有資料時預設收合，點擊展開；本機預覽可用 `?date=YYYY-MM-DD` 指定要對照的日期。

由 Apple 小秘書在產出每日卡片後執行：

```bash
python3 /workspace/daily-card/publish_linkhub.py /workspace/daily-card/YYYY-MM-DD-today.json morning
python3 /workspace/daily-card/publish_linkhub.py /workspace/daily-card/YYYY-MM-DD-evening.json evening
```

腳本會先淨化敏感內容，覆寫 `reminders.json`，再只 commit / push 這個檔。

## 常駐看板（board.html）

<https://penguin-yeh.github.io/link-hub/board.html> 是給外接螢幕常駐用的看板：不用互動，每 20 秒自動換一則，內容直接從各網站的最新頁面抓（新聞、X、洞察、學習、週末），來源依權重隨機抽（新聞、X 較常出現），相鄰兩則一定不同來源；每個來源內整輪洗牌後才會重複。今日提醒是私人行程，看板不要加入 `reminders.json` 這個來源。

- 參數：`?t=30` 改每則停留秒數；`?src=news,x` 只看部分來源（`news`、`x`、`insight`、`learn`、`weekend`）。
- 每 20 分鐘自動重抓（不用改 board.html，各網站更新後看板自己跟上）；`?dim=1` 可開啟 23:00–07:00 自動調暗（預設關閉）；支援的瀏覽器會阻止螢幕休眠。
- 鍵盤（選用）：`→` 下一則、空白鍵暫停、`F` 全螢幕；點畫面會開啟該則原文。
- 它靠解析各網站的 HTML 取內容，**各網站改版面結構時要同步檢查 `board.html` 裡對應的 `loadXxx()`**。只在同網域（github.io）下運作，本機預覽需把各 repo 放在同一層資料夾一起架站。
