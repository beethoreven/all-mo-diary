# router-backend 評估與進度（2026-11-10 起）

狀態：**日記已在 router-backend 上線；共用程式 `shared/` 已建好（2026-11-11），其他專案開始串接**。主掌者是本專案的 session `local_c53463eb-860b-4a84-84b4-3b1e7c827ae9`；改程式的規則在 `router-backend/CLAUDE.md`，加入步驟在 `router-backend/README.md`。

## 目標
把只有使用者自己和太太在用的專案 backend 合併成**一個 Render 服務**，避免免費服務數量與 750 小時額度不夠用。代價是一起掛，使用者接受。

## 和 boo-king-king 的差別
boo-king-king（`local_a0fef359-fdf5-40a1-a007-129841f86d2f` 回覆、`boo-king-king-backend/tenancy.py`）是「同一份程式、多家店」：網址前綴 `/v/<店家>` → ContextVar → 那家店自己的 Neon DB；記憶體狀態一律走 `PerTenant`，有 AST 掃描測試把關。
這裡是「好幾份不同的程式、同一個行程」：每個 app 本來就有自己的模組狀態與 DB，**不需要 tenant_id 欄位，也大多用不到 PerTenant**。

## 架構
```
router-backend/
  app.py           werkzeug DispatcherMiddleware：/all-mo-diary → apps.all_mo_diary, /mama-fufood → apps.mama_fufood ...
                   /health（不碰 DB，保活用）、/ready（逐一檢查每個 app）
  apps/<name>/     每個專案一個套件
  requirements.txt、.python-version   全部共用一份
```
- 各專案 meta repo 的 backend submodule 改指向 router-backend；搬程式用 `git subtree` 保留紀錄。
- 每個 app 自己的 DB（自己的連線字串），設定用前綴：`ALL_MO_DIARY__DATABASE_URL`、`MAMA_FUFOOD__GOOGLE_CLIENT_ID`、`MAMA_FUFOOD__SESSION_SECRET`…

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

順序：all-mo-diary → mama-fufood、mama-stocker、fireless-war → 最後評估 zh-cn-to-tw。

2026-11-11 使用者決定：三個專案**同時搬程式**（各在自己的 `apps/<套件>/`），**切換一次一個**，順序 mama-fufood（要發 App 新版，最花時間）→ mama-stocker → fireless-war；舊服務留到確認沒問題才關。fireless-war 的 demo 路由（不看白名單、任何 Google 帳號可用）**一起搬**，保留它自己的低額度。

## 共用程式（2026-11-11 決定）
使用者要求：API 各專案不同，但跟 API 沒有直接關係的安全機制等，能共用就共用。盤點 all-mo-diary、mama-fufood、mama-stocker、fireless-war 的 backend 之後：

- **共用（`router-backend/shared/`）**：Google ID Token 驗證、App 通行證、管理後台 session／管理員名單／`require_admin`、資料庫連線（每 app 與整台兩層上限）、請求大小與 gzip 上限、每日次數、拒絕統計、公用資料快取、Flask 錯誤格式與 CORS、時間與字數工具。diary 與 mama-fufood 原本是逐行複製的同一份程式，stocker 的連線層也是同一種做法。
- **留在各 app**：只有一個 app 用到的，例如 LINE webhook 簽章、走勢圖網址簽章（mama-stocker）、主持人白名單與 demo 路由（fireless-war）、各 app 的版本號規則。等第二個 app 也要用，再搬進 `shared/`。
- **相容性**：通行證與後台 session 的格式跟原本一模一樣，測試用各 app 原本程式產生的已知值釘住。mama-fufood 搬過來時，只要沿用 `mff1.`、原本的 purpose 字串、`sessions` 表名、`mama-fufood:schema` 鎖名，以及同一個 SESSION_SECRET，手機上的通行證與後台登入就不會失效。
- **順手修掉的**：Google 公鑰抓取原本沿用 google-auth 預設的 120 秒逾時，改成 10 秒。「Google 連不上」原本被當成「憑證無效」（all-mo-diary／mama-fufood 回 401 會把人登出；fireless-war 則反過來，把錯的 issuer 當成「連不上」回 503），現在統一成：無效回 401，連不上回 503，不登出。
- **歸屬**：`shared/` 與 `router/` 只由主掌者改；其他 session 只改自己的 `apps/<套件>/`、`tests/<套件>/`，加 `MOUNTS`／`PER_APP_KEYS`／`requirements.txt` 各一行。

## 2026-11-12 的決定
- **切換改成三個一起切**（取代上面的「一次一個」）：使用者自己做，照一份統一清單（只留本機的 `docs/cutover-checklist.md`）。第一階段同一次做完，第二階段觀察後一起關舊服務、刪舊保活、拿掉舊 submodule。
- **命名**：一律用專案的完整名稱，不縮寫（不能出現 fufood、stocker）。網址前綴與環境變數前綴：all-mo-diary（`/all-mo-diary`、`ALL_MO_DIARY__`，切換當天從 `/diary` 改名）、mama-fufood、mama-stocker、fireless-war。
- **準則**：子專案（backend、app、web，包括 router-backend）的程式、註解、測試、README、commit 訊息只寫程式與技術理由；skill、CLAUDE.md、known-issue 編號、session ID、本機文件參照、討論紀錄、出處、家人都不寫。維護需要的筆記只放各專案的 meta repo。已發給七個專案（含 zh-cn-to-tw、group-judge、boo-king-king）。router-backend 的 CLAUDE.md 已移出 repo 並加進 `.gitignore`。
- **已公開的歷史不改寫**，只保證之後的 commit 符合準則。
- **舊的 backend repo**（mama-fufood-backend、mama-stocker-backend、fireless-war-backend）在第二階段設成私人，舊程式不另外清理。
- **分工**：主掌者確認各專案符合準則後，各專案自己 commit、push；會停機或要使用者動手的事，先回報主掌者，由主掌者整理給使用者。
