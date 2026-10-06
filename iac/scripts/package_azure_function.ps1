[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\..\artifacts\azure_function_package.zip")
)

$ErrorActionPreference = "Stop"

$sourceDirectory = Join-Path $PSScriptRoot "..\..\app\azure_function"
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $resolvedOutput
$stagingDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("tangamandapio-function-" + [guid]::NewGuid())

try {
    New-Item -ItemType Directory -Force -Path $outputDirectory, $stagingDirectory | Out-Null

    Copy-Item -Path (Join-Path $sourceDirectory "function_app.py") -Destination $stagingDirectory
    Copy-Item -Path (Join-Path $sourceDirectory "host.json") -Destination $stagingDirectory
    Copy-Item -Path (Join-Path $sourceDirectory "requirements.txt") -Destination $stagingDirectory

    $dependenciesDirectory = Join-Path $stagingDirectory ".python_packages\lib\site-packages"
    New-Item -ItemType Directory -Force -Path $dependenciesDirectory | Out-Null
    python -m pip install --disable-pip-version-check --no-cache-dir `
        --target $dependenciesDirectory `
        --requirement (Join-Path $sourceDirectory "requirements.txt")

    if (Test-Path $resolvedOutput) {
        Remove-Item -LiteralPath $resolvedOutput -Force
    }

    Compress-Archive -Path (Join-Path $stagingDirectory "*") -DestinationPath $resolvedOutput -Force
    Write-Host "Paquete creado: $resolvedOutput"
}
finally {
    if (Test-Path $stagingDirectory) {
        Remove-Item -LiteralPath $stagingDirectory -Recurse -Force
    }
}
