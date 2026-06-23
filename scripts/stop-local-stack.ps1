[CmdletBinding()]
param(
    [switch]$RemoveVolumes
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Push-Location $RepoRoot
try {
    $args = @("compose", "down")
    if ($RemoveVolumes) {
        $args += "-v"
    }
    & docker @args
}
finally {
    Pop-Location
}

Write-Host "FinEvent Docker stack stopped." -ForegroundColor Green
