[CmdletBinding()]
param(
    [string]$OutputPath,
    [string]$PythonExecutable = "python"
)

$ErrorActionPreference = "Stop"

$sourceDirectory = Join-Path $PSScriptRoot "..\..\app\azure_function"
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$artifactDirectory = Join-Path $repositoryRoot "artifacts"
$outputDirectory = if ($OutputPath) { Split-Path -Parent ([System.IO.Path]::GetFullPath($OutputPath)) } else { $artifactDirectory }
$buildId = [guid]::NewGuid().ToString("N")
$stagingDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("tangamandapio-function-" + $buildId)
$stagedArchive = Join-Path $outputDirectory (".azure-function-package-" + $buildId + ".zip")

try {
    New-Item -ItemType Directory -Force -Path $outputDirectory, $stagingDirectory | Out-Null

    Copy-Item -Path (Join-Path $sourceDirectory "function_app.py") -Destination $stagingDirectory
    Copy-Item -Path (Join-Path $sourceDirectory "host.json") -Destination $stagingDirectory
    Copy-Item -Path (Join-Path $sourceDirectory "requirements.txt") -Destination $stagingDirectory
    Copy-Item -Path (Join-Path $sourceDirectory "requirements.lock") -Destination $stagingDirectory

    $dependenciesDirectory = Join-Path $stagingDirectory ".python_packages\lib\site-packages"
    New-Item -ItemType Directory -Force -Path $dependenciesDirectory | Out-Null
    & $PythonExecutable -m pip install --disable-pip-version-check --no-cache-dir --no-compile `
        --target $dependenciesDirectory `
        --require-hashes --only-binary=:all: `
        --python-version 3.11 --platform manylinux2014_x86_64 --implementation cp --abi cp311 `
        --requirement (Join-Path $sourceDirectory "requirements.lock")
    if ($LASTEXITCODE -ne 0) {
        throw "Function dependency installation failed with exit code $LASTEXITCODE."
    }

    # Windows PowerShell 5.1 does not eagerly load the compression assemblies.
    # Load the framework types explicitly before creating/validating the ZIP.
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $fixedTimestamp = [DateTimeOffset]::new(1980, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
    $zipStream = [System.IO.File]::Open(
        $stagedArchive,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
    $archive = $null
    try {
        $archive = [System.IO.Compression.ZipArchive]::new(
            $zipStream,
            [System.IO.Compression.ZipArchiveMode]::Create,
            $false
        )

        $files = Get-ChildItem -LiteralPath $stagingDirectory -Recurse -File |
            Where-Object { $_.FullName -notmatch "__pycache__|\.pyc$" } |
            Sort-Object FullName
        $stagingRootPrefix = [System.IO.Path]::GetFullPath($stagingDirectory)
        $lastRootCharacter = $stagingRootPrefix[$stagingRootPrefix.Length - 1]
        if ($lastRootCharacter -ne [System.IO.Path]::DirectorySeparatorChar -and
            $lastRootCharacter -ne [System.IO.Path]::AltDirectorySeparatorChar) {
            $stagingRootPrefix += [System.IO.Path]::DirectorySeparatorChar
        }

        foreach ($file in $files) {
            $fullPath = [System.IO.Path]::GetFullPath($file.FullName)
            if (-not $fullPath.StartsWith($stagingRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Function staging file escaped the package directory: $($file.Name)"
            }
            $relativePath = $fullPath.Substring($stagingRootPrefix.Length).Replace("\", "/")
            $entry = $archive.CreateEntry($relativePath, [System.IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = $fixedTimestamp

            $inputStream = [System.IO.File]::OpenRead($file.FullName)
            $entryStream = $null
            try {
                $entryStream = $entry.Open()
                $inputStream.CopyTo($entryStream)
            }
            finally {
                if ($null -ne $entryStream) {
                    $entryStream.Dispose()
                }
                $inputStream.Dispose()
            }
        }
    }
    finally {
        if ($null -ne $archive) {
            try {
                $archive.Dispose()
            }
            finally {
                $zipStream.Dispose()
            }
        }
        else {
            $zipStream.Dispose()
        }
    }

    $package = [System.IO.Compression.ZipFile]::OpenRead($stagedArchive)
    try {
        $entryNames = @($package.Entries | ForEach-Object { $_.FullName })
        $requiredEntries = @(
            "function_app.py",
            "host.json",
            "requirements.txt",
            "requirements.lock",
            ".python_packages/lib/site-packages/azure/functions/__init__.py"
        )
        $missingEntries = @($requiredEntries | Where-Object { $_ -notin $entryNames })
        if ($missingEntries.Count -gt 0) {
            throw "Function ZIP is incomplete: $($missingEntries -join ', ')"
        }
    }
    finally {
        $package.Dispose()
    }

    $packageSha256 = (Get-FileHash -LiteralPath $stagedArchive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($OutputPath) {
        $resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
        $expectedName = "azure_function_package-$packageSha256.zip"
        if ([System.IO.Path]::GetFileName($resolvedOutput) -ne $expectedName) {
            throw "OutputPath debe usar el nombre inmutable $expectedName"
        }
    }
    else {
        $resolvedOutput = Join-Path $artifactDirectory "azure_function_package-$packageSha256.zip"
    }

    if (Test-Path -LiteralPath $resolvedOutput) {
        $existingSha256 = (Get-FileHash -LiteralPath $resolvedOutput -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($existingSha256 -ne $packageSha256) {
            throw "El destino ya existe con contenido distinto; no se sobrescribe: $resolvedOutput"
        }
        Remove-Item -LiteralPath $stagedArchive -Force
        Write-Host "Paquete inmutable ya existente: $resolvedOutput"
    }
    else {
        [System.IO.File]::Move($stagedArchive, $resolvedOutput)
        Write-Host "Paquete inmutable creado: $resolvedOutput"
    }

    Write-Host "SHA256: $packageSha256"
    Write-Output "PACKAGE_PATH=$resolvedOutput"
}
finally {
    if (Test-Path $stagingDirectory) {
        Remove-Item -LiteralPath $stagingDirectory -Recurse -Force
    }
    if (Test-Path $stagedArchive) {
        Remove-Item -LiteralPath $stagedArchive -Force
    }
}
