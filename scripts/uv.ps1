$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$globalUv = Get-Command uv -ErrorAction SilentlyContinue
$localUv = Join-Path $projectRoot '.tools/uv/bin/uv.exe'
if ($globalUv) {
    $uvExecutable = $globalUv.Source
} elseif (Test-Path -LiteralPath $localUv) {
    $uvExecutable = $localUv
} else {
    throw 'uv was not found. Install uv, then rerun. See docs/DEVELOPMENT.md.'
}
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectRoot '.tools/python'
$env:UV_PYTHON_BIN_DIR = Join-Path $projectRoot '.tools/bin'
$env:UV_CACHE_DIR = Join-Path $projectRoot '.tools/uv-cache'
Push-Location (Join-Path $projectRoot 'backend')
try {
    & $uvExecutable @args
    $toolExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $toolExitCode
