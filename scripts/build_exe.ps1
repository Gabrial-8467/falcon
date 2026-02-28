param(
    [string]$PythonExe = ".\myenv\Scripts\python.exe",
    [string]$ExeName = "falcon"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found at '$PythonExe'."
}

Write-Host "Installing build dependencies..."
& $PythonExe -m pip install --upgrade pip pyinstaller

Write-Host "Cleaning previous build artifacts..."
if (Test-Path ".\build") { Remove-Item -Recurse -Force ".\build" }
if (Test-Path ".\dist") { Remove-Item -Recurse -Force ".\dist" }
if (Test-Path ".\$ExeName.spec") { Remove-Item -Force ".\$ExeName.spec" }

Write-Host "Building single-file executable..."
& $PythonExe -m PyInstaller `
    --onefile `
    --name $ExeName `
    --paths ".\src" `
    ".\tools\falcon_cli.py"

if (-not (Test-Path ".\dist\$ExeName.exe")) {
    throw "Build failed: .\dist\$ExeName.exe was not created."
}

Write-Host "Done. Executable available at .\dist\$ExeName.exe"
