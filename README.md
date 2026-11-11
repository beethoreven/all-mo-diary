# 全心日記（all-mo-diary）

一天一篇的 Android 日記 App。這是 meta repo：規格、工具，以及三個子 repo（git submodule）。

| 路徑 | 內容 |
|---|---|
| `all-mo-diary-app/` | Flutter App（[repo](https://github.com/beethoreven/all-mo-diary-app)） |
| `all-mo-diary-web/` | 網站：首頁、使用者條款、隱私權政策、管理後台 admin.html（[repo](https://github.com/beethoreven/all-mo-diary-web)，GitHub Pages） |
| `router-backend/` | 共用後端，日記掛在 `/diary`（[repo](https://github.com/beethoreven/router-backend)） |
| `docs/SPEC_DRAFT.md` | 規格 |
| `docs/SETUP_TODO.md` | 上線前要做的外部設定（Google Cloud、Neon、Render、字體 repo、第一次登入後台） |
| `docs/router-backend-plan.md` | 共用後端的評估與規劃 |
| `tools/字體瘦身.command` | 字體瘦身工具（雙擊，把字體檔拖進視窗） |
| `tools/sync_texts.sh` | 把 App 的條款、隱私權政策複製到網站 |

取得全部程式：

```bash
git clone --recurse-submodules https://github.com/beethoreven/all-mo-diary.git
```
