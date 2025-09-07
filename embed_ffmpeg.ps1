# requires -Version 5.1
<# 
Embed FFmpeg for this app (Windows x64)
- Downloads the latest prebuilt FFmpeg from BtbN (ZIP)
- Extracts and copies ffmpeg.exe, ffprobe.exe and ffplay.exe to .\app\bin
- Copies license files to .\app\licenses\ffmpeg
#>

[CmdletBinding()]
param(
    [string]$SourceUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
)

$ErrorActionPreference = "Stop"

function Ensure-Tls12 {
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    } catch {}
}

function New-Dir([string]$p) {
    if (-not (Test-Path -LiteralPath $p)) {
        New-Item -ItemType Directory -Path $p -Force | Out-Null
    }
}

function Download-File([string]$url, [string]$dest) {
    Write-Host "Baixando: $url"
    try {
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -TimeoutSec 600
    } catch {
        Write-Warning "Falha com Invoke-WebRequest. Tentando Start-BitsTransfer..."
        Start-BitsTransfer -Source $url -Destination $dest -ErrorAction Stop
    }
}

function Get-Sha256([string]$file) {
    $h = Get-FileHash -Algorithm SHA256 -LiteralPath $file
    return $h.Hash.ToLower()
}

# 1) Local paths
$projRoot = (Get-Location).Path
$appDir   = Join-Path $projRoot "app"
$binDir   = Join-Path $appDir "bin"
$licDir   = Join-Path $appDir "licenses\ffmpeg"
$tmp      = Join-Path $env:TEMP ("ffmpeg_dl_" + [guid]::NewGuid().ToString("N"))
$zipFile  = Join-Path $tmp "ffmpeg.zip"

# 2) Prep dirs
Ensure-Tls12
New-Dir $tmp
New-Dir $appDir
New-Dir $binDir
New-Dir $licDir

# 3) Download
Download-File -url $SourceUrl -dest $zipFile
$sha = Get-Sha256 $zipFile
Write-Host "SHA256 do pacote baixado: $sha"

# 4) Extract
$extractDir = Join-Path $tmp "unzipped"
New-Dir $extractDir
Expand-Archive -LiteralPath $zipFile -DestinationPath $extractDir -Force

# 5) Locate bin folder automatically (varies by build)
$binCandidates = Get-ChildItem -Path $extractDir -Filter "bin" -Recurse -Directory | Select-Object -First 1
if (-not $binCandidates) {
    throw "Pasta 'bin' não encontrada no pacote FFmpeg."
}
$binSrc = $binCandidates.FullName

# 6) Copy executables
$exeNames = @("ffmpeg.exe", "ffprobe.exe", "ffplay.exe")
foreach ($exe in $exeNames) {
    $src = Join-Path $binSrc $exe
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $binDir $exe) -Force
    } else {
        Write-Warning "$exe não encontrado no pacote; seguindo."
    }
}

# 7) Copy license/readme files if present
$licenseFiles = Get-ChildItem -Path $extractDir -Recurse -File | Where-Object {
    $_.Name -match 'LICENSE|COPYING|README|NOTICE'
}
foreach ($f in $licenseFiles) {
    Copy-Item -LiteralPath $f.FullName -Destination $licDir -Force
}

# 8) Print summary
Write-Host ""
Write-Host "✅ FFmpeg incorporado com sucesso em: $binDir"
Write-Host "   - Verifique com: .\app\bin\ffmpeg.exe -version"
Write-Host "   - Licenças: $licDir"
Write-Host ""
Write-Host "Dica: mantenha esses binários junto com seu executável/app para execução portátil."
