[CmdletBinding()]
param(
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

function Resolve-Port {
    param(
        [int]$Provided,
        [string]$EnvName,
        [int]$Default
    )
    if ($Provided -gt 0) {
        return $Provided
    }
    $value = [Environment]::GetEnvironmentVariable($EnvName, "Process")
    if ($value -and ($value -match "^\d+$")) {
        return [int]$value
    }
    return $Default
}

function Test-Http {
    param(
        [string]$Url,
        [hashtable]$Headers = @{}
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 8
        return "HTTP $($response.StatusCode)"
    }
    catch {
        return "unreachable"
    }
}

Import-DotEnv (Join-Path $RepoRoot ".env")
$BackendPort = Resolve-Port -Provided $BackendPort -EnvName "BACKEND_PORT" -Default 18000
$FrontendPort = Resolve-Port -Provided $FrontendPort -EnvName "FRONTEND_PORT" -Default 3000

Push-Location $RepoRoot
try {
    Write-Host "Docker Compose services" -ForegroundColor Cyan
    docker compose ps
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "HTTP checks" -ForegroundColor Cyan
Write-Host "  Backend /health: $(Test-Http -Url "http://127.0.0.1:$BackendPort/health")"
if ($env:FINEVENT_ADMIN_API_KEY) {
    Write-Host "  Backend /admin/health: $(Test-Http -Url "http://127.0.0.1:$BackendPort/admin/health" -Headers @{ "X-Admin-API-Key" = $env:FINEVENT_ADMIN_API_KEY })"
}
else {
    Write-Host "  Backend /admin/health: skipped because FINEVENT_ADMIN_API_KEY is empty"
}
Write-Host "  Frontend /admin: $(Test-Http -Url "http://localhost:$FrontendPort/admin")"
