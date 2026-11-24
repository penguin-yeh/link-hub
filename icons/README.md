# 各站 icon

這裡是總站以外、這次沒有寫入權的 8 個站。每個資料夾放到該 repo 根目錄（檔名不要改）。`apple-touch-icon.png` 是 180、不透明。

每個 HTML 的 `<head>` 接上（已有舊的 icon 連結就換掉）：

```html
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="apple-touch-icon.png" sizes="180x180">
<link rel="manifest" href="site.webmanifest">
```

`weekend-fun` 還要刪掉原來那行企鵝 data-uri icon。`learning-daily` 的 `scripts/render_email.py` 產生頁面時，`<head>` 裡的 `<title>` 後面也要加上面四行，不然下一期會把 icon 弄掉。

| 資料夾 | 圖案 | 主色 |
|---|---|---|
| daily-news | 報紙 | `#1E4D8C` |
| daily-insights | 燈泡 | `#E6B325` |
| x-trends | 三根上升長條（不是 X 標誌） | `#242428` |
| learning-daily | 打開的書 | `#5B3A9E` |
| csapp-ddia-study | 新芽 | `#1F7A4D` |
| weekend-fun | 地圖針 | `#E25B2A` |
| expense-dashboard | 帳本 | `#9B2F55` |
| savings | 撑滿的小豬 | `#0E7490` |

總站自己的圖示是鏈結，主色 `#7A5A32`，已經放在 repo 根目錄。類別 chips 的「學習」連到 csapp-ddia-study，所以 chip 用新芽，不是這本打開的書。
