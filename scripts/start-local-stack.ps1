[CmdletBinding()]
param(
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$FrontendRoot = Join-Path $RepoRoot "frontend\admin"

function Write-Step {
    param([string]$Message)
    Write-Host "[finevent] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[ok] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[warn] $Message" -ForegroundColor Yellow
}

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
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.Length -ge 2) {
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        if ($key -match "^[A-Za-z_][A-Za-z0-9_]*$") {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

function Set-OrAppend-DotEnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    $lines = @()
    if (Test-Path $Path) {
        $lines = @(Get-Content $Path)
    }

    $pattern = "^" + [regex]::Escape($Key) + "="
    $updated = $false
    $nextLines = foreach ($line in $lines) {
        if ($line -match $pattern) {
            $updated = $true
            "$Key=$Value"
        }
        else {
            $line
        }
    }

    if (-not $updated) {
        $nextLines += "$Key=$Value"
    }

    $nextLines | Set-Content -Path $Path -Encoding UTF8
    [Environment]::SetEnvironmentVariable($Key, $Value, "Process")
}

function New-LocalAdminKey {
    $bytes = [byte[]]::new(32)
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    $token = [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_").TrimEnd("=")
    return "finevent-local-$token"
}

function Ensure-RootEnv {
    $envPath = Join-Path $RepoRoot ".env"
    $envExamplePath = Join-Path $RepoRoot ".env.example"

    if (-not (Test-Path $envPath)) {
        Copy-Item $envExamplePath $envPath
        Write-Warn "Created .env from .env.example. Fill external API keys before running model workflows."
    }

    Import-DotEnv $envPath

    if (-not $env:FINEVENT_ADMIN_API_KEY) {
        Set-OrAppend-DotEnvValue -Path $envPath -Key "FINEVENT_ADMIN_API_KEY" -Value (New-LocalAdminKey)
        Write-Ok "Generated FINEVENT_ADMIN_API_KEY in .env for local admin authentication."
    }
    if (-not $env:FINEVENT_ADMIN_AUTH_DISABLED) {
        Set-OrAppend-DotEnvValue -Path $envPath -Key "FINEVENT_ADMIN_AUTH_DISABLED" -Value "false"
    }
    if (-not $env:FINEVENT_ALLOWED_ORIGINS) {
        Set-OrAppend-DotEnvValue -Path $envPath -Key "FINEVENT_ALLOWED_ORIGINS" -Value "http://localhost:3000,http://127.0.0.1:3000"
    }

    Import-DotEnv $envPath
}

function Ensure-FrontendEnv {
    param([int]$Port)

    $frontendEnvPath = Join-Path $FrontendRoot ".env.local"
    $apiBaseUrl = "http://127.0.0.1:$Port"

    @(
        "# Local Next.js runtime config for FinEvent Admin."
        "# Do not put FINEVENT_ADMIN_API_KEY here because NEXT_PUBLIC_* is visible in the browser bundle."
        "# Enter the admin key at /admin/settings instead."
        "NEXT_PUBLIC_FINEVENT_API_BASE_URL=$apiBaseUrl"
    ) | Set-Content -Path $frontendEnvPath -Encoding UTF8
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

function Stop-LegacyProjectProcessOnPort {
    param([int]$Port)

    $connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    foreach ($connection in $connections) {
        $pidValue = [int]$connection.OwningProcess
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $pidValue" -ErrorAction SilentlyContinue
        if (-not $process -or -not $process.CommandLine) {
            continue
        }

        $commandLine = $process.CommandLine
        $belongsToProject = $commandLine.Contains($RepoRoot.Path) -or $commandLine.Contains("frontend\admin") -or $commandLine.Contains("finevent.api.main")
        $isDevRuntime = $process.Name -match "^(python|python.exe|node|node.exe|pnpm|pnpm.cmd)$"

        if ($belongsToProject -and $isDevRuntime) {
            Write-Warn "Stopping legacy native dev process on port ${Port}: PID $pidValue ($($process.Name))."
            Stop-Process -Id $pidValue -Force
        }
    }
}

function Wait-ContainerHealthy {
    param(
        [string]$ContainerName,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $status = docker inspect -f "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $ContainerName 2>$null
        if ($status -eq "healthy" -or $status -eq "running") {
            Write-Ok "$ContainerName is $status."
            return
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    docker logs --tail 80 $ContainerName
    throw "Timed out waiting for $ContainerName to become healthy."
}

function Test-Http {
    param(
        [string]$Url,
        [hashtable]$Headers = @{}
    )

    $response = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 20
    return $response.StatusCode
}

Ensure-RootEnv
$BackendPort = Resolve-Port -Provided $BackendPort -EnvName "BACKEND_PORT" -Default 18000
$FrontendPort = Resolve-Port -Provided $FrontendPort -EnvName "FRONTEND_PORT" -Default 3000

[Environment]::SetEnvironmentVariable("BACKEND_PORT", "$BackendPort", "Process")
[Environment]::SetEnvironmentVariable("FRONTEND_PORT", "$FrontendPort", "Process")
[Environment]::SetEnvironmentVariable("NEXT_PUBLIC_FINEVENT_API_BASE_URL", "http://127.0.0.1:$BackendPort", "Process")

Ensure-FrontendEnv -Port $BackendPort
Stop-LegacyProjectProcessOnPort -Port $FrontendPort
Stop-LegacyProjectProcessOnPort -Port $BackendPort

Push-Location $RepoRoot
try {
    $composeArgs = @("compose", "up", "-d")
    if (-not $NoBuild) {
        $composeArgs += "--build"
    }

    Write-Step "Starting full Docker Compose stack..."
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed with exit code $LASTEXITCODE."
    }

    Wait-ContainerHealthy -ContainerName "finevent-postgres"
    Wait-ContainerHealthy -ContainerName "finevent-backend"
    Wait-ContainerHealthy -ContainerName "finevent-frontend"

    $apiStatus = Test-Http -Url "http://127.0.0.1:$BackendPort/health"
    Write-Ok "Backend /health returned HTTP $apiStatus."

    $adminStatus = Test-Http `
        -Url "http://127.0.0.1:$BackendPort/admin/health" `
        -Headers @{ "X-Admin-API-Key" = $env:FINEVENT_ADMIN_API_KEY }
    Write-Ok "Backend /admin/health returned HTTP $adminStatus."

    $frontendStatus = Test-Http -Url "http://localhost:$FrontendPort/admin"
    Write-Ok "Frontend /admin returned HTTP $frontendStatus."
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "FinEvent Docker stack is ready:" -ForegroundColor Green
Write-Host "  Admin UI:   http://localhost:$FrontendPort/admin"
Write-Host "  Backend:    http://127.0.0.1:$BackendPort"
$postgresPort = $env:POSTGRES_PORT
if (-not $postgresPort) {
    $postgresPort = "55433"
}
Write-Host "  Postgres:   localhost:$postgresPort"
Write-Host ""
Write-Host "Open /admin/settings and enter FINEVENT_ADMIN_API_KEY from root .env."
