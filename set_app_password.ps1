# Sets your WEB APP login password hash in MySQL (not your MySQL root password).
# Requires: MySQL running, backend/.env MYSQL_* correct.
# Usage:  .\set_app_password.ps1
#         (you will be prompted; input is not echoed)

$plain = Read-Host "Enter your Dura Capital app login password" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($plain)
try {
  $env:BOOTSTRAP_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

Set-Location $PSScriptRoot
python .\sync_user_password.py
Remove-Item Env:\BOOTSTRAP_PASSWORD -ErrorAction SilentlyContinue
