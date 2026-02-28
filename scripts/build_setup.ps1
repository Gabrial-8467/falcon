param(
    [string]$PythonExe = ".\myenv\Scripts\python.exe",
    [string]$InnoCompiler = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $InnoCompiler)) {
    throw "Inno Setup compiler not found at '$InnoCompiler'. Install Inno Setup 6 and retry."
}

Write-Host "Step 1/2: Building falcon.exe..."
& ".\scripts\build_exe.ps1" -PythonExe $PythonExe -ExeName "falcon"

Write-Host "Step 2/2: Building installer (falcon-setup-x64.exe)..."
& $InnoCompiler ".\installer\falcon.iss"

if (-not (Test-Path ".\dist\falcon-setup-x64.exe")) {
    throw "Setup build failed: .\dist\falcon-setup-x64.exe was not created."
}

Write-Host "Done. Installer available at .\dist\falcon-setup-x64.exe"
