# set color theme
$Theme = @{
    Primary   = 'Cyan'
    Success   = 'Green'
    Warning   = 'Yellow'
    Error     = 'Red'
    Info      = 'White'
}

# ASCII Logo
$Logo = @"
   ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗      ██████╗ ██████╗  ██████╗   
  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗     ██╔══██╗██╔══██╗██╔═══██╗  
  ██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝     ██████╔╝██████╔╝██║   ██║  
  ██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗     ██╔═══╝ ██╔══██╗██║   ██║  
  ╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║     ██║     ██║  ██║╚██████╔╝  
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝  
"@

# Beautiful Output Function
function Write-Styled {
    param (
        [string]$Message,
        [string]$Color = $Theme.Info,
        [string]$Prefix = "",
        [switch]$NoNewline
    )
    $symbol = switch ($Color) {
        $Theme.Success { "[OK]" }
        $Theme.Error   { "[X]" }
        $Theme.Warning { "[!]" }
        default        { "[*]" }
    }
    
    $output = if ($Prefix) { "$symbol $Prefix :: $Message" } else { "$symbol $Message" }
    if ($NoNewline) {
        Write-Host $output -ForegroundColor $Color -NoNewline
    } else {
        Write-Host $output -ForegroundColor $Color
    }
}

# Get version number function
function Get-LatestVersion {
    try {
        $latestRelease = Invoke-RestMethod -Uri "https://api.github.com/repos/yeongpin/cursor-free-vip/releases/latest"
        return @{
            Version = $latestRelease.tag_name.TrimStart('v')
            Assets = $latestRelease.assets
        }
    } catch {
        Write-Styled $_.Exception.Message -Color $Theme.Error -Prefix "Error"
        throw "Cannot get latest version"
    }
}

# Show Logo
Write-Host $Logo -ForegroundColor $Theme.Primary
$releaseInfo = Get-LatestVersion
$version = $releaseInfo.Version
Write-Host "Version $version" -ForegroundColor $Theme.Info
Write-Host "Created by YeongPin`n" -ForegroundColor $Theme.Info

# Set TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Main installation function
function Install-CursorFreeVIP {
    Write-Styled "Start downloading Cursor Free VIP" -Color $Theme.Primary -Prefix "Download"
    
    try {
        # Get latest version
        Write-Styled "Checking latest version..." -Color $Theme.Primary -Prefix "Update"
        $releaseInfo = Get-LatestVersion
        $version = $releaseInfo.Version
        Write-Styled "Found latest version: $version" -Color $Theme.Success -Prefix "Version"
        
        # Find corresponding resources
        $asset = $releaseInfo.Assets | Where-Object { $_.name -eq "CursorFreeVIP_${version}_windows.exe" }
        if (!$asset) {
            Write-Styled "File not found: CursorFreeVIP_${version}_windows.exe" -Color $Theme.Error -Prefix "Error"
            Write-Styled "Available files:" -Color $Theme.Warning -Prefix "Info"
            $releaseInfo.Assets | ForEach-Object {
                Write-Styled "- $($_.name)" -Color $Theme.Info
            }
            throw "Cannot find target file"
        }
        
        # Check if Downloads folder already exists for the corresponding version
        function Get-DownloadsPath {
            try {
                $shell = New-Object -ComObject Shell.Application
                $downloads = $shell.NameSpace('shell:Downloads')
                if ($downloads -ne $null) {
                    return $downloads.Self.Path
                }
            } catch {}
        
            return "$env:USERPROFILE\Downloads"
        }
        
        $downloadsPath = Get-DownloadsPath
        $savePath = Join-Path $downloadsPath "CursorFreeVIP_$latestVersion`_windows.exe"
        
        if (Test-Path $downloadPath) {
            Write-Styled "Found existing installation file" -Color $Theme.Success -Prefix "Found"
            Write-Styled "Location: $downloadPath" -Color $Theme.Info -Prefix "Location"
            
            # Check if running with administrator privileges
            $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
            
            if (-not $isAdmin) {
                Write-Styled "Requesting administrator privileges..." -Color $Theme.Warning -Prefix "Admin"
                
                # Create new process with administrator privileges
                $startInfo = New-Object System.Diagnostics.ProcessStartInfo
                $startInfo.FileName = $downloadPath
                $startInfo.UseShellExecute = $true
                $startInfo.Verb = "runas"
                
                try {
                    [System.Diagnostics.Process]::Start($startInfo)
                    Write-Styled "Program started with admin privileges" -Color $Theme.Success -Prefix "Launch"
                    return
                }
                catch {
                    Write-Styled "Failed to start with admin privileges. Starting normally..." -Color $Theme.Warning -Prefix "Warning"
                    Start-Process $downloadPath
                    return
                }
            }
            
            # If already running with administrator privileges, start directly
            Start-Process $downloadPath
            return
        }
        
        Write-Styled "No existing installation file found, starting download..." -Color $Theme.Primary -Prefix "Download"

        # Use HttpWebRequest for chunked download with real-time progress bar
        $url = $asset.browser_download_url
        $outputFile = $downloadPath
        Write-Styled "Downloading from: $url" -Color $Theme.Info -Prefix "URL"
        Write-Styled "Saving to: $outputFile" -Color $Theme.Info -Prefix "Path"

        $request = [System.Net.HttpWebRequest]::Create($url)
        $request.UserAgent = "PowerShell Script"
        $response = $request.GetResponse()
        $totalLength = $response.ContentLength
        $responseStream = $response.GetResponseStream()
        $fileStream = [System.IO.File]::OpenWrite($outputFile)
        $buffer = New-Object byte[] 8192
        $bytesRead = 0
        $totalRead = 0
        $lastProgress = -1
        $startTime = Get-Date
        try {
            do {
                $bytesRead = $responseStream.Read($buffer, 0, $buffer.Length)
                if ($bytesRead -gt 0) {
                    $fileStream.Write($buffer, 0, $bytesRead)
                    $totalRead += $bytesRead
                    $progress = [math]::Round(($totalRead / $totalLength) * 100, 1)
                    if ($progress -ne $lastProgress) {
                        $elapsed = (Get-Date) - $startTime
                        $speed = if ($elapsed.TotalSeconds -gt 0) { $totalRead / $elapsed.TotalSeconds } else { 0 }
                        $speedDisplay = if ($speed -gt 1MB) {
                            "{0:N2} MB/s" -f ($speed / 1MB)
                        } elseif ($speed -gt 1KB) {
                            "{0:N2} KB/s" -f ($speed / 1KB)
                        } else {
                            "{0:N2} B/s" -f $speed
                        }
                        $downloadedMB = [math]::Round($totalRead / 1MB, 2)
                        $totalMB = [math]::Round($totalLength / 1MB, 2)
                        Write-Progress -Activity "Downloading CursorFreeVIP" -Status "$downloadedMB MB / $totalMB MB ($progress%) - $speedDisplay" -PercentComplete $progress
                        $lastProgress = $progress
                    }
                }
            } while ($bytesRead -gt 0)
        } finally {
            $fileStream.Close()
            $responseStream.Close()
            $response.Close()
        }
        Write-Progress -Activity "Downloading CursorFreeVIP" -Completed
        # Check file exists and is not zero size
        if (!(Test-Path $outputFile) -or ((Get-Item $outputFile).Length -eq 0)) {
            throw "Download failed or file is empty."
        }
        Write-Styled "Download completed!" -Color $Theme.Success -Prefix "Complete"
        Write-Styled "File location: $outputFile" -Color $Theme.Info -Prefix "Location"
        Write-Styled "Starting program..." -Color $Theme.Primary -Prefix "Launch"
        Start-Process $outputFile
    }
    catch {
        Write-Styled $_.Exception.Message -Color $Theme.Error -Prefix "Error"
        throw
    }
}

# Execute installation
try {
    Install-CursorFreeVIP
}
catch {
    Write-Styled "Download failed" -Color $Theme.Error -Prefix "Error"
    Write-Styled $_.Exception.Message -Color $Theme.Error
}
finally {
    Write-Host "`nPress any key to exit..." -ForegroundColor $Theme.Info
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
}
