# 參考：mama-fufood 的開發經驗

來源：2026-11-10，mama-fufood（媽媽記副食品，Flutter + Flask）的 session「新專案規格討論與技術問題」（`local_9cdcae8d-bcd0-4296-805b-50a24f766772`）整理提供。
之後要問 mama-fufood 的事，改找 `local_192a6da1-a514-4ddd-8cfa-55097a52497b`；mama-stocker 找 `local_d52787ce-6eb5-4b1e-ba9d-6ec057a15cb9`。
原始程式：`/Users/darkather/Codebase/mama-fufood`（mama-fufood-app、mama-fufood-backend、mama-fufood-web，各自的 README 有完整設計與架設 SOP）。

---

## 一、檔案放在使用者自己的 Google 雲端硬碟

### 核心原則
使用者的私人資料（紀錄、照片）不上我們的伺服器，只放手機本機＋使用者自己的 Google Drive。後端只存公用資料與意見回饋。寫進隱私權政策，是賣點。

### 兩個 Drive 權限，兩種空間
- `drive.appdata`（App 專用區，使用者看不到）：紀錄同步檔、匯出檔的加密金鑰。
- `drive.file`（只能碰 App 自己建立的檔案）：使用者看得到的「App 名/」資料夾，放匯出檔與「照片/」子資料夾。照片刻意放看得到的地方：手機遺失時照片還在。
- 兩個都不是受限權限，不用做安全評估。**OAuth 同意畫面停在「測試」狀態時，基本資料以外的授權 7 天就失效，自用也要設成正式版。**

### 程式結構（lib/services/drive_store.dart）
- 抽象介面 `CloudStore`（listAppData / readAppData / createAppData / updateAppData / folder / upload / downloadToFile / metadata / findByName / delete），實作 `GoogleDriveStore` 用 googleapis 的 drive v3。
- 測試用記憶體假雲端（`test/services/fake_cloud.dart`，可模擬斷網）；同步測試用兩支假手機共用一個假雲端跑情境。**一開始就這樣設計。**
- 每次呼叫包一層 `_call()`：拿 access token；401 先丟掉 token 重試一次；錯誤分類 network / unauthorized / not_found / storage_full / other 並給看得懂的訊息；一般操作 60 秒逾時，大檔 30 分鐘（沒逾時會讓之後的同步全部排隊）。
- > 5 MB 用 resumable upload；下載串流寫檔，不整份放記憶體。
- 資料夾用路徑找或建，結果快取。
- Drive 查詢的 `name contains` 其實是前綴比對，結果要再自己確認。

### 同步設計（lib/services/sync_engine.dart）
- Drive 沒有條件式更新，兩支手機同時寫同一檔會互蓋 → **每筆紀錄一個檔**（`xxx_rec_{UUID}.json`），衝突縮到「同一筆兩邊都改」。另有清單檔與版本檔 `manifest.json`。
- 每個檔的 `appProperties` 帶 u（最後修改時間）、d（是否刪除）、b（所屬實體），不下載內容就能比對；列表一次就知道誰變了。
- 用 manifest 版本分三種情況：
  - 雲端版本 = 上次同步的版本 → 沒人動過，直接上傳，再讀一次確認。
  - 雲端版本 = 上次「要寫」的版本 → 上次其實已經傳成功。
  - 其他 → 有人動過，逐筆比對，沒衝突自動合併，衝突才問使用者。
- 刪除用 tombstone，不然另一支手機會把它復活。
- 沒成功絕不刪本機；雲端少了檔案也不刪手機上的紀錄。
- 衝突只比內容，不比修改時間（匯入的紀錄會被標成剛修改）。
- 多筆衝突選項：每筆保留較新的 / 以本機覆蓋 / 以雲端覆蓋 / 關閉同步。對話框列出衝突日期。
- 實體怎麼認要早想清楚，匯入和同步用同一套規則（原本同步與匯入規則不同，導致同一實體被判成兩個）。
- 預期外狀況不要自動修（例如自動加「(2)」），停下來、記進診斷記錄、跳對話框讓使用者回報。

### 照片（lib/services/photo_service.dart）
- 一律重新壓成 JPEG（長邊 1280、品質 80），先依方向轉正，再移除 EXIF（含地點）。
- 存在 app support 目錄（不進 Android 自動備份，上限 25 MB，超過整份不備份）。
- 開「照片存到雲端」時上傳到看得到的照片資料夾；上傳後核對 MD5，一致才刪本機那份。
- 別支手機上傳的照片沒有 fileId，就用檔名（`{photoId}.jpg`）在資料夾找，下載到 cache。
- Bug：用 Future 快取避免重複下載時，`whenComplete(() => map.remove(id))` 會回傳 map 裡那個 Future（自己等自己），照片永遠轉圈。要寫成 `{ map.remove(id); }`。

### 匯出加密
- 匯出檔整份加密（含照片）：檔頭（識別字 + JSON：格式版本、金鑰代號…）＋每段 1 MiB 的 AES-256-GCM。nonce = 隨機前綴 + 段落序號；檔頭與「是否最後一段」當附加驗證資料，竄改、調換、截斷都解不開。
- 金鑰一個 Google 帳號一把，存在 appdata；伺服器拿不到、也無法救援。
- 只有 Drive 明確回答「沒有」才建新金鑰；讀取失敗一律當錯誤。兩把並存時都保留，用建立時間最早的；匯入時依檔頭的金鑰代號找。
- 匯出檔名不放個人資訊。
- 匯出檔有格式版本；舊格式只把解密後的 JSON 送後端無狀態轉換（/api/v1/convert）。

### Google 登入與 Drive 授權（最痛的坑，lib/services/auth_service.dart）
- 不靠 Google 靜默／自動登入決定登入狀態。
- 登入那一刻用 Google ID Token 跟後端換**我們自己的通行證**（180 天），連同 sub、email 存在手機上；開 App 直接讀回來，不呼叫靜默登入。
- Drive 權杖用 `GoogleSignInPlatform.instance.clientAuthorizationTokensForScopes`，帶記住的 userId／email：先試不跳畫面；沒權限且使用者按了按鈕才 `promptIfUnauthorized: true`；背景同步一律不跳畫面。
- 驗收必做「重開測試」（見全域 CLAUDE.md 與 google-auth skill）。

---

## 二、後端結構（mama-fufood-backend）

### 技術
- Python 3.15.1（`.python-version`），Flask 3.1 + gunicorn，psycopg 3。
- Neon Postgres（新加坡，和 Render 同區）；Render 免費 web service。
- google-auth + cachecontrol 驗 ID Token（遵守公開金鑰的 Cache-Control）。
- requirements.txt 全釘最新正式版並寫註解；開發一律在 .venv。

### 資料夾
- `app.py`：create_app；`/health`（不碰資料庫，給保活）、`/ready`（檢查資料庫與快取）、統一錯誤處理、CORS。
- `config.py`：環境變數。
- `routes/public.py`（App API）、`routes/admin.py`（後台 API）。
- `auth_utils/`：google_auth.py、app_tokens.py（無狀態通行證）、sessions.py（後台 session）、access.py（管理員檢查）。
- `db/`：connection.py、schema.py（啟動時 ensure_schema，CREATE TABLE IF NOT EXISTS）、各資料表模組。
- `services/`：public_cache.py（記憶體快取）、quota.py（每人每日次數）、payload.py（JSON、gzip、大小上限、防壓縮炸彈）、rejections.py。
- `export_formats/`：每版欄位定義、通用檢查器、`CONVERTERS[N]`（N → N+1），samples/ 每版一份樣本。
- `seed/`、`tools/`（local_db.sh 起本機 Postgres；唯讀帳號讀回饋）、`tests/`（pytest，需 DB 的用 TEST_DATABASE_URL）。

### 資料表
admins、sessions、公用資料表、dataset_releases、app_config（單列：最低 App 版本、強制更新原因、更新網址、公告）、formats、feedback（保留 90 天）。

### App API（全部 POST，Authorization: Bearer，錯誤 `{"error", "code"}`）
1. `/api/v1/session`：Google ID Token 換 App 通行證 `{token, expires_at}`。格式 `prefix1.` + base64url(json{v, sub, email, iat, exp}) + `.` + HMAC，金鑰從 SESSION_SECRET 以用途字串衍生。伺服器不存，180 天到期；發出超過 30 天就在每日檢查回應裡換新。
2. `/api/v1/check`（每日檢查）：送 app_version、**platform（第一版就送）**、datasets；回 min_app_version、force_update、force_reason、update_url、checks_left、各資料集狀態，必要時附新 token。每人每天 10 次（記憶體）。完全不碰資料庫；不存 IP、裝置資訊。
3. `/api/v1/feedback`：回饋＋診斷附件（壓縮 ≤ 1 MiB，解壓 ≤ 4 MiB）；同 UUID 重送回 200 duplicate；每日 3 則；先在記憶體擋嘗試次數；Email 以外個資遮蔽。
4. `/api/v1/convert`：舊格式轉換，無狀態，每日 5 次（失敗還額度）；Render 512 MB → semaphore 一次一份，先讀完內容才搶名額。

### 管理後台（`/admin`，前端是 GitHub Pages 靜態頁）
- `/login`（非管理員 403 且不存任何東西）、`/logout`、`/me`。
- session：40 字亂數 + 24 字 HMAC，簽章錯不碰 DB；滑動有效期；撤銷靠每次檢查白名單（快取 30 秒）。
- 草稿 CRUD（ID 不可改、刪、重用）、`/publish/<dataset>`（先寫 DB，交易成功再重載快取）、`/cache/reload`、`/app-config`、`/formats`、`/feedback`（含依 Email 刪除）、`/admins`。

### 部署踩過的坑（Render）
- gunicorn 單一 worker（`--workers 1 --threads 8`），否則記憶體計數各算各的。
- 不要在 import 階段開執行緒或對外連線；改成第一個請求進來才在 worker 裡開始載入。
- 程式裡直接關掉 `gunicorn.access` logger（Render 會印含 IP 的 access log）。
- `/health` 不碰 DB 給 cron-job.org 保活；`/ready` 才檢查 DB（Neon 閒置 5 分鐘暫停）。
- Render 免費 750 小時是整個 workspace 共用，同 workspace 只能有一個要保持醒著的免費服務。
- 推送前跑上傳檢查（法律 → 安全 → 討論紀錄）；密碼金鑰不進 git。Google client ID 可公開，secret 不行。
