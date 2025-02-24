# 檢查是否是通過權限提升啟動的
param(
    [switch]$Elevated
)

# 設置顏色主題
$Theme = @{
    Primary   = 'Cyan'
    Success   = 'Green'
    Warning   = 'Yellow'
    Error     = 'Red'
    Info      = 'White'
}

# ASCII Logo
$Logo = @"
██████╗ ███████╗███████╗███████╗████████╗    ████████╗ ██████╗  ██████╗ ██╗     
██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝    ╚══██╔══╝██╔═══██╗██╔═══██╗██║     
██████╔╝█████╗  ███████╗█████╗     ██║          ██║   ██║   ██║██║   ██║██║     
██╔══██╗██╔══╝  ╚════██║██╔══╝     ██║          ██║   ██║   ██║██║   ██║██║     
██║  ██║███████╗███████║███████╗   ██║          ██║   ╚██████╔╝╚██████╔╝███████╗
╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝   ╚═╝          ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
"@

# 美化輸出函數
function Write-Styled {
    param (
        [string]$Message,
        [string]$Color = $Theme.Info,
        [string]$Prefix = "",
        [switch]$NoNewline
    )
    $emoji = switch ($Color) {
        $Theme.Success { "✅" }
        $Theme.Error   { "❌" }
        $Theme.Warning { "⚠️" }
        default        { "ℹ️" }
    }
    
    $output = if ($Prefix) { "$emoji $Prefix :: $Message" } else { "$emoji $Message" }
    if ($NoNewline) {
        Write-Host $output -ForegroundColor $Color -NoNewline
    } else {
        Write-Host $output -ForegroundColor $Color
    }
}

# 檢查管理員權限
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-NOT $isAdmin) {
    Write-Styled "需要管理員權限來運行重置工具" -Color $Theme.Warning -Prefix "權限"
    Write-Styled "正在請求管理員權限..." -Color $Theme.Primary -Prefix "提升"
    
    # 顯示操作選項
    Write-Host "`n選擇操作:" -ForegroundColor $Theme.Primary
    Write-Host "1. 請求管理員權限" -ForegroundColor $Theme.Info
    Write-Host "2. 退出程序" -ForegroundColor $Theme.Info
    
    $choice = Read-Host "`n請輸入選項 (1-2)"
    
    if ($choice -ne "1") {
        Write-Styled "操作已取消" -Color $Theme.Warning -Prefix "取消"
        Write-Host "`n按任意鍵退出..." -ForegroundColor $Theme.Info
        $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
        exit
    }
    
    try {
        Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Elevated"
        exit
    }
    catch {
        Write-Styled "無法獲取管理員權限" -Color $Theme.Error -Prefix "錯誤"
        Write-Styled "請以管理員身份運行 PowerShell 後重試" -Color $Theme.Warning -Prefix "提示"
        Write-Host "`n按任意鍵退出..." -ForegroundColor $Theme.Info
        $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
        exit 1
    }
}

# 如果是提升權限後的窗口，等待一下確保窗口可見
if ($Elevated) {
    Start-Sleep -Seconds 1
}

# 顯示 Logo
Write-Host $Logo -ForegroundColor $Theme.Primary
Write-Host "Created by YeongPin`n" -ForegroundColor $Theme.Info

# 設置 TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# 創建臨時目錄
$TmpDir = Join-Path $env:TEMP ([System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null

# 清理函數
function Cleanup {
    if (Test-Path $TmpDir) {
        Remove-Item -Recurse -Force $TmpDir -ErrorAction SilentlyContinue
    }
}

try {
    # 下載地址
    $url = "https://github.com/yeongpin/cursor-free-vip/releases/download/ManualReset/reset_machine_manual.exe"
    $output = Join-Path $TmpDir "reset_machine_manual.exe"

    # 下載文件
    Write-Styled "正在下載重置工具..." -Color $Theme.Primary -Prefix "下載"
    Invoke-WebRequest -Uri $url -OutFile $output
    Write-Styled "下載完成！" -Color $Theme.Success -Prefix "完成"

    # 執行重置工具
    Write-Styled "正在啟動重置工具..." -Color $Theme.Primary -Prefix "執行"
    Start-Process -FilePath $output -Wait
    Write-Styled "重置完成！" -Color $Theme.Success -Prefix "完成"
}
catch {
    Write-Styled "操作失敗" -Color $Theme.Error -Prefix "錯誤"
    Write-Styled $_.Exception.Message -Color $Theme.Error
}
finally {
    Cleanup
    Write-Host "`n按任意鍵退出..." -ForegroundColor $Theme.Info
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
} 