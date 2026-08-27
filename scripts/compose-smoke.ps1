param(
    [int] $TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

function Wait-ForHttp {
    param(
        [string] $Url,
        [int] $TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5

            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                return
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "Timed out waiting for $Url"
}

function Invoke-Checked {
    param(
        [string] $FilePath,
        [string[]] $Arguments
    )

    & $FilePath @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

Invoke-Checked "docker" @("compose", "build")
Invoke-Checked "docker" @("compose", "up", "-d", "postgres", "redis")
Invoke-Checked "docker" @("compose", "run", "--rm", "api", "alembic", "upgrade", "head")
Invoke-Checked "docker" @("compose", "up", "-d", "api", "worker")

try {
    Wait-ForHttp -Url "http://localhost:8000/health" -TimeoutSeconds $TimeoutSeconds
    Wait-ForHttp -Url "http://localhost:8000/health/ready" -TimeoutSeconds $TimeoutSeconds
    Wait-ForHttp -Url "http://localhost:8000/openapi.json" -TimeoutSeconds $TimeoutSeconds

    Invoke-Checked "docker" @("compose", "ps")
    Write-Host "Compose smoke test passed."
}
finally {
    docker compose down
}
