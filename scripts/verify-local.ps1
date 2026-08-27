$ErrorActionPreference = "Stop"

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

$python = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

Invoke-Checked $python @("-m", "compileall", "app", "tests")
Invoke-Checked $python @("-m", "alembic", "current")
Invoke-Checked $python @("-m", "unittest", "discover", "-s", "tests")
Invoke-Checked "docker" @("compose", "config", "--quiet")
Invoke-Checked "terraform" @("-chdir=infra/aws", "validate")

Write-Host "Local verification passed."
