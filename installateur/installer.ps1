# Installateur NCK pour Windows (sans assistant graphique) — aucun Python requis.
#   irm https://raw.githubusercontent.com/NockiProgramTECH/nck/main/installateur/installer.ps1 | iex
# Variables : $env:NCK_VERSION (défaut : dernière), $env:NCK_PREFIX (défaut : %LOCALAPPDATA%\NCK)
$ErrorActionPreference = "Stop"
$Depot = "NockiProgramTECH/nck"
$Prefix = if ($env:NCK_PREFIX) { $env:NCK_PREFIX } else { Join-Path $env:LOCALAPPDATA "NCK" }
$Version = $env:NCK_VERSION
if (-not $Version) {
  $rel = Invoke-RestMethod "https://api.github.com/repos/$Depot/releases/latest"
  $Version = $rel.tag_name -replace '^v', ''
}
$Arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "x64" }
$Archive = "nck-$Version-windows-$Arch.zip"
$Url = "https://github.com/$Depot/releases/download/v$Version/$Archive"
Write-Host "→ Téléchargement de NCK $Version (windows-$Arch)…"
$Tmp = Join-Path $env:TEMP $Archive
Invoke-WebRequest $Url -OutFile $Tmp
if (Test-Path $Prefix) { Remove-Item $Prefix -Recurse -Force }
New-Item -ItemType Directory -Path $Prefix | Out-Null
Expand-Archive $Tmp -DestinationPath $Prefix -Force
Remove-Item $Tmp
# L'archive contient un dossier nck\ : on remonte son contenu.
$Interne = Join-Path $Prefix "nck"
if (Test-Path (Join-Path $Interne "nck.exe")) {
  Get-ChildItem $Interne | Move-Item -Destination $Prefix -Force
  Remove-Item $Interne -Recurse -Force
}
# PATH utilisateur
$PathUtilisateur = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not (($PathUtilisateur -split ";") -contains $Prefix)) {
  [Environment]::SetEnvironmentVariable("Path", "$PathUtilisateur;$Prefix", "User")
  $env:Path = "$env:Path;$Prefix"
  Write-Host "→ $Prefix ajouté au PATH (ouvrez un nouveau terminal)."
}
# Extension VS Code
$VsCode = Join-Path $env:USERPROFILE ".vscode\extensions"
if ((Test-Path (Join-Path $env:USERPROFILE ".vscode")) -and (Test-Path (Join-Path $Prefix "editeurs\vscode"))) {
  $Cible = Join-Path $VsCode "nck-lang"
  if (Test-Path $Cible) { Remove-Item $Cible -Recurse -Force }
  New-Item -ItemType Directory -Path $VsCode -Force | Out-Null
  Copy-Item (Join-Path $Prefix "editeurs\vscode") $Cible -Recurse
  Write-Host "→ Extension VS Code installée (redémarrez VS Code)."
}
Write-Host ""
& (Join-Path $Prefix "nck.exe") info
Write-Host ""
Write-Host "✓ NCK $Version installé. Essayez :  nck `"$Prefix\exemples\bonjour.nck`""
