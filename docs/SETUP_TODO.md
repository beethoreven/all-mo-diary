# 上線 SOP（使用者要做的外部設定）

（2026-11-11。照 mama-fufood README「上線 SOP」改寫成全心日記版；遇到畫面跟這裡不一樣、或按鈕是灰的，以那份 README 的 Part B～E 說明為準。）

做完每一步，把「交回給 Claude」那一欄的資料貼回來即可。**密碼與連線字串不要貼到聊天**，只貼到它該去的地方。

| 步驟 | 要做的事 | 交回給 Claude |
|---|---|---|
| 1 | 網站上線（GitHub Pages） | 不用 |
| 2 | Google Cloud（登入與雲端硬碟） | 網頁用戶端的 **用戶端 ID** |
| 3 | Neon 資料庫 | 不用（連線字串只貼到 Render） |
| 4 | Render 後端 | 後端的網址 |
| 5 | cron-job.org 保活 | 不用 |

---

## 1. 網站上線（GitHub Pages）

Google 的品牌設定要填三個網址，Google 會實際打開它們，所以網站要先上線。程式已經推上去了。

1. 打開 <https://github.com/beethoreven/all-mo-diary-web/settings/pages>
2. **Build and deployment → Source** 選 **Deploy from a branch**；**Branch** 選 `main`、資料夾 `/ (root)` → **Save**。
3. 等一兩分鐘，同一頁上方出現「Your site is live at …」。

**確認**：下面三個網址都打得開（不是 404）：
- <https://beethoreven.github.io/all-mo-diary-web/>
- <https://beethoreven.github.io/all-mo-diary-web/legal.html?doc=privacy>
- <https://beethoreven.github.io/all-mo-diary-web/legal.html?doc=terms>

## 2. Google Cloud（登入與雲端硬碟）

> 每一步開始前，確認畫面最上方的專案選單是 `all-mo-diary`。

**2-1 建立專案**：<https://console.cloud.google.com/projectcreate> → 專案名稱 `all-mo-diary`（位置「無機構」）→ **建立**。不需要付款帳戶。

**2-2 啟用 Google Drive API**：<https://console.cloud.google.com/apis/library/drive.googleapis.com> → **啟用**。

**2-3 開始使用 Google Auth Platform**：<https://console.cloud.google.com/auth/overview> → **開始使用**：
- 應用程式名稱：`全心日記`
- 使用者支援電子郵件：你的 Email
- 目標對象：**外部**
- 聯絡資訊：你的 Email → 勾選同意 → **建立**

**2-4 品牌**：<https://console.cloud.google.com/auth/branding>

| 欄位 | 值 |
|---|---|
| 應用程式標誌 | **不要上傳**（外部、正式版一上傳就要走品牌驗證） |
| 應用程式首頁 | `https://beethoreven.github.io/all-mo-diary-web/` |
| 應用程式隱私權政策連結 | `https://beethoreven.github.io/all-mo-diary-web/legal.html?doc=privacy` |
| 應用程式服務條款連結 | `https://beethoreven.github.io/all-mo-diary-web/legal.html?doc=terms` |
| 授權網域 | `beethoreven.github.io`（不是 `github.io`） |
| 開發人員聯絡資訊 | 你的 Email |

拉到最下面 **儲存**。

**2-5 資料存取權**：<https://console.cloud.google.com/auth/scopes> → **新增或移除範圍**：
1. 勾選 `openid`、`.../auth/userinfo.email`、`.../auth/userinfo.profile`。
2. 在「手動新增範圍」貼上這兩行 → **新增至表格**：
   ```
   https://www.googleapis.com/auth/drive.appdata
   https://www.googleapis.com/auth/drive.file
   ```
3. 確認五個都勾選 → **更新** → 回到頁面按 **儲存**。（都是非敏感範圍，不用送審。）

**2-6 發布成正式版**：<https://console.cloud.google.com/auth/audience> → 「發布狀態」從**測試中**按 **發布應用程式** → **確認**，變成**正式版**。
- 停在測試中的話，雲端硬碟的授權 7 天就失效，而且只有「測試使用者」登得進來。
- 按鈕是灰的、或要求送審：先不送審，在同一頁 **測試使用者 → 新增使用者** 加入會用的 Google 帳號（mama-fufood README B6 的替代做法）。

**2-7 建立兩個用戶端**：<https://console.cloud.google.com/auth/clients> → **建立用戶端**

① 應用程式類型 **網頁應用程式**
- 名稱：`all-mo-diary-web`
- 已授權的 JavaScript 來源 → 新增兩個：`https://beethoreven.github.io`、`http://localhost:8010`（只有網域、結尾不要斜線）
- 重新導向 URI：不用填
- **建立** → 畫面顯示的 **用戶端 ID（Client ID）交回給 Claude**（不是秘密，會寫進 App 與後端設定）

② 應用程式類型 **Android**
- 套件名稱：`tw.com.tutorarthur.allmodiary`
- SHA-1 憑證指紋（這台 Mac 的除錯金鑰，已經幫你查好）：
  ```
  1A:BC:EE:34:06:13:0E:A6:7C:27:7A:8D:03:B6:4B:B1:FA:F8:40:C2
  ```
- **建立**。Android 用戶端的 ID 不用交回（Google 用套件名稱加 SHA-1 對應）。之後有正式版金鑰時，再建一個正式版 SHA-1 的 Android 用戶端。

## 3. Neon 資料庫

1. <https://console.neon.tech/app/projects> → **New project**

| 欄位 | 值 |
|---|---|
| Project name | `all-mo-diary` |
| Postgres version | **18** |
| Cloud provider | AWS |
| Region | **AWS Asia Pacific 1 (Singapore)**（建好不能改，要和 Render 同區） |

2. 專案首頁 → **Connect** → 打開 **Connection pooling** → 複製連線字串。確認它有 **`-pooler`**、**`ap-southeast-1`**、結尾 **`sslmode=require`**。
3. 這串含密碼：**只貼到第 4 步 Render 的環境變數**。

## 4. Render 後端（router-backend）

**4-1 建 workspace**：<https://dashboard.render.com/> → 左上 workspace 選單 → **New workspace** → 名稱 `router-backend`，方案選免費。
（免費 750 小時是整個 workspace 共用；這個後端要 24 小時醒著，同一個 workspace 不能有別的要醒著的免費服務。開不了新的免費 workspace 時，見 mama-fufood README D2。）

**4-2 建立 Web Service**：確認左上是 `router-backend` → **New → Web Service** → **GitHub** → 選 `router-backend`。
列表裡沒有：按 **Configure GitHub**（或 <https://github.com/settings/installations> → Render → Configure）把 `router-backend` 加進去。

**4-3 設定**：

| 欄位 | 值 |
|---|---|
| Name | `router-backend`（網址會是 `https://router-backend.onrender.com`；被用走就換一個） |
| Language | **Python 3**（讀 repo 的 `.python-version`：3.15.2） |
| Branch | `main` |
| Region | **Singapore** |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn wsgi:app --workers 1 --threads 16 --timeout 120`（**一定要單一 worker**） |
| Instance Type | **Free** |

**4-4 環境變數**（Environment Variables，**名稱一定要有 `DIARY__` 前綴**，沒有前綴後端會拒絕啟動；值前後不要加引號）：

| 名稱 | 值 |
|---|---|
| `DIARY__DATABASE_URL` | 第 3 步的 Neon 連線字串 |
| `DIARY__GOOGLE_CLIENT_ID` | 2-7 ① 的網頁用戶端 ID |
| `DIARY__SESSION_SECRET` | 終端機執行 `python3 -c "import secrets; print(secrets.token_hex(32))"` 產生的亂數 |
| `DIARY__ALLOWED_ORIGINS` | `https://beethoreven.github.io` |
| `DIARY__FIRST_ADMIN_EMAIL` | 第一位管理員的 Google 帳號 Email |

**4-5 Advanced**：Health Check Path 填 `/health`。

**4-6** **Deploy Web Service**，等 2～5 分鐘。

**確認**：
- `https://router-backend.onrender.com/health` 顯示 `"ok": true`
- `https://router-backend.onrender.com/ready` 顯示 `"diary": {"loaded": true, ...}`

**常見問題**：
- 找不到 Python 3.15.2：Render 還沒有這一版。告訴 Claude，改成 Render 有的最新版並寫下原因。
- 啟動失敗、Logs 出現 `ConfigError`：訊息會說是哪個環境變數（例如少了前綴、值前後有引號）。

把後端網址交回給 Claude。

## 5. cron-job.org 保活

1. <https://console.cron-job.org/jobs> → **Create cronjob**
2. URL：`https://router-backend.onrender.com/health`（換成你的網址）；排程：**每 10 分鐘**。
3. **Create**。`/health` 不碰資料庫，不會叫醒 Neon。

---

## 之後才需要

- App 正式版的簽署金鑰（mama-fufood README Part G）：要裝到家人手機前。
- `all-mo-diary-fonts` repo 與它的 GitHub 金鑰：字體功能恢復時。

## 已確認

- 條款與隱私權政策：聯絡人「阿舍老師」、`tutorarthurouat@outlook.com`、「免費提供」都正確（2026-11-11 使用者確認）。
