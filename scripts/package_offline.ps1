$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$output = Join-Path $repo "deploy\offline"
$archive = Join-Path $output "greenhouse-images.tar"

Push-Location $repo
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker Engine is not running." }
    docker compose build --pull
    if ($LASTEXITCODE -ne 0) { throw "Image build failed." }
    docker compose pull mosquitto
    if ($LASTEXITCODE -ne 0) { throw "Mosquitto image pull failed." }

    New-Item -ItemType Directory -Force -Path $output | Out-Null
    docker image save --output $archive `
        greenhouse-api:0.2.0 `
        greenhouse-frontend:0.2.0 `
        eclipse-mosquitto:2
    if ($LASTEXITCODE -ne 0) { throw "Offline image export failed." }

    $hash = (Get-FileHash -Algorithm SHA256 $archive).Hash.ToLowerInvariant()
    "$hash *greenhouse-images.tar" | Set-Content -Encoding ascii "$archive.sha256"
    Write-Host "Offline image bundle created: $archive"
}
finally {
    Pop-Location
}
