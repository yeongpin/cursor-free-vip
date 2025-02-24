<#
.Synopsis
Activate a Python virtual environment for the current PowerShell session.

.Description
Pushes the python executable for a virtual environment to the front of the
$Env:PATH environment variable and sets the prompt to signify that you are
in a Python virtual environment. Makes use of the command line switches as
well as the `pyvenv.cfg` file values present in the virtual environment.

.Parameter VenvDir
Path to the directory that contains the virtual environment to activate. The
default value for this is the parent of the directory that the Activate.ps1
script is located within.

.Parameter Prompt
The prompt prefix to display when this virtual environment is activated. By
default, this prompt is the name of the virtual environment folder (VenvDir)
surrounded by parentheses and followed by a single space (ie. '(.venv) ').

.Example
Activate.ps1
Activates the Python virtual environment that contains the Activate.ps1 script.

.Example
Activate.ps1 -Verbose
Activates the Python virtual environment that contains the Activate.ps1 script,
and shows extra information about the activation as it executes.

.Example
Activate.ps1 -VenvDir C:\Users\MyUser\Common\.venv
Activates the Python virtual environment located in the specified location.

.Example
Activate.ps1 -Prompt "MyPython"
Activates the Python virtual environment that contains the Activate.ps1 script,
and prefixes the current prompt with the specified string (surrounded in
parentheses) while the virtual environment is active.

.Notes
On Windows, it may be required to enable this Activate.ps1 script by setting the
execution policy for the user. You can do this by issuing the following PowerShell
command:

PS C:\> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

For more information on Execution Policies: 
https://go.microsoft.com/fwlink/?LinkID=135170

#>
Param(
    [Parameter(Mandatory = $false)]
    [String]
    $VenvDir,
    [Parameter(Mandatory = $false)]
    [String]
    $Prompt
)

<# Function declarations --------------------------------------------------- #>

<#
.Synopsis
Remove all shell session elements added by the Activate script, including the
addition of the virtual environment's Python executable from the beginning of
the PATH variable.

.Parameter NonDestructive
If present, do not remove this function from the global namespace for the
session.

#>
function global:deactivate ([switch]$NonDestructive) {
    # Revert to original values

    # The prior prompt:
    if (Test-Path -Path Function:_OLD_VIRTUAL_PROMPT) {
        Copy-Item -Path Function:_OLD_VIRTUAL_PROMPT -Destination Function:prompt
        Remove-Item -Path Function:_OLD_VIRTUAL_PROMPT
    }

    # The prior PYTHONHOME:
    if (Test-Path -Path Env:_OLD_VIRTUAL_PYTHONHOME) {
        Copy-Item -Path Env:_OLD_VIRTUAL_PYTHONHOME -Destination Env:PYTHONHOME
        Remove-Item -Path Env:_OLD_VIRTUAL_PYTHONHOME
    }

    # The prior PATH:
    if (Test-Path -Path Env:_OLD_VIRTUAL_PATH) {
        Copy-Item -Path Env:_OLD_VIRTUAL_PATH -Destination Env:PATH
        Remove-Item -Path Env:_OLD_VIRTUAL_PATH
    }

    # Just remove the VIRTUAL_ENV altogether:
    if (Test-Path -Path Env:VIRTUAL_ENV) {
        Remove-Item -Path env:VIRTUAL_ENV
    }

    # Just remove VIRTUAL_ENV_PROMPT altogether.
    if (Test-Path -Path Env:VIRTUAL_ENV_PROMPT) {
        Remove-Item -Path env:VIRTUAL_ENV_PROMPT
    }

    # Just remove the _PYTHON_VENV_PROMPT_PREFIX altogether:
    if (Get-Variable -Name "_PYTHON_VENV_PROMPT_PREFIX" -ErrorAction SilentlyContinue) {
        Remove-Variable -Name _PYTHON_VENV_PROMPT_PREFIX -Scope Global -Force
    }

    # Leave deactivate function in the global namespace if requested:
    if (-not $NonDestructive) {
        Remove-Item -Path function:deactivate
    }
}

<#
.Description
Get-PyVenvConfig parses the values from the pyvenv.cfg file located in the
given folder, and returns them in a map.

For each line in the pyvenv.cfg file, if that line can be parsed into exactly
two strings separated by `=` (with any amount of whitespace surrounding the =)
then it is considered a `key = value` line. The left hand string is the key,
the right hand is the value.

If the value starts with a `'` or a `"` then the first and last character is
stripped from the value before being captured.

.Parameter ConfigDir
Path to the directory that contains the `pyvenv.cfg` file.
#>
function Get-PyVenvConfig(
    [String]
    $ConfigDir
) {
    Write-Verbose "Given ConfigDir=$ConfigDir, obtain values in pyvenv.cfg"

    # Ensure the file exists, and issue a warning if it doesn't (but still allow the function to continue).
    $pyvenvConfigPath = Join-Path -Resolve -Path $ConfigDir -ChildPath 'pyvenv.cfg' -ErrorAction Continue

    # An empty map will be returned if no config file is found.
    $pyvenvConfig = @{ }

    if ($pyvenvConfigPath) {

        Write-Verbose "File exists, parse `key = value` lines"
        $pyvenvConfigContent = Get-Content -Path $pyvenvConfigPath

        $pyvenvConfigContent | ForEach-Object {
            $keyval = $PSItem -split "\s*=\s*", 2
            if ($keyval[0] -and $keyval[1]) {
                $val = $keyval[1]

                # Remove extraneous quotations around a string value.
                if ("'""".Contains($val.Substring(0, 1))) {
                    $val = $val.Substring(1, $val.Length - 2)
                }

                $pyvenvConfig[$keyval[0]] = $val
                Write-Verbose "Adding Key: '$($keyval[0])'='$val'"
            }
        }
    }
    return $pyvenvConfig
}


<# Begin Activate script --------------------------------------------------- #>

# Determine the containing directory of this script
$VenvExecPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvExecDir = Get-Item -Path $VenvExecPath

Write-Verbose "Activation script is located in path: '$VenvExecPath'"
Write-Verbose "VenvExecDir Fullname: '$($VenvExecDir.FullName)"
Write-Verbose "VenvExecDir Name: '$($VenvExecDir.Name)"

# Set values required in priority: CmdLine, ConfigFile, Default
# First, get the location of the virtual environment, it might not be
# VenvExecDir if specified on the command line.
if ($VenvDir) {
    Write-Verbose "VenvDir given as parameter, using '$VenvDir' to determine values"
}
else {
    Write-Verbose "VenvDir not given as a parameter, using parent directory name as VenvDir."
    $VenvDir = $VenvExecDir.Parent.FullName.TrimEnd("\\/")
    Write-Verbose "VenvDir=$VenvDir"
}

# Next, read the `pyvenv.cfg` file to determine any required value such
# as `prompt`.
$pyvenvCfg = Get-PyVenvConfig -ConfigDir $VenvDir

# Next, set the prompt from the command line, or the config file, or
# just use the name of the virtual environment folder.
if ($Prompt) {
    Write-Verbose "Prompt specified as argument, using '$Prompt'"
}
else {
    Write-Verbose "Prompt not specified as argument to script, checking pyvenv.cfg value"
    if ($pyvenvCfg -and $pyvenvCfg['prompt']) {
        Write-Verbose "  Setting based on value in pyvenv.cfg='$($pyvenvCfg['prompt'])'"
        $Prompt = $pyvenvCfg['prompt'];
    }
    else {
        Write-Verbose "  Setting prompt based on parent's directory's name. (Is the directory name passed to venv module when creating the virtual environment)"
        Write-Verbose "  Got leaf-name of $VenvDir='$(Split-Path -Path $venvDir -Leaf)'"
        $Prompt = Split-Path -Path $venvDir -Leaf
    }
}

Write-Verbose "Prompt = '$Prompt'"
Write-Verbose "VenvDir='$VenvDir'"

# Deactivate any currently active virtual environment, but leave the
# deactivate function in place.
deactivate -nondestructive

# Now set the environment variable VIRTUAL_ENV, used by many tools to determine
# that there is an activated venv.
$env:VIRTUAL_ENV = $VenvDir

if (-not $Env:VIRTUAL_ENV_DISABLE_PROMPT) {

    Write-Verbose "Setting prompt to '$Prompt'"

    # Set the prompt to include the env name
    # Make sure _OLD_VIRTUAL_PROMPT is global
    function global:_OLD_VIRTUAL_PROMPT { "" }
    Copy-Item -Path function:prompt -Destination function:_OLD_VIRTUAL_PROMPT
    New-Variable -Name _PYTHON_VENV_PROMPT_PREFIX -Description "Python virtual environment prompt prefix" -Scope Global -Option ReadOnly -Visibility Public -Value $Prompt

    function global:prompt {
        Write-Host -NoNewline -ForegroundColor Green "($_PYTHON_VENV_PROMPT_PREFIX) "
        _OLD_VIRTUAL_PROMPT
    }
    $env:VIRTUAL_ENV_PROMPT = $Prompt
}

# Clear PYTHONHOME
if (Test-Path -Path Env:PYTHONHOME) {
    Copy-Item -Path Env:PYTHONHOME -Destination Env:_OLD_VIRTUAL_PYTHONHOME
    Remove-Item -Path Env:PYTHONHOME
}

# Add the venv to the PATH
Copy-Item -Path Env:PATH -Destination Env:_OLD_VIRTUAL_PATH
$Env:PATH = "$VenvExecDir$([System.IO.Path]::PathSeparator)$Env:PATH"

# SIG # Begin signature block
# MII3ewYJKoZIhvcNAQcCoII3bDCCN2gCAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCBnL745ElCYk8vk
# dBtMuQhLeWJ3ZGfzKW4DHCYzAn+QB6CCG9IwggXMMIIDtKADAgECAhBUmNLR1FsZ
# lUgTecgRwIeZMA0GCSqGSIb3DQEBDAUAMHcxCzAJBgNVBAYTAlVTMR4wHAYDVQQK
# ExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xSDBGBgNVBAMTP01pY3Jvc29mdCBJZGVu
# dGl0eSBWZXJpZmljYXRpb24gUm9vdCBDZXJ0aWZpY2F0ZSBBdXRob3JpdHkgMjAy
# MDAeFw0yMDA0MTYxODM2MTZaFw00NTA0MTYxODQ0NDBaMHcxCzAJBgNVBAYTAlVT
# MR4wHAYDVQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xSDBGBgNVBAMTP01pY3Jv
# c29mdCBJZGVudGl0eSBWZXJpZmljYXRpb24gUm9vdCBDZXJ0aWZpY2F0ZSBBdXRo
# b3JpdHkgMjAyMDCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBALORKgeD
# Bmf9np3gx8C3pOZCBH8Ppttf+9Va10Wg+3cL8IDzpm1aTXlT2KCGhFdFIMeiVPvH
# or+Kx24186IVxC9O40qFlkkN/76Z2BT2vCcH7kKbK/ULkgbk/WkTZaiRcvKYhOuD
# PQ7k13ESSCHLDe32R0m3m/nJxxe2hE//uKya13NnSYXjhr03QNAlhtTetcJtYmrV
# qXi8LW9J+eVsFBT9FMfTZRY33stuvF4pjf1imxUs1gXmuYkyM6Nix9fWUmcIxC70
# ViueC4fM7Ke0pqrrBc0ZV6U6CwQnHJFnni1iLS8evtrAIMsEGcoz+4m+mOJyoHI1
# vnnhnINv5G0Xb5DzPQCGdTiO0OBJmrvb0/gwytVXiGhNctO/bX9x2P29Da6SZEi3
# W295JrXNm5UhhNHvDzI9e1eM80UHTHzgXhgONXaLbZ7LNnSrBfjgc10yVpRnlyUK
# xjU9lJfnwUSLgP3B+PR0GeUw9gb7IVc+BhyLaxWGJ0l7gpPKWeh1R+g/OPTHU3mg
# trTiXFHvvV84wRPmeAyVWi7FQFkozA8kwOy6CXcjmTimthzax7ogttc32H83rwjj
# O3HbbnMbfZlysOSGM1l0tRYAe1BtxoYT2v3EOYI9JACaYNq6lMAFUSw0rFCZE4e7
# swWAsk0wAly4JoNdtGNz764jlU9gKL431VulAgMBAAGjVDBSMA4GA1UdDwEB/wQE
# AwIBhjAPBgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBTIftJqhSobyhmYBAcnz1AQ
# T2ioojAQBgkrBgEEAYI3FQEEAwIBADANBgkqhkiG9w0BAQwFAAOCAgEAr2rd5hnn
# LZRDGU7L6VCVZKUDkQKL4jaAOxWiUsIWGbZqWl10QzD0m/9gdAmxIR6QFm3FJI9c
# Zohj9E/MffISTEAQiwGf2qnIrvKVG8+dBetJPnSgaFvlVixlHIJ+U9pW2UYXeZJF
# xBA2CFIpF8svpvJ+1Gkkih6PsHMNzBxKq7Kq7aeRYwFkIqgyuH4yKLNncy2RtNwx
# AQv3Rwqm8ddK7VZgxCwIo3tAsLx0J1KH1r6I3TeKiW5niB31yV2g/rarOoDXGpc8
# FzYiQR6sTdWD5jw4vU8w6VSp07YEwzJ2YbuwGMUrGLPAgNW3lbBeUU0i/OxYqujY
# lLSlLu2S3ucYfCFX3VVj979tzR/SpncocMfiWzpbCNJbTsgAlrPhgzavhgplXHT2
# 6ux6anSg8Evu75SjrFDyh+3XOjCDyft9V77l4/hByuVkrrOj7FjshZrM77nq81YY
# uVxzmq/FdxeDWds3GhhyVKVB0rYjdaNDmuV3fJZ5t0GNv+zcgKCf0Xd1WF81E+Al
# GmcLfc4l+gcK5GEh2NQc5QfGNpn0ltDGFf5Ozdeui53bFv0ExpK91IjmqaOqu/dk
# ODtfzAzQNb50GQOmxapMomE2gj4d8yu8l13bS3g7LfU772Aj6PXsCyM2la+YZr9T
# 03u4aUoqlmZpxJTG9F9urJh4iIAGXKKy7aIwggb+MIIE5qADAgECAhMzAAE6wJsA
# snAfNTDUAAAAATrAMA0GCSqGSIb3DQEBDAUAMFoxCzAJBgNVBAYTAlVTMR4wHAYD
# VQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xKzApBgNVBAMTIk1pY3Jvc29mdCBJ
# RCBWZXJpZmllZCBDUyBFT0MgQ0EgMDIwHhcNMjQxMjAzMDk0MTAzWhcNMjQxMjA2
# MDk0MTAzWjB8MQswCQYDVQQGEwJVUzEPMA0GA1UECBMGT3JlZ29uMRIwEAYDVQQH
# EwlCZWF2ZXJ0b24xIzAhBgNVBAoTGlB5dGhvbiBTb2Z0d2FyZSBGb3VuZGF0aW9u
# MSMwIQYDVQQDExpQeXRob24gU29mdHdhcmUgRm91bmRhdGlvbjCCAaIwDQYJKoZI
# hvcNAQEBBQADggGPADCCAYoCggGBAOb6O8bNcUcKFE6vSWXiMf3/EALRFfo4QQDq
# m/XTiKG7GeHjRzVGTGhooTagMmKc4m52JNEPsQxCwXYCcTz9bRt/I+CYfHcqIAKL
# Ga46L/7a7T6qFF0tcAX15uMED8xwApWO8GP4wYxGS/a0GD3OGpl2qsZmw0lKFm+f
# rD8ip4F4z6KrnmsVlC0qMdCndPH+2NAstO7k+ArRhqDvsu5Jt39O2M7LuaX6loEp
# 43CWmkr7i+cLlkNbRx5hBrN/8MJQDhnprS2a6y+3PGLNDDUvN9Yb9UMZFwu5xcjM
# AP8VqdQYmgdz7PZDlIncayelUgxG1Zdx6CWqngNOKpc4lkTKzxf3Q8m+awDXCw7L
# 18jWlFL1Jki2khRmU4HhPzKf2WcgQCHtUPekmvnNUeNFT3TZsxXyhXuDTmB+BOV7
# TpUO594HbMIhdktkdZ2mA/mcKPN4NnYJy55pUmwQIOuqPY1dlR+nv2ko466xxd8x
# pUO3R/pAse5WXaNx6fy9jj0ChNuNmQIDAQABo4ICGTCCAhUwDAYDVR0TAQH/BAIw
# ADAOBgNVHQ8BAf8EBAMCB4AwPAYDVR0lBDUwMwYKKwYBBAGCN2EBAAYIKwYBBQUH
# AwMGGysGAQQBgjdhgqKNuwqmkohkgZH0oEWCk/3hbzAdBgNVHQ4EFgQUJrRvpIJJ
# B/SCh4T20kb8yCbcj7MwHwYDVR0jBBgwFoAUZZ9RzoVofy+KRYiq3acxux4NAF4w
# ZwYDVR0fBGAwXjBcoFqgWIZWaHR0cDovL3d3dy5taWNyb3NvZnQuY29tL3BraW9w
# cy9jcmwvTWljcm9zb2Z0JTIwSUQlMjBWZXJpZmllZCUyMENTJTIwRU9DJTIwQ0El
# MjAwMi5jcmwwgaUGCCsGAQUFBwEBBIGYMIGVMGQGCCsGAQUFBzAChlhodHRwOi8v
# d3d3Lm1pY3Jvc29mdC5jb20vcGtpb3BzL2NlcnRzL01pY3Jvc29mdCUyMElEJTIw
# VmVyaWZpZWQlMjBDUyUyMEVPQyUyMENBJTIwMDIuY3J0MC0GCCsGAQUFBzABhiFo
# dHRwOi8vb25lb2NzcC5taWNyb3NvZnQuY29tL29jc3AwZgYDVR0gBF8wXTBRBgwr
# BgEEAYI3TIN9AQEwQTA/BggrBgEFBQcCARYzaHR0cDovL3d3dy5taWNyb3NvZnQu
# Y29tL3BraW9wcy9Eb2NzL1JlcG9zaXRvcnkuaHRtMAgGBmeBDAEEATANBgkqhkiG
# 9w0BAQwFAAOCAgEAvsdWH8gSPoZt5yblw1MghytJmjs6zeME3/iAYXPzcwwXfB08
# RLMesfF0svS4P1GEdP+CcIIqFl7/48ECI4eregPZjypMWhqPQQWuT8+gMDiWRtYj
# KGEhu+faY+U8Bqv/OrRRS6MHNAoJAGH3t/oxeLXTaeW1URtswm+gvEx+K9KFpHP9
# j1mF0wh4wuVvUJAGYc4KpcorLk7P9vQTLCDmFZi08HMcRYQURHEpskWiSS4czpfv
# ImpRPD5RbIqkQnK7M5wX8X+cI/0hCUb0TjIuxBo92FU726ivQ2vqpzuuRo2Uw1wR
# hzerJI2Bilj66tBzPNn02EZt978Ju/f6+N7b0tFD0kSz1DwTYAR3eK9CwRxIXCGf
# 2rrHz/T9ATSlF71xw2g0R5HBPaJKaySj7PXIU5Nq9sEVCuUSJmNmiZRdBkF76LKH
# mg3cCM5QbgpKfnc46Hi6I7D9q8F1XF0IJwRgP/fwDquWnkTHOoWC9nA0+eLedlAh
# oKYQGEKzAdNLdXdWyUNTjnUKhEXLQgPyDPP9ZLHK+jjQwc6ptwPoX3uuSHtrNmnu
# EIFibcHCp6JVIIu5B94xKS99hGXhaxbuaOMyCvTEVmoLMxAWpF1lVyUUTgj9Lr4W
# /qdqUE+7a1QTDLLswxY8djZCJejn0pDLoKoNfjaeIaRKXXrRs2BND+qKDaowggda
# MIIFQqADAgECAhMzAAAABft6XDITYd9dAAAAAAAFMA0GCSqGSIb3DQEBDAUAMGMx
# CzAJBgNVBAYTAlVTMR4wHAYDVQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xNDAy
# BgNVBAMTK01pY3Jvc29mdCBJRCBWZXJpZmllZCBDb2RlIFNpZ25pbmcgUENBIDIw
# MjEwHhcNMjEwNDEzMTczMTUzWhcNMjYwNDEzMTczMTUzWjBaMQswCQYDVQQGEwJV
# UzEeMBwGA1UEChMVTWljcm9zb2Z0IENvcnBvcmF0aW9uMSswKQYDVQQDEyJNaWNy
# b3NvZnQgSUQgVmVyaWZpZWQgQ1MgRU9DIENBIDAyMIICIjANBgkqhkiG9w0BAQEF
# AAOCAg8AMIICCgKCAgEA0hqZfD8ykKTA6CDbWvshmBpDoBf7Lv132RVuSqVwQO3a
# ALLkuRnnTIoRmMGo0fIMQrtwR6UHB06xdqOkAfqB6exubXTHu44+duHUCdE4ngjE
# LBQyluMuSOnHaEdveIbt31OhMEX/4nQkph4+Ah0eR4H2sTRrVKmKrlOoQlhia73Q
# g2dHoitcX1uT1vW3Knpt9Mt76H7ZHbLNspMZLkWBabKMl6BdaWZXYpPGdS+qY80g
# DaNCvFq0d10UMu7xHesIqXpTDT3Q3AeOxSylSTc/74P3og9j3OuemEFauFzL55t1
# MvpadEhQmD8uFMxFv/iZOjwvcdY1zhanVLLyplz13/NzSoU3QjhPdqAGhRIwh/YD
# zo3jCdVJgWQRrW83P3qWFFkxNiME2iO4IuYgj7RwseGwv7I9cxOyaHihKMdT9Neo
# SjpSNzVnKKGcYMtOdMtKFqoV7Cim2m84GmIYZTBorR/Po9iwlasTYKFpGZqdWKyY
# nJO2FV8oMmWkIK1iagLLgEt6ZaR0rk/1jUYssyTiRqWr84Qs3XL/V5KUBEtUEQfQ
# /4RtnI09uFFUIGJZV9mD/xOUksWodGrCQSem6Hy261xMJAHqTqMuDKgwi8xk/mfl
# r7yhXPL73SOULmu1Aqu4I7Gpe6QwNW2TtQBxM3vtSTmdPW6rK5y0gED51RjsyK0C
# AwEAAaOCAg4wggIKMA4GA1UdDwEB/wQEAwIBhjAQBgkrBgEEAYI3FQEEAwIBADAd
# BgNVHQ4EFgQUZZ9RzoVofy+KRYiq3acxux4NAF4wVAYDVR0gBE0wSzBJBgRVHSAA
# MEEwPwYIKwYBBQUHAgEWM2h0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9wa2lvcHMv
# RG9jcy9SZXBvc2l0b3J5Lmh0bTAZBgkrBgEEAYI3FAIEDB4KAFMAdQBiAEMAQTAS
# BgNVHRMBAf8ECDAGAQH/AgEAMB8GA1UdIwQYMBaAFNlBKbAPD2Ns72nX9c0pnqRI
# ajDmMHAGA1UdHwRpMGcwZaBjoGGGX2h0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9w
# a2lvcHMvY3JsL01pY3Jvc29mdCUyMElEJTIwVmVyaWZpZWQlMjBDb2RlJTIwU2ln
# bmluZyUyMFBDQSUyMDIwMjEuY3JsMIGuBggrBgEFBQcBAQSBoTCBnjBtBggrBgEF
# BQcwAoZhaHR0cDovL3d3dy5taWNyb3NvZnQuY29tL3BraW9wcy9jZXJ0cy9NaWNy
# b3NvZnQlMjBJRCUyMFZlcmlmaWVkJTIwQ29kZSUyMFNpZ25pbmclMjBQQ0ElMjAy
# MDIxLmNydDAtBggrBgEFBQcwAYYhaHR0cDovL29uZW9jc3AubWljcm9zb2Z0LmNv
# bS9vY3NwMA0GCSqGSIb3DQEBDAUAA4ICAQBFSWDUd08X4g5HzvVfrB1SiV8pk6XP
# HT9jPkCmvU/uvBzmZRAjYk2gKYR3pXoStRJaJ/lhjC5Dq/2R7P1YRZHCDYyK0zvS
# RMdE6YQtgGjmsdhzD0nCS6hVVcgfmNQscPJ1WHxbvG5EQgYQ0ZED1FN0MOPQzWe1
# zbH5Va0dSxtnodBVRjnyDYEm7sNEcvJHTG3eXzAyd00E5KDCsEl4z5O0mvXqwaH2
# PS0200E6P4WqLwgs/NmUu5+Aa8Lw/2En2VkIW7Pkir4Un1jG6+tj/ehuqgFyUPPC
# h6kbnvk48bisi/zPjAVkj7qErr7fSYICCzJ4s4YUNVVHgdoFn2xbW7ZfBT3QA9zf
# hq9u4ExXbrVD5rxXSTFEUg2gzQq9JHxsdHyMfcCKLFQOXODSzcYeLpCd+r6GcoDB
# ToyPdKccjC6mAq6+/hiMDnpvKUIHpyYEzWUeattyKXtMf+QrJeQ+ny5jBL+xqdOO
# PEz3dg7qn8/oprUrUbGLBv9fWm18fWXdAv1PCtLL/acMLtHoyeSVMKQYqDHb3Qm0
# uQ+NQ0YE4kUxSQa+W/cCzYAI32uN0nb9M4Mr1pj4bJZidNkM4JyYqezohILxYkgH
# bboJQISrQWrm5RYdyhKBpptJ9JJn0Z63LjdnzlOUxjlsAbQir2Wmz/OJE703BbHm
# QZRwzPx1vu7S5zCCB54wggWGoAMCAQICEzMAAAAHh6M0o3uljhwAAAAAAAcwDQYJ
# KoZIhvcNAQEMBQAwdzELMAkGA1UEBhMCVVMxHjAcBgNVBAoTFU1pY3Jvc29mdCBD
# b3Jwb3JhdGlvbjFIMEYGA1UEAxM/TWljcm9zb2Z0IElkZW50aXR5IFZlcmlmaWNh
# dGlvbiBSb290IENlcnRpZmljYXRlIEF1dGhvcml0eSAyMDIwMB4XDTIxMDQwMTIw
# MDUyMFoXDTM2MDQwMTIwMTUyMFowYzELMAkGA1UEBhMCVVMxHjAcBgNVBAoTFU1p
# Y3Jvc29mdCBDb3Jwb3JhdGlvbjE0MDIGA1UEAxMrTWljcm9zb2Z0IElEIFZlcmlm
# aWVkIENvZGUgU2lnbmluZyBQQ0EgMjAyMTCCAiIwDQYJKoZIhvcNAQEBBQADggIP
# ADCCAgoCggIBALLwwK8ZiCji3VR6TElsaQhVCbRS/3pK+MHrJSj3Zxd3KU3rlfL3
# qrZilYKJNqztA9OQacr1AwoNcHbKBLbsQAhBnIB34zxf52bDpIO3NJlfIaTE/xrw
# eLoQ71lzCHkD7A4As1Bs076Iu+mA6cQzsYYH/Cbl1icwQ6C65rU4V9NQhNUwgrx9
# rGQ//h890Q8JdjLLw0nV+ayQ2Fbkd242o9kH82RZsH3HEyqjAB5a8+Ae2nPIPc8s
# ZU6ZE7iRrRZywRmrKDp5+TcmJX9MRff241UaOBs4NmHOyke8oU1TYrkxh+YeHgfW
# o5tTgkoSMoayqoDpHOLJs+qG8Tvh8SnifW2Jj3+ii11TS8/FGngEaNAWrbyfNrC6
# 9oKpRQXY9bGH6jn9NEJv9weFxhTwyvx9OJLXmRGbAUXN1U9nf4lXezky6Uh/cgjk
# Vd6CGUAf0K+Jw+GE/5VpIVbcNr9rNE50Sbmy/4RTCEGvOq3GhjITbCa4crCzTTHg
# YYjHs1NbOc6brH+eKpWLtr+bGecy9CrwQyx7S/BfYJ+ozst7+yZtG2wR461uckFu
# 0t+gCwLdN0A6cFtSRtR8bvxVFyWwTtgMMFRuBa3vmUOTnfKLsLefRaQcVTgRnzeL
# zdpt32cdYKp+dhr2ogc+qM6K4CBI5/j4VFyC4QFeUP2YAidLtvpXRRo3AgMBAAGj
# ggI1MIICMTAOBgNVHQ8BAf8EBAMCAYYwEAYJKwYBBAGCNxUBBAMCAQAwHQYDVR0O
# BBYEFNlBKbAPD2Ns72nX9c0pnqRIajDmMFQGA1UdIARNMEswSQYEVR0gADBBMD8G
# CCsGAQUFBwIBFjNodHRwOi8vd3d3Lm1pY3Jvc29mdC5jb20vcGtpb3BzL0RvY3Mv
# UmVwb3NpdG9yeS5odG0wGQYJKwYBBAGCNxQCBAweCgBTAHUAYgBDAEEwDwYDVR0T
# AQH/BAUwAwEB/zAfBgNVHSMEGDAWgBTIftJqhSobyhmYBAcnz1AQT2ioojCBhAYD
# VR0fBH0wezB5oHegdYZzaHR0cDovL3d3dy5taWNyb3NvZnQuY29tL3BraW9wcy9j
# cmwvTWljcm9zb2Z0JTIwSWRlbnRpdHklMjBWZXJpZmljYXRpb24lMjBSb290JTIw
# Q2VydGlmaWNhdGUlMjBBdXRob3JpdHklMjAyMDIwLmNybDCBwwYIKwYBBQUHAQEE
# gbYwgbMwgYEGCCsGAQUFBzAChnVodHRwOi8vd3d3Lm1pY3Jvc29mdC5jb20vcGtp
# b3BzL2NlcnRzL01pY3Jvc29mdCUyMElkZW50aXR5JTIwVmVyaWZpY2F0aW9uJTIw
# Um9vdCUyMENlcnRpZmljYXRlJTIwQXV0aG9yaXR5JTIwMjAyMC5jcnQwLQYIKwYB
# BQUHMAGGIWh0dHA6Ly9vbmVvY3NwLm1pY3Jvc29mdC5jb20vb2NzcDANBgkqhkiG
# 9w0BAQwFAAOCAgEAfyUqnv7Uq+rdZgrbVyNMul5skONbhls5fccPlmIbzi+OwVdP
# Q4H55v7VOInnmezQEeW4LqK0wja+fBznANbXLB0KrdMCbHQpbLvG6UA/Xv2pfpVI
# E1CRFfNF4XKO8XYEa3oW8oVH+KZHgIQRIwAbyFKQ9iyj4aOWeAzwk+f9E5StNp5T
# 8FG7/VEURIVWArbAzPt9ThVN3w1fAZkF7+YU9kbq1bCR2YD+MtunSQ1Rft6XG7b4
# e0ejRA7mB2IoX5hNh3UEauY0byxNRG+fT2MCEhQl9g2i2fs6VOG19CNep7SquKaB
# jhWmirYyANb0RJSLWjinMLXNOAga10n8i9jqeprzSMU5ODmrMCJE12xS/NWShg/t
# uLjAsKP6SzYZ+1Ry358ZTFcx0FS/mx2vSoU8s8HRvy+rnXqyUJ9HBqS0DErVLjQw
# K8VtsBdekBmdTbQVoCgPCqr+PDPB3xajYnzevs7eidBsM71PINK2BoE2UfMwxCCX
# 3mccFgx6UsQeRSdVVVNSyALQe6PT12418xon2iDGE81OGCreLzDcMAZnrUAx4XQL
# Uz6ZTl65yPUiOh3k7Yww94lDf+8oG2oZmDh5O1Qe38E+M3vhKwmzIeoB1dVLlz4i
# 3IpaDcR+iuGjH2TdaC1ZOmBXiCRKJLj4DT2uhJ04ji+tHD6n58vhavFIrmcxghr/
# MIIa+wIBATBxMFoxCzAJBgNVBAYTAlVTMR4wHAYDVQQKExVNaWNyb3NvZnQgQ29y
# cG9yYXRpb24xKzApBgNVBAMTIk1pY3Jvc29mdCBJRCBWZXJpZmllZCBDUyBFT0Mg
# Q0EgMDICEzMAATrAmwCycB81MNQAAAABOsAwDQYJYIZIAWUDBAIBBQCggcgwGQYJ
# KoZIhvcNAQkDMQwGCisGAQQBgjcCAQQwHAYKKwYBBAGCNwIBCzEOMAwGCisGAQQB
# gjcCARUwLwYJKoZIhvcNAQkEMSIEIGcBno/ti9PCrR9sXrajsTvlHQvGxbk63JiI
# URJByQuGMFwGCisGAQQBgjcCAQwxTjBMoEaARABCAHUAaQBsAHQAOgAgAFIAZQBs
# AGUAYQBzAGUAXwB2ADMALgAxADIALgA4AF8AMgAwADIANAAxADIAMAAzAC4AMAAx
# oQKAADANBgkqhkiG9w0BAQEFAASCAYA12ir0FCUD2IvWiy7MqsqAciOsLhTQmvF0
# /jSGXaCIrGUzlySVKbuQ47XFYcT5xIoz7ChRS/OvrKCJ0eTjFHn7osTLM4BrKZFi
# G0CwUrFom77qPC4XQQY238IGPMiJZCza+PbrXun7tGNqJSH4uCybQMnB1XH3W9qy
# o3Mn89gnba36QesJ8wl5no+HvIS0LnylhzvDcqdO3yI/EC22XJ/f/XENtDIRI+nC
# nwFuo22Ez2ElzjpFtn9kLyA0/Z8Q6SEcboSbpu6daFBgFe6Ztfrs2ga8C4BRgale
# NJJjL9EqnuHQmMC6TctFqw6bMdQi1OhJsKOaPrp3jWY1np+1jI7X+jcrJ0ZYrTpN
# iH5tIgbYarDF6D2HA8Tka5vfKtG7Q2KBOWH9PqJIAjwHCr0XaIQa1NbkAYFmsVMH
# 4MJluljUeMx3Gh9wfCx1R9485sNAFp+Triawf20YtgbTXPw+e0gzjE8vGDBht6i7
# +8Yrqbq00uH3Y+JtjWAis+oi8ZrMPDGhghgUMIIYEAYKKwYBBAGCNwMDATGCGAAw
# ghf8BgkqhkiG9w0BBwKgghftMIIX6QIBAzEPMA0GCWCGSAFlAwQCAQUAMIIBYgYL
# KoZIhvcNAQkQAQSgggFRBIIBTTCCAUkCAQEGCisGAQQBhFkKAwEwMTANBglghkgB
# ZQMEAgEFAAQgZFXp7g3d1kespGffVXL6HjYsxYd3bAR3mRUetFkYstkCBmdEaWXk
# sRgTMjAyNDEyMDMyMDE0MzIuODM2WjAEgAIB9KCB4aSB3jCB2zELMAkGA1UEBhMC
# VVMxEzARBgNVBAgTCldhc2hpbmd0b24xEDAOBgNVBAcTB1JlZG1vbmQxHjAcBgNV
# BAoTFU1pY3Jvc29mdCBDb3Jwb3JhdGlvbjElMCMGA1UECxMcTWljcm9zb2Z0IEFt
# ZXJpY2EgT3BlcmF0aW9uczEnMCUGA1UECxMeblNoaWVsZCBUU1MgRVNOOjc4MDAt
# MDVFMC1EOTQ3MTUwMwYDVQQDEyxNaWNyb3NvZnQgUHVibGljIFJTQSBUaW1lIFN0
# YW1waW5nIEF1dGhvcml0eaCCDyEwggeCMIIFaqADAgECAhMzAAAABeXPD/9mLsmH
# AAAAAAAFMA0GCSqGSIb3DQEBDAUAMHcxCzAJBgNVBAYTAlVTMR4wHAYDVQQKExVN
# aWNyb3NvZnQgQ29ycG9yYXRpb24xSDBGBgNVBAMTP01pY3Jvc29mdCBJZGVudGl0
# eSBWZXJpZmljYXRpb24gUm9vdCBDZXJ0aWZpY2F0ZSBBdXRob3JpdHkgMjAyMDAe
# Fw0yMDExMTkyMDMyMzFaFw0zNTExMTkyMDQyMzFaMGExCzAJBgNVBAYTAlVTMR4w
# HAYDVQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xMjAwBgNVBAMTKU1pY3Jvc29m
# dCBQdWJsaWMgUlNBIFRpbWVzdGFtcGluZyBDQSAyMDIwMIICIjANBgkqhkiG9w0B
# AQEFAAOCAg8AMIICCgKCAgEAnnznUmP94MWfBX1jtQYioxwe1+eXM9ETBb1lRkd3
# kcFdcG9/sqtDlwxKoVIcaqDb+omFio5DHC4RBcbyQHjXCwMk/l3TOYtgoBjxnG/e
# ViS4sOx8y4gSq8Zg49REAf5huXhIkQRKe3Qxs8Sgp02KHAznEa/Ssah8nWo5hJM1
# xznkRsFPu6rfDHeZeG1Wa1wISvlkpOQooTULFm809Z0ZYlQ8Lp7i5F9YciFlyAKw
# n6yjN/kR4fkquUWfGmMopNq/B8U/pdoZkZZQbxNlqJOiBGgCWpx69uKqKhTPVi3g
# VErnc/qi+dR8A2MiAz0kN0nh7SqINGbmw5OIRC0EsZ31WF3Uxp3GgZwetEKxLms7
# 3KG/Z+MkeuaVDQQheangOEMGJ4pQZH55ngI0Tdy1bi69INBV5Kn2HVJo9XxRYR/J
# PGAaM6xGl57Ei95HUw9NV/uC3yFjrhc087qLJQawSC3xzY/EXzsT4I7sDbxOmM2r
# l4uKK6eEpurRduOQ2hTkmG1hSuWYBunFGNv21Kt4N20AKmbeuSnGnsBCd2cjRKG7
# 9+TX+sTehawOoxfeOO/jR7wo3liwkGdzPJYHgnJ54UxbckF914AqHOiEV7xTnD1a
# 69w/UTxwjEugpIPMIIE67SFZ2PMo27xjlLAHWW3l1CEAFjLNHd3EQ79PUr8FUXet
# Xr0CAwEAAaOCAhswggIXMA4GA1UdDwEB/wQEAwIBhjAQBgkrBgEEAYI3FQEEAwIB
# ADAdBgNVHQ4EFgQUa2koOjUvSGNAz3vYr0npPtk92yEwVAYDVR0gBE0wSzBJBgRV
# HSAAMEEwPwYIKwYBBQUHAgEWM2h0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9wa2lv
# cHMvRG9jcy9SZXBvc2l0b3J5Lmh0bTATBgNVHSUEDDAKBggrBgEFBQcDCDAZBgkr
# BgEEAYI3FAIEDB4KAFMAdQBiAEMAQTAPBgNVHRMBAf8EBTADAQH/MB8GA1UdIwQY
# MBaAFMh+0mqFKhvKGZgEByfPUBBPaKiiMIGEBgNVHR8EfTB7MHmgd6B1hnNodHRw
# Oi8vd3d3Lm1pY3Jvc29mdC5jb20vcGtpb3BzL2NybC9NaWNyb3NvZnQlMjBJZGVu
# dGl0eSUyMFZlcmlmaWNhdGlvbiUyMFJvb3QlMjBDZXJ0aWZpY2F0ZSUyMEF1dGhv
# cml0eSUyMDIwMjAuY3JsMIGUBggrBgEFBQcBAQSBhzCBhDCBgQYIKwYBBQUHMAKG
# dWh0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9wa2lvcHMvY2VydHMvTWljcm9zb2Z0
# JTIwSWRlbnRpdHklMjBWZXJpZmljYXRpb24lMjBSb290JTIwQ2VydGlmaWNhdGUl
# MjBBdXRob3JpdHklMjAyMDIwLmNydDANBgkqhkiG9w0BAQwFAAOCAgEAX4h2x35t
# tVoVdedMeGj6TuHYRJklFaW4sTQ5r+k77iB79cSLNe+GzRjv4pVjJviceW6AF6yc
# WoEYR0LYhaa0ozJLU5Yi+LCmcrdovkl53DNt4EXs87KDogYb9eGEndSpZ5ZM74LN
# vVzY0/nPISHz0Xva71QjD4h+8z2XMOZzY7YQ0Psw+etyNZ1CesufU211rLslLKsO
# 8F2aBs2cIo1k+aHOhrw9xw6JCWONNboZ497mwYW5EfN0W3zL5s3ad4Xtm7yFM7Uj
# rhc0aqy3xL7D5FR2J7x9cLWMq7eb0oYioXhqV2tgFqbKHeDick+P8tHYIFovIP7Y
# G4ZkJWag1H91KlELGWi3SLv10o4KGag42pswjybTi4toQcC/irAodDW8HNtX+cbz
# 0sMptFJK+KObAnDFHEsukxD+7jFfEV9Hh/+CSxKRsmnuiovCWIOb+H7DRon9Tlxy
# diFhvu88o0w35JkNbJxTk4MhF/KgaXn0GxdH8elEa2Imq45gaa8D+mTm8LWVydt4
# ytxYP/bqjN49D9NZ81coE6aQWm88TwIf4R4YZbOpMKN0CyejaPNN41LGXHeCUMYm
# Bx3PkP8ADHD1J2Cr/6tjuOOCztfp+o9Nc+ZoIAkpUcA/X2gSMkgHAPUvIdtoSAHE
# UKiBhI6JQivRepyvWcl+JYbYbBh7pmgAXVswggeXMIIFf6ADAgECAhMzAAAAO4pp
# Wb4UBWRxAAAAAAA7MA0GCSqGSIb3DQEBDAUAMGExCzAJBgNVBAYTAlVTMR4wHAYD
# VQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xMjAwBgNVBAMTKU1pY3Jvc29mdCBQ
# dWJsaWMgUlNBIFRpbWVzdGFtcGluZyBDQSAyMDIwMB4XDTI0MDIxNTIwMzYxMloX
# DTI1MDIxNTIwMzYxMlowgdsxCzAJBgNVBAYTAlVTMRMwEQYDVQQIEwpXYXNoaW5n
# dG9uMRAwDgYDVQQHEwdSZWRtb25kMR4wHAYDVQQKExVNaWNyb3NvZnQgQ29ycG9y
# YXRpb24xJTAjBgNVBAsTHE1pY3Jvc29mdCBBbWVyaWNhIE9wZXJhdGlvbnMxJzAl
# BgNVBAsTHm5TaGllbGQgVFNTIEVTTjo3ODAwLTA1RTAtRDk0NzE1MDMGA1UEAxMs
# TWljcm9zb2Z0IFB1YmxpYyBSU0EgVGltZSBTdGFtcGluZyBBdXRob3JpdHkwggIi
# MA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQCoN2tZV70ADgeArSKowvN7sD1W
# j9d2dKDzNsSpQZSD3kwUftP9qC4o/eDvvzx/AzPtJpkW5JpDqYKGIk3NSyyWFlY1
# 2loL6mhkRO8K3lLLgZ9wAr68z+1W0NLs0Bd48QUtLfckAiToekndsqKFP28jZOKB
# U43nW2SiLEL1Wo2JUHFW5Crw16Bkms3b8U9etQKcErNDgTbUnxFbc73Dr47el6pp
# sy6ZMFK7aWzryjKZZfJwS1EmgT2CTQ4XY9qj2Fd9y3gSWNlP+XrGyCiPQ3oQ5cdr
# 9Ms59najNa0WxHbR7B8DPIxXRDxCmdQxHw3HL9N8SC017cvwA4hEuBMfix2gC7xi
# DyM+pTkl28BZ1ANnBznEMZs9rbHtKQpyz2bsNO0RYRP+xrIZtWduvwCWEB6k2H5U
# HSYErMUTm2T4VOQeGsjPRFco+t/5spFqPBsUr/774i4Z+fAfD91D1DFgiK5CVZgg
# k1StKFVDfQSKU5YRXI/TaM4bVocAW3S9rVgpQXCcWI/WJEBxYZn6SJ5dE45VlCwy
# C7HEZvCOrtM02rELlCcXbGdICL3FltPh9A2ZsDw0HA6/7NXF3mhyZ37yQ3sprS/M
# glb5ddY3/KL7nyCfehVuQDjFD2S/h7FCkM1tFFOJnHrn+UHaBsWS/LjyKdBLSK26
# D/C6RPbM6m5MqeJQIwIDAQABo4IByzCCAccwHQYDVR0OBBYEFBmDkSnO3Ykx3QWs
# 933wkNmnHPEVMB8GA1UdIwQYMBaAFGtpKDo1L0hjQM972K9J6T7ZPdshMGwGA1Ud
# HwRlMGMwYaBfoF2GW2h0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9wa2lvcHMvY3Js
# L01pY3Jvc29mdCUyMFB1YmxpYyUyMFJTQSUyMFRpbWVzdGFtcGluZyUyMENBJTIw
# MjAyMC5jcmwweQYIKwYBBQUHAQEEbTBrMGkGCCsGAQUFBzAChl1odHRwOi8vd3d3
# Lm1pY3Jvc29mdC5jb20vcGtpb3BzL2NlcnRzL01pY3Jvc29mdCUyMFB1YmxpYyUy
# MFJTQSUyMFRpbWVzdGFtcGluZyUyMENBJTIwMjAyMC5jcnQwDAYDVR0TAQH/BAIw
# ADAWBgNVHSUBAf8EDDAKBggrBgEFBQcDCDAOBgNVHQ8BAf8EBAMCB4AwZgYDVR0g
# BF8wXTBRBgwrBgEEAYI3TIN9AQEwQTA/BggrBgEFBQcCARYzaHR0cDovL3d3dy5t
# aWNyb3NvZnQuY29tL3BraW9wcy9Eb2NzL1JlcG9zaXRvcnkuaHRtMAgGBmeBDAEE
# AjANBgkqhkiG9w0BAQwFAAOCAgEAKrAu6dFJYu6BKhLMdAxnEMzeKzJOMunyOeCM
# X9VC/meVFudURy3RKZMYUq0YFqQ0BsmfufswGszwfSnqaq116/fomiYokxBDQU/r
# 2u8sXod6NfSaD8/xx/pAFSU28YFYJh46+wdlR30wgf+8uJJMlpZ90fGiZ2crTw0K
# ZJWWSg53MlXTalBP7ZepnoVp9NmcRD9CDw+3IdkjzH1yCnfjbWp0HfBJdv7WJVlc
# nRM45MYqUX1x+5LCeeDnBw2pTj3cDKPNNtNhb8BHRcTJSH84tjVRTtpCtc1XZE5u
# +u0g1tCzLSm7AmR+SZjoClyzinuQuqk/8kx6YRow7Y8wBiZjP5LfriRreaDGpm97
# efzhkwVKcsZsKnw007GhPRQWz52fSgMsRzg6rWx6MRBv3c+kBcefgLVVEI3gguge
# j9NwDXUnmH+DC6ir5NTQ3ZVLhwA2Fjbn+rctcXeozP5g/CS9Qx4C8RpkvyZGvBEB
# DyNFdU9r2HyMvFP/NaUCI0xC7oLde5FONeRFI01itSXk1N7R80JUW7jqRKvy7Ueq
# g6T6PwWfAd/R+vh7oQXhLH98dPJMODz3cdCtw5MeAnfcfUDEE8b6mzJK5iLJbnKY
# IQ+o9T/AcS0A1yCiClaBZBTociaFT5JStvCe7CDzvUWVBY375ezQ+l6M3tTzy63G
# pBDohSMxggdGMIIHQgIBATB4MGExCzAJBgNVBAYTAlVTMR4wHAYDVQQKExVNaWNy
# b3NvZnQgQ29ycG9yYXRpb24xMjAwBgNVBAMTKU1pY3Jvc29mdCBQdWJsaWMgUlNB
# IFRpbWVzdGFtcGluZyBDQSAyMDIwAhMzAAAAO4ppWb4UBWRxAAAAAAA7MA0GCWCG
# SAFlAwQCAQUAoIIEnzARBgsqhkiG9w0BCRACDzECBQAwGgYJKoZIhvcNAQkDMQ0G
# CyqGSIb3DQEJEAEEMBwGCSqGSIb3DQEJBTEPFw0yNDEyMDMyMDE0MzJaMC8GCSqG
# SIb3DQEJBDEiBCBNv25RRNMkG3WBRCPMirWBBK5bDR5n2jrt3NxatbZRRjCBuQYL
# KoZIhvcNAQkQAi8xgakwgaYwgaMwgaAEIJPbJzLEniYkzwpcwDrQSswJJ/yvXnr9
# 1KPiO2/Blq7cMHwwZaRjMGExCzAJBgNVBAYTAlVTMR4wHAYDVQQKExVNaWNyb3Nv
# ZnQgQ29ycG9yYXRpb24xMjAwBgNVBAMTKU1pY3Jvc29mdCBQdWJsaWMgUlNBIFRp
# bWVzdGFtcGluZyBDQSAyMDIwAhMzAAAAO4ppWb4UBWRxAAAAAAA7MIIDYQYLKoZI
# hvcNAQkQAhIxggNQMIIDTKGCA0gwggNEMIICLAIBATCCAQmhgeGkgd4wgdsxCzAJ
# BgNVBAYTAlVTMRMwEQYDVQQIEwpXYXNoaW5ndG9uMRAwDgYDVQQHEwdSZWRtb25k
# MR4wHAYDVQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xJTAjBgNVBAsTHE1pY3Jv
# c29mdCBBbWVyaWNhIE9wZXJhdGlvbnMxJzAlBgNVBAsTHm5TaGllbGQgVFNTIEVT
# Tjo3ODAwLTA1RTAtRDk0NzE1MDMGA1UEAxMsTWljcm9zb2Z0IFB1YmxpYyBSU0Eg
# VGltZSBTdGFtcGluZyBBdXRob3JpdHmiIwoBATAHBgUrDgMCGgMVAClO3IQMdSPc
# u/l/uN44JqTQiG/3oGcwZaRjMGExCzAJBgNVBAYTAlVTMR4wHAYDVQQKExVNaWNy
# b3NvZnQgQ29ycG9yYXRpb24xMjAwBgNVBAMTKU1pY3Jvc29mdCBQdWJsaWMgUlNB
# IFRpbWVzdGFtcGluZyBDQSAyMDIwMA0GCSqGSIb3DQEBCwUAAgUA6vlz6jAiGA8y
# MDI0MTIwMzEyMTEyMloYDzIwMjQxMjA0MTIxMTIyWjB3MD0GCisGAQQBhFkKBAEx
# LzAtMAoCBQDq+XPqAgEAMAoCAQACAiVbAgH/MAcCAQACAhKYMAoCBQDq+sVqAgEA
# MDYGCisGAQQBhFkKBAIxKDAmMAwGCisGAQQBhFkKAwKgCjAIAgEAAgMHoSChCjAI
# AgEAAgMBhqAwDQYJKoZIhvcNAQELBQADggEBALcfsg+u49h09/2fVfz+1Oa0FPvl
# IbwTVUeWlo8UR47kMKA9YMmJ6keO8V0AZFgm2gpw7makh+I1YuB94yqAdmD927Y+
# W/mDiAT8+42WeSa73vAM0vg0ec6fwS03d+R312Cz0qgZ6MfzqmHOQqSpmxX2hMrF
# fGwmZPaAgUwBovI0Hlv5L5Y4hUOF1nP0OOdkJYpqUJNv7Zf/i7cwJ2cUNHdrakld
# W/2arqSCAC9sduzylh2SYCkvrOgAy/AkAHlazB3iaX1KptwZj8yaK6IfXE9nlMy5
# lMpyDoqyU2nBQaqxcJ2tFAnTqT5LNrDan1XtSTXokbRfZ52wUeNv02NIy7cwDQYJ
# KoZIhvcNAQEBBQAEggIAKSKc+LD6QvnR4RvbNgzgxW9+v7RnkF3ymYnzljaCs++W
# zZVRZxTGF1+ploDbpD9MvJiLgOqO5B5ROh2hfs3GtPBsC8vWek4glRhzja9HCTZT
# WBjsqT7zCj/cemZXBr91bImFKawdxy1PL+YeWYQieQ6f+nMRZzL9HT4qqXTuwrHt
# GbG7yUJvau7AT2jynHPZhQTO8vkHHyMbs2CXxO5D/SyDtqpszYJyCAl+V/jgaZZl
# KGN4Vyfh4fLCaTOGSpoAp1qQBICuHcT+3ZdZpUFbr9hyqBCgAGshqNGwEcjrPGc/
# Sisb0AsTjGAJL9bprQ+94InpaRNdKFj2PwNZ3A02+Re8rWAdcH2vQ/NW7fDSD0aE
# MO26CnK7J+XG1HwVjsqivX/4XS5R1MVIMswcbSUiaouTAN33h5m/vsEMFFG46Qv2
# wJYHr/5QzzqrRsMkuDMqECUBrfJXrIQhwiG8paMMv//91XHniJj8vfB8a1EWQLA3
# +xqOcI9WGdLKzMSmalAOu3LE9PaVdeESNA8pp7EzmbgkzgkJ/uL/+c8ZQvxpXx6K
# DA4vpw2utiUATCPB1J8R+TXkLiSoIZUNNPzF3OndLm91Teziwgd9X2sWrfaBJh5r
# 70oKaRn7atZnxen4l5eUcas0WvsgM0Pb55UfhlPZeX1YC1bX2jpoYUblRMc6bCY=
# SIG # End signature block
