#Requires -Version 7.4
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backupDirectory = Join-Path $projectRoot '.data/backups'
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
$backupName = "wagamaga-$(Get-Date -AsUTC -Format 'yyyyMMddTHHmmssZ')-$([guid]::NewGuid().ToString('N')).dump"
$archive = Join-Path $backupDirectory $backupName
$partial = "$archive.partial"

Push-Location $projectRoot
try {
    # PowerShell 7.4+ preserves native stdout bytes during redirection.
    docker compose exec -T db sh -eu -c 'pg_dump --username "$POSTGRES_USER" --dbname "$APP_DB_NAME" --format custom' > $partial
    if ($LASTEXITCODE -ne 0) {
        throw 'PostgreSQL backup failed.'
    }
    $stream = [IO.File]::OpenRead($partial)
    try {
        $header = [byte[]]::new(5)
        if ($stream.Read($header, 0, $header.Length) -ne $header.Length -or
            [Text.Encoding]::ASCII.GetString($header) -ne 'PGDMP') {
            throw 'PostgreSQL backup did not produce a valid archive header.'
        }
    } finally {
        $stream.Dispose()
    }
    Move-Item -LiteralPath $partial -Destination $archive
    Get-FileHash -LiteralPath $archive -Algorithm SHA256
} finally {
    if (Test-Path -LiteralPath $partial) {
        Remove-Item -LiteralPath $partial
    }
    Pop-Location
}
