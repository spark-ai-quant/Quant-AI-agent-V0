$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$appName = ([string][char]0x7F51) + ([string][char]0x9875)
$launcherPath = Join-Path $root "web_launcher.py"
$innerProjectRoot = Join-Path $root "Quant-AI-agent-main\Quant-AI-agent-main"
$distBase = Join-Path $root "dist"
$distRoot = Join-Path $distBase $appName
$distProjectRoot = Join-Path $distRoot "Quant-AI-agent-main\Quant-AI-agent-main"
$buildRoot = Join-Path $root "build\pyinstaller"
$specRoot = Join-Path $buildRoot "spec"
$requirementsPath = Join-Path $innerProjectRoot "requirements.txt"
$condaLibraryBin = "C:\Users\dingz\anaconda3\Library\bin"
$expatDllPath = "C:\Users\dingz\anaconda3\Library\bin\expat.dll"
$libExpatDllPath = "C:\Users\dingz\anaconda3\Library\bin\libexpat.dll"

function Invoke-Robocopy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    robocopy $Source $Destination /E /XD __pycache__ /XF *.pyc | Out-Null

    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed for $Source -> $Destination with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path $launcherPath)) {
    throw "Launcher not found: $launcherPath"
}

if (-not (Test-Path $innerProjectRoot)) {
    throw "Inner project not found: $innerProjectRoot"
}

python -m pip install -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install runtime requirements."
}

python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install PyInstaller."
}

if (Test-Path $distRoot) {
    Remove-Item $distRoot -Recurse -Force
}

Get-ChildItem $distBase -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.PSIsContainer } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

if (Test-Path $buildRoot) {
    Remove-Item $buildRoot -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $distBase | Out-Null
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $specRoot | Out-Null

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name $appName `
    --distpath $distBase `
    --workpath $buildRoot `
    --specpath $specRoot `
    --collect-all streamlit `
    --collect-all openai `
    --collect-all dotenv `
    --add-binary "$expatDllPath;." `
    --add-binary "$libExpatDllPath;." `
    --exclude-module matplotlib `
    $launcherPath

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

New-Item -ItemType Directory -Force -Path $distProjectRoot | Out-Null

$topLevelFiles = @(
    "generated_strategy.py",
    "main.py",
    "README.md",
    "requirements.txt",
    "streamlit_app.py"
)

foreach ($fileName in $topLevelFiles) {
    $sourcePath = Join-Path $innerProjectRoot $fileName
    if (Test-Path $sourcePath) {
        Copy-Item $sourcePath $distProjectRoot -Force
    }
}

Invoke-Robocopy -Source (Join-Path $innerProjectRoot "agent") -Destination (Join-Path $distProjectRoot "agent")
Invoke-Robocopy -Source (Join-Path $innerProjectRoot "templates") -Destination (Join-Path $distProjectRoot "templates")

robocopy $condaLibraryBin (Join-Path $distRoot "_internal") *.dll /NJH /NJS /NC /NS /NFL | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "Failed to copy Conda runtime DLLs."
}

Write-Host ""
Write-Host "Build completed successfully."
Write-Host "Launch file: $(Join-Path $distRoot ($appName + '.exe'))"
Write-Host "Send the entire folder: $distRoot"
