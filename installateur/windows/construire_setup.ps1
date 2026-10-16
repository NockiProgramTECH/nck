# Construit NCK-Setup-<version>.exe sous Windows : trouve (ou installe) Inno Setup, puis compile nck.iss.
#   powershell -ExecutionPolicy Bypass -File installateur\windows\construire_setup.ps1
# Options : -SansExe (ne pas relancer PyInstaller si dist\nck\nck.exe existe déjà)
param([switch]$SansExe)
$ErrorActionPreference = "Stop"
$Racine = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Racine

# 1. L'exécutable nck.exe
if (-not $SansExe -or -not (Test-Path "dist\nck\nck.exe")) {
  Write-Host "-> Construction de dist\nck\nck.exe (PyInstaller)..."
  python -m PyInstaller --version 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { python -m pip install pyinstaller }
  python installateur\construire.py
  if ($LASTEXITCODE -ne 0) { throw "La construction de l'exécutable a échoué." }
}

# 2. Trouver ISCC.exe (Inno Setup)
function Trouver-ISCC {
  $candidats = @(
    (Get-Command iscc.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
  )
  foreach ($c in $candidats) { if ($c -and (Test-Path $c)) { return $c } }
  return $null
}
$iscc = Trouver-ISCC
if (-not $iscc) {
  Write-Host "Inno Setup n'est pas installé. Installation avec winget..."
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
    $iscc = Trouver-ISCC
  }
  if (-not $iscc) {
    throw "Installez Inno Setup 6 depuis https://jrsoftware.org/isdl.php puis relancez ce script."
  }
}
Write-Host "-> Inno Setup : $iscc"

# 3. Compiler
$version = python -c "import nck; print(nck.__version__)"
& $iscc "/DVersion=$version" "installateur\windows\nck.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC a échoué (code $LASTEXITCODE)." }
Write-Host ""
Write-Host "OK - dist\NCK-Setup-$version.exe"
