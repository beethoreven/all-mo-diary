# 上線前要由使用者完成的設定

（2026-11-11 整理。照 mama-fufood README「上線 SOP」Part A～D 改寫成全心日記版；細節與截圖說明以那份為準。）

登入、雲端同步、匯入/匯出、意見回饋、字體清單都需要下面這些外部設定。程式可以先寫、先用假的雲端測試，但要在手機上真的跑起來，必須先完成這些步驟。

## 0. GitHub repo（Claude 可以代做，需要你同意）

| repo | 公開／私人 | 用途 |
|---|---|---|
| `all-mo-diary` | 待定 | meta repo（規格、工具、submodule） |
| `all-mo-diary-app` | 待定 | Flutter App |
| `all-mo-diary-web` | **公開**（免費的 GitHub Pages 需要） | 首頁、使用者條款、隱私權政策、管理後台 |
| `router-backend` | 待定（Render 讀得到即可） | 共用後端 |
| `all-mo-diary-fonts` | **公開**（App 直接下載） | 字體檔放在 Release（字體功能暫停中） |

Google 的品牌設定（下一步）要填三個**打得開**的網址，所以 `all-mo-diary-web` 要先上線：
- `https://beethoreven.github.io/all-mo-diary-web/`
- `https://beethoreven.github.io/all-mo-diary-web/legal.html?doc=privacy`
- `https://beethoreven.github.io/all-mo-diary-web/legal.html?doc=terms`

## 1. Google Cloud（登入與雲端硬碟）

建議開一個**新專案**（同意畫面上顯示的 App 名稱跟著專案走）。

1. <https://console.cloud.google.com/> → 新增專案 `all-mo-diary`。
2. API 和服務 → 程式庫 → 啟用 **Google Drive API**。
3. Google Auth Platform → 開始使用：App 名稱 `全心日記`、目標對象**外部**。
4. **品牌**：首頁、隱私權政策、服務條款填上面三個網址；授權網域 `beethoreven.github.io`；**不要上傳標誌**（會觸發品牌驗證）。
5. **資料存取權**：`openid`、`userinfo.email`、`userinfo.profile`，手動加 `https://www.googleapis.com/auth/drive.appdata`、`https://www.googleapis.com/auth/drive.file`。都是非敏感範圍，不用送審。
6. **目標對象 → 發布應用程式**（正式版）。停在「測試中」的話，雲端硬碟授權 7 天就失效。按鈕是灰的：照 mama-fufood README B6 的替代做法（維持測試中、加測試使用者）。
7. **用戶端 → 建立用戶端**：
   - **網頁應用程式** `all-mo-diary-web`：已授權的 JavaScript 來源 `https://beethoreven.github.io`、`http://localhost:8010`。建立後**把用戶端 ID 給 Claude**（這個 ID 不是秘密，會寫進 App 與後端設定）。
   - **Android**：套件名稱 `tw.com.tutorarthur.allmodiary`，SHA-1 用除錯金鑰的（指令見 mama-fufood README B7）。之後有正式版金鑰時再加一個正式版的 SHA-1。

## 2. Neon 資料庫

- 新專案 `all-mo-diary`，Postgres 18，區域 **AWS Asia Pacific 1 (Singapore)**（建好不能改，要和 Render 同區）。
- 複製 **Connection pooling** 的連線字串（主機名有 `-pooler`、`ap-southeast-1`、結尾 `sslmode=require`）。**只貼到 Render 的環境變數**，不要貼到聊天或 git。
- 存放：意見回饋、管理員、App 設定（最低版本）、字體清單。日記內容不會進資料庫。

## 3. Render（router-backend）

- 依 `router-backend-plan.md`：router-backend **自己一個 workspace**（750 小時是整個 workspace 共用）。
- New → Web Service → `router-backend`，Region **Singapore**，Language Python 3（讀 `.python-version`，3.15.2；Render 沒有這版就改成它有的最新版並寫下原因）。
- Build：`pip install -r requirements.txt`；Start：`gunicorn wsgi:app --workers 1 --threads 16 --timeout 120`；Health Check Path：`/health`。
- 環境變數（全部帶 `DIARY__` 前綴，沒有前綴的服務會拒絕啟動）：

| 名稱 | 值 |
|---|---|
| `DIARY__DATABASE_URL` | Neon 連線字串 |
| `DIARY__GOOGLE_CLIENT_ID` | 網頁應用程式的用戶端 ID |
| `DIARY__SESSION_SECRET` | `python3 -c "import secrets; print(secrets.token_hex(32))"` 產生 |
| `DIARY__ALLOWED_ORIGINS` | `https://beethoreven.github.io` |
| `DIARY__FIRST_ADMIN_EMAIL` | 第一位管理員的 Google 帳號 |

- 保活：cron-job.org 每 10 分鐘打 `/health`（不碰資料庫）。

## 4. 之後才需要

- App 正式版簽署金鑰（mama-fufood README Part G）：要裝到家人手機前。
- 字體 repo 的 GitHub 金鑰（只對 `all-mo-diary-fonts` 有寫入權）：字體功能恢復時。

## 請確認

- 條款與隱私權政策裡的「阿舍老師」與 `tutorarthurouat@outlook.com` 是否沿用 mama-fufood 的。
- 條款寫「免費提供」是否正確。
