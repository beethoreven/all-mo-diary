# router-backend 評估（草案，2026-11-10）

狀態：**清單已決定（見最後一節），還沒動工**。

## 目標
把只有使用者自己和太太在用的專案 backend 合併成**一個 Render 服務**，避免免費服務數量與 750 小時額度不夠用。代價是一起掛，使用者接受。

## 和 boo-king-king 的差別
boo-king-king（`local_a0fef359-fdf5-40a1-a007-129841f86d2f` 回覆、`boo-king-king-backend/tenancy.py`）是「同一份程式、多家店」：網址前綴 `/v/<店家>` → ContextVar → 那家店自己的 Neon DB；記憶體狀態一律走 `PerTenant`，有 AST 掃描測試把關。
這裡是「好幾份不同的程式、同一個行程」：每個 app 本來就有自己的模組狀態與 DB，**不需要 tenant_id 欄位，也大多用不到 PerTenant**。

## 架構
```
router-backend/
  app.py           werkzeug DispatcherMiddleware：/diary → apps.diary, /fufood → apps.fufood ...
                   /health（不碰 DB，保活用）、/ready（逐一檢查每個 app）
  apps/<name>/     每個專案一個套件
  requirements.txt、.python-version   全部共用一份
```
- 各專案 meta repo 的 backend submodule 改指向 router-backend；搬程式用 `git subtree` 保留紀錄。
- 每個 app 自己的 DB（自己的連線字串），設定用前綴：`DIARY__DATABASE_URL`、`FUFOOD__GOOGLE_CLIENT_ID`、`FUFOOD__SESSION_SECRET`…

## 必須處理的問題
1. **同名套件撞名**（最大）：各 backend 都有最上層 `db/`、`auth_utils/`、`config.py`、`app.py`；`sys.modules` 全行程共用，第二個 import 會默默拿到第一個的模組。每個 app 改成 `apps.<name>.*`，import 全部改。
2. **環境變數互蓋**：各 app 直接讀 `os.environ["DATABASE_URL"]` 之類。改成每個 app 讀自己前綴的設定。照 boo-king-king：設定寫錯（少設、沒前綴的殘留、值前後有引號、兩個 app 填了同一個 DB）一律讓服務起不來；秘密欄位不印進 log。
3. **版本統一**：Python 3.15.1 / 3.14 / 3.12 → 統一最新版；mama-stocker 的 Flask 3.0.3、gunicorn 23 等一起升。
4. **故障隔離**：每個 app 延遲載入，載入失敗只有該前綴回 503。不要在 import 時開執行緒或對外連線（mama-stocker 的 warm-up 要改）。
5. **共用資源**：單一 worker（記憶體計數），執行緒調多；對外連線都設逾時；DB 連線不用 psycopg_pool（Render 凍結後會卡死），每次開新連線，並設整台與每 app 兩層上限。512 MB 要量 Pillow 等的記憶體。
6. **CORS**：每個 app 只放行自己的前端來源，必填。
7. **已發出的用戶端寫死網址**：mama-fufood App 要發新版；LINE webhook 網址要改；舊服務留到新版裝好。
8. **地區**：Render 與 Neon 要同區（新加坡）；舊 DB 的區域要先查，Neon 區域建好不能改。
9. **Render workspace**：750 instance-hours 按 workspace 算，同 workspace 兩個保活服務會超過，懲罰是整個 workspace 停到下個月。router-backend 單獨一個 workspace，或確認該 workspace 只有它要保持醒著。
10. **部署耦合**：任一 app 改動都重新部署全部；考慮手動部署、部署前跑全部 app 的測試。
11. fireless-war 刻意不保留登入（全域 CLAUDE.md 的例外），合併後保持它自己的行為。

## 專案清單（使用者 2026-11-10 決定）
| 專案 | 決定 | 聯絡 session |
|---|---|---|
| all-mo-diary | 第一個，一開始就在 router-backend | 本專案 |
| mama-fufood | 搬 | `local_192a6da1-a514-4ddd-8cfa-55097a52497b` |
| mama-stocker | 搬（順便升版、拿掉 import 時的執行緒） | `local_d52787ce-6eb5-4b1e-ba9d-6ec057a15cb9` |
| fireless-war | 可以搬（負載極小，原本沒打算搬） | `local_3f9a0d6e-45f6-4d9b-87ac-0d6b03225e4a` |
| zh-cn-to-tw | 最後才搬：目前用量大、不能停機，等其他都穩定再說 | — |
| group-judge | 先不搬（本身用量大） | — |
| boo-king-king | 獨立，不搬 | `local_a0fef359-fdf5-40a1-a007-129841f86d2f` |

順序：all-mo-diary → mama-fufood、mama-stocker、fireless-war（一次一個，舊服務留到確認沒問題才關）→ 最後評估 zh-cn-to-tw。
