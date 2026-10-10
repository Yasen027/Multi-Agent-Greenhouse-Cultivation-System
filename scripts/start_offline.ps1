$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$archive = Join-Path $repo "deploy\offline\greenhouse-images.tar"
$checksum = "$archive.sha256"

Push-Location $repo
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker Engine is not running. Start Docker Desktop first." }
    if (-not (Test-Path -LiteralPath $archive)) {
        throw "Offline image bundle not found: $archive"
    }
    if (Test-Path -LiteralPath $checksum) {
        $expected = ((Get-Content -LiteralPath $checksum -Raw) -split '\s+')[0]
        $actual = (Get-FileHash -Algorithm SHA256 $archive).Hash.ToLowerInvariant()
        if ($actual -ne $expected) {
            throw "Offline image checksum failed. Copy the bundle again."
        }
    }

    docker image load --input $archive
    if ($LASTEXITCODE -ne 0) { throw "Offline image load failed." }
    docker compose up -d --no-build --pull never --wait --wait-timeout 120
    if ($LASTEXITCODE -ne 0) { throw "One or more containers failed their health check." }

    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 5
    if ($health.status -ne "ok") {
        throw "API health endpoint did not return ok."
    }
    $twin = Invoke-RestMethod -Uri "http://localhost:8000/api/digital-twin/status" -TimeoutSec 5
    if (-not $twin.online) {
        throw "Digital twin is not online."
    }

    Write-Host "Startup passed: API, MQTT, digital twin, and frontend are healthy."
    Write-Host "Dashboard: http://localhost:5173"
}
finally {
    Pop-Location
}
