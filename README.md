<div align="center" markdown="1">
   <sup>Special thanks to:</sup>
   <br>
   <br>
   <a href="http://go.warp.dev/cursor-free-vip">
      <img alt="Warp sponsorship" width="400" src="https://github.com/user-attachments/assets/ab8dd143-b0fd-4904-bdc5-dd7ecac94eae">
   </a>

### [Warp, the intelligent terminal for developers](http://go.warp.dev/cursor-free-vip)
[Available for MacOS, Linux, & Windows](http://go.warp.dev/cursor-free-vip)<br>

</div>

---

# ➤ Cursor Free VIP

<div align="center">
<p align="center">
  <img src="./images/logo.png" alt="Cursor Pro Logo" width="200" style="border-radius: 6px;"/>
</p>

<p align="center">

[![Release](https://img.shields.io/endpoint?url=https://api.pinstudios.net/api/badges/release/yeongpin/cursor-free-vip)](https://github.com/yeongpin/cursor-free-vip/releases/latest)
[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC_BY--NC--ND_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Stars](https://img.shields.io/endpoint?url=https://api.pinstudios.net/api/badges/stars/yeongpin/cursor-free-vip)](https://github.com/yeongpin/cursor-free-vip/stargazers)
[![Downloads](https://img.shields.io/endpoint?url=https://api.pinstudios.net/api/badges/downloads/yeongpin/cursor-free-vip/total)](https://github.com/yeongpin/cursor-free-vip/releases/latest)
<a href="https://buymeacoffee.com/yeongpin" target="_blank"><img alt="Buy Me a Coffee" src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support%20Me-FFDA33"></a>
 [<img src="https://devin.ai/assets/deepwiki-badge.png" alt="Ask DeepWiki.com" height="20"/>](https://deepwiki.com/yeongpin/cursor-free-vip)

</p>


<a href="https://trendshift.io/repositories/13425" target="_blank"><img src="https://trendshift.io/api/badge/repositories/13425" alt="yeongpin%2Fcursor-free-vip | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
<br>

<h4>Support Latest 0.49.x Version | 支持最新 0.49.x 版本</h4>

This tool is for educational purposes, currently the repo does not violate any laws. Please support the original project.
This tool will not generate any fake email accounts and OAuth access.

Supports Windows, macOS and Linux.

For optimal performance, run with privileges and always stay up to date.

這是一款用於學習和研究的工具，目前 repo 沒有違反任何法律。請支持原作者。
這款工具不會生成任何假的電子郵件帳戶和 OAuth 訪問。

支持 Windows、macOS 和 Linux。

對於最佳性能，請以管理員身份運行並始終保持最新。


<p align="center">
  <img src="./images/product_2025-04-16_10-40-21.png" alt="new" width="800" style="border-radius: 6px;"/><br>
</p>

</div>

## 🔄 Change Log | 更新日志

[Watch Change Log | 查看更新日志](CHANGELOG.md)

## ✨ Features | 功能特點

* Support Windows macOS and Linux systems<br>支持 Windows、macOS 和 Linux 系統<br>

* Reset Cursor's configuration<br>重置 Cursor 的配置<br>

* Multi-language support (English, 简体中文, 繁體中文, Vietnamese)<br>多語言支持（英文、简体中文、繁體中文、越南語）<br>

## 💻 System Support | 系統支持

| Operating System | Architecture      | Supported |
|------------------|-------------------|-----------|
| Windows          | x64, x86          | ✅         |
| macOS            | Intel, Apple Silicon | ✅      |
| Linux            | x64, x86, ARM64   | ✅         |

## 👀 How to use | 如何使用

<details open>
<summary><b>⭐ Auto Run Script | 腳本自動化運行</b></summary>

### **Linux/macOS**

```bash
curl -fsSL https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/scripts/install.sh -o install.sh && chmod +x install.sh && ./install.sh
```

### **Archlinux** (Removed from aur)

~~Install via [AUR](https://aur.archlinux.org/packages/cursor-free-vip-git)~~

```bash
yay -S cursor-free-vip-git
```

### **Windows**

```powershell
irm https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/scripts/install.ps1 | iex
```

</details>

If you want to stop the script, please press Ctrl+C<br>要停止腳本，請按 Ctrl+C

## ❗ Note | 注意事項

📝 Config | 文件配置
`Win / Macos / Linux Path | 路徑 [Documents/.cursor-free-vip/config.ini]`
<details>
<summary><b>⭐ Config | 文件配置</b></summary>

```
[Chrome]
# Default Google Chrome Path | 默認Google Chrome 遊覽器路徑
chromepath = C:\Program Files\Google/Chrome/Application/chrome.exe

[Turnstile]
# Handle Turnstile Wait Time | 等待人機驗證時間
handle_turnstile_time = 2
# Handle Turnstile Wait Random Time (must merge 1-3 or 1,3) | 等待人機驗證隨機時間（必須是 1-3 或者 1,3 這樣的組合）
handle_turnstile_random_time = 1-3

[OSPaths]
# Storage Path | 存儲路徑
storage_path = /Users/username/Library/Application Support/Cursor/User/globalStorage/storage.json
# SQLite Path | SQLite路徑
sqlite_path = /Users/username/Library/Application Support/Cursor/User/globalStorage/state.vscdb
# Machine ID Path | 機器ID路徑
machine_id_path = /Users/username/Library/Application Support/Cursor/machineId
# For Linux users: ~/.config/cursor/machineid

[Timing]
# Min Random Time | 最小隨機時間
min_random_time = 0.1
# Max Random Time | 最大隨機時間
max_random_time = 0.8
# Page Load Wait | 頁面加載等待時間
page_load_wait = 0.1-0.8
# Input Wait | 輸入等待時間
input_wait = 0.3-0.8
# Submit Wait | 提交等待時間
submit_wait = 0.5-1.5
# Verification Code Input | 驗證碼輸入等待時間
verification_code_input = 0.1-0.3
# Verification Success Wait | 驗證成功等待時間
verification_success_wait = 2-3
# Verification Retry Wait | 驗證重試等待時間
verification_retry_wait = 2-3
# Email Check Initial Wait | 郵件檢查初始等待時間
email_check_initial_wait = 4-6
# Email Refresh Wait | 郵件刷新等待時間
email_refresh_wait = 2-4
# Settings Page Load Wait | 設置頁面加載等待時間
settings_page_load_wait = 1-2
# Failed Retry Time | 失敗重試時間
failed_retry_time = 0.5-1
# Retry Interval | 重試間隔
retry_interval = 8-12
# Max Timeout | 最大超時時間
max_timeout = 160

[Utils]
# Check Update | 檢查更新
check_update = True
# Show Account Info | 顯示賬號信息
show_account_info = True

[TempMailPlus]
# Enable TempMailPlus | 啓用 TempMailPlus（任何轉發到TempMailPlus的郵件都支持獲取驗證碼，例如cloudflare郵件Catch-all）
enabled = false
# TempMailPlus Email | TempMailPlus 電子郵件
email = xxxxx@mailto.plus
# TempMailPlus pin | TempMailPlus pin碼
epin = 

[WindowsPaths]
storage_path = C:\Users\yeongpin\AppData\Roaming\Cursor\User\globalStorage\storage.json
sqlite_path = C:\Users\yeongpin\AppData\Roaming\Cursor\User\globalStorage\state.vscdb
machine_id_path = C:\Users\yeongpin\AppData\Roaming\Cursor\machineId
cursor_path = C:\Users\yeongpin\AppData\Local\Programs\Cursor\resources\app
updater_path = C:\Users\yeongpin\AppData\Local\cursor-updater
update_yml_path = C:\Users\yeongpin\AppData\Local\Programs\Cursor\resources\app-update.yml
product_json_path = C:\Users\yeongpin\AppData\Local\Programs\Cursor\resources\app\product.json

[Browser]
default_browser = opera
chrome_path = C:\Program Files\Google\Chrome\Application\chrome.exe
edge_path = C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
firefox_path = C:\Program Files\Mozilla Firefox\firefox.exe
brave_path = C:\Program Files\BraveSoftware/Brave-Browser/Application/brave.exe
chrome_driver_path = D:\VisualCode\cursor-free-vip-new\drivers\chromedriver.exe
edge_driver_path = D:\VisualCode\cursor-free-vip-new\drivers\msedgedriver.exe
firefox_driver_path = D:\VisualCode\cursor-free-vip-new\drivers\geckodriver.exe
brave_driver_path = D:\VisualCode\cursor-free-vip-new\drivers\chromedriver.exe
opera_path = C:\Users\yeongpin\AppData\Local\Programs\Opera\opera.exe
opera_driver_path = D:\VisualCode\cursor-free-vip-new\drivers\chromedriver.exe

[OAuth]
show_selection_alert = False
timeout = 120
max_attempts = 3
```

</details>

* Use administrator privileges to run the script <br>請使用管理員身份運行腳本

* Confirm that Cursor is closed before running the script <br>請確保在運行腳本前已經關閉 Cursor<br>

* This tool is only for learning and research purposes <br>此工具僅供學習和研究使用<br>

* Please comply with the relevant software usage terms when using this tool <br>使用本工具時請遵守相關軟件使用條款

## 🚨 Common Issues | 常見問題

|                   如果遇到權限問題，請確保：                    |                   此腳本以管理員身份運行                    |
|:--------------------------------------------------:|:------------------------------------------------:|
| If you encounter permission issues, please ensure: | This script is run with administrator privileges |
| Error 'User is not authorized' | This means your account was banned for using temporary (disposal) mail. Ensure using a non-temporary mail service |
## 🤩 Contribution | 貢獻

歡迎提交 Issue 和 Pull Request！


<a href="https://github.com/yeongpin/cursor-free-vip/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=yeongpin/cursor-free-vip&preview=true&max=&columns=" />
</a>
<br /><br />

## 📩 Disclaimer | 免責聲明

本工具僅供學習和研究使用，使用本工具所產生的任何後果由使用者自行承擔。 <br>

This tool is only for learning and research purposes, and any consequences arising from the use of this tool are borne
by the user.

## 💰 Buy Me a Coffee | 請我喝杯咖啡

<div align="center">
  <table>
    <tr>
      <td>
        <img src="./images/provi-code.jpg" alt="buy_me_a_coffee" width="280"/><br>
      </td>
      <td>
        <img src="./images/paypal.png" alt="buy_me_a_coffee" width="280"/><br>
      </td>
    </tr>
  </table>
</div>

## ⭐ Star History | 星星數

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=yeongpin/cursor-free-vip&type=Date)](https://star-history.com/#yeongpin/cursor-free-vip&Date)

</div>

## 📝 License | 授權

本項目採用 [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/) 授權。
Please refer to the [LICENSE](LICENSE.md) file for details.
