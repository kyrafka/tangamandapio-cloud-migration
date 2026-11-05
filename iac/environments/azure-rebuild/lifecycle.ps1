[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('up', 'down', 'bootstrap-state')]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$ExpectedSubscriptionId,

    [string]$VarFile = (Join-Path $PSScriptRoot 'rebuild.tfvars.example'),

    [string]$TerraformPath,

    [string]$BootstrapStatePath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Stop-Lifecycle([string]$Message) {
    throw "Operación detenida: $Message"
}

if ($ExpectedSubscriptionId -notmatch '^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$') {
    Stop-Lifecycle 'ExpectedSubscriptionId debe ser el GUID de la suscripción autorizada.'
}

$az = Get-Command az -ErrorAction SilentlyContinue
if (-not $az) { Stop-Lifecycle 'no se encontró Azure CLI.' }
$actualSubscriptionId = (& $az.Source account show --query id --output tsv 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($actualSubscriptionId)) {
    Stop-Lifecycle 'Azure CLI no tiene una sesión válida; no se tocaron recursos.'
}
$actualSubscriptionId = $actualSubscriptionId.Trim()
if (-not $actualSubscriptionId.Equals($ExpectedSubscriptionId, [StringComparison]::OrdinalIgnoreCase)) {
    Stop-Lifecycle "la sesión apunta a otra suscripción ($actualSubscriptionId)."
}
Write-Host 'Alcance: solo la raíz azure-rebuild; no despliega la VPN, las demás redes privadas, recuperación entre regiones ni recursos AWS.'

if ([string]::IsNullOrWhiteSpace($TerraformPath)) {
    $repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
    $bundledTerraform = Join-Path $repoRoot 'tools\terraform-1.16.0\terraform.exe'
    if (Test-Path -LiteralPath $bundledTerraform) {
        $TerraformPath = $bundledTerraform
    } else {
        $terraformCommand = Get-Command terraform -ErrorAction SilentlyContinue
        if (-not $terraformCommand) { Stop-Lifecycle 'no se encontró Terraform 1.5 o posterior.' }
        $TerraformPath = $terraformCommand.Source
    }
}

$mainRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$stateRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\azure-tfstate'))
$packageScript = Join-Path $PSScriptRoot '..\..\scripts\package_azure_function.ps1'
$planPath = Join-Path ([IO.Path]::GetTempPath()) ("tangamandapio-$Action-$([guid]::NewGuid().ToString('N')).tfplan")
$bootstrapRoot = $null
$bootstrapSucceeded = $false

function Invoke-Terraform([string]$Root, [string[]]$Arguments) {
    & $TerraformPath "-chdir=$Root" @Arguments
    if ($LASTEXITCODE -ne 0) { Stop-Lifecycle "Terraform falló en $Root (código $LASTEXITCODE)." }
}

function Confirm-Apply([string]$Prompt, [string]$ExpectedText) {
    $answer = Read-Host $Prompt
    if ($answer -cne $ExpectedText) { Stop-Lifecycle 'confirmación incorrecta; no se aplicó el plan.' }
}

function Initialize-Backend([string]$Root, [switch]$Reconfigure, [int]$RetryCount = 1) {
    $arguments = @('init', '-input=false', '-lockfile=readonly')
    if ($Reconfigure) { $arguments += '-reconfigure' }
    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        $output = @(& $TerraformPath "-chdir=$Root" @arguments 2>&1)
        if ($LASTEXITCODE -eq 0) {
            $output | ForEach-Object { Write-Host $_ }
            return
        }

        $message = ($output | ForEach-Object { $_.ToString() }) -join "`n"
        $isTransientRbacFailure = $message -match '403|AuthorizationPermissionMismatch|Failed to get existing workspaces'
        if ($isTransientRbacFailure -and $attempt -lt $RetryCount) {
            Write-Warning "El permiso de Blob aún se propaga; reintento $($attempt + 1) de $RetryCount en 20 segundos."
            Start-Sleep -Seconds 20
            continue
        }

        $output | ForEach-Object { Write-Host $_ }
        Stop-Lifecycle "Terraform no pudo inicializar el backend en $Root (código $LASTEXITCODE)."
    }
}

function Build-FunctionPackage {
    $packageOutput = @(& $packageScript)
    if ($LASTEXITCODE -ne 0) { Stop-Lifecycle 'no se pudo construir el paquete reproducible de la Function.' }
    $packageLine = $packageOutput | Where-Object { $_ -match '^PACKAGE_PATH=' } | Select-Object -Last 1
    if (-not $packageLine) { Stop-Lifecycle 'el empaquetador no devolvió PACKAGE_PATH.' }
    $packagePath = ($packageLine -replace '^PACKAGE_PATH=', '').Trim()
    if (-not (Test-Path -LiteralPath $packagePath)) { Stop-Lifecycle 'el paquete generado no existe.' }
    Write-Host ($packageOutput | Where-Object { $_ -notmatch '^PACKAGE_PATH=' })
    return $packagePath
}

function Complete-StateBackend([string]$StateFile) {
    if (-not (Test-Path -LiteralPath $StateFile -PathType Leaf)) {
        Stop-Lifecycle 'no existe el archivo de state local para completar el backend.'
    }

    $resolvedStateFile = [IO.Path]::GetFullPath($StateFile)
    $stateDirectory = [IO.Path]::GetDirectoryName($resolvedStateFile)
    $expectedTempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\', '/')
    $directoryName = [IO.Path]::GetFileName($stateDirectory)
    if ([IO.Path]::GetFileName($resolvedStateFile) -cne 'terraform.tfstate' -or
        -not $stateDirectory.StartsWith("$expectedTempRoot\", [StringComparison]::OrdinalIgnoreCase) -or
        $directoryName -notmatch '^tangamandapio-tfstate-[0-9a-f]{32}$') {
        Stop-Lifecycle 'el state de recuperación debe estar en una carpeta temporal tangamandapio-tfstate generada por este lifecycle.'
    }

    try {
        $stateDocument = Get-Content -LiteralPath $resolvedStateFile -Raw | ConvertFrom-Json
    }
    catch {
        Stop-Lifecycle 'el state local no es JSON válido; no se enviará al backend.'
    }
    $stateResources = @($stateDocument.resources | ForEach-Object { "$($_.type).$($_.name)" })
    $requiredResources = @(
        'azurerm_resource_group.state',
        'azurerm_storage_account.state',
        'azurerm_role_assignment.backend_writer',
        'azurerm_storage_container.state'
    )
    if (@($requiredResources | Where-Object { $_ -notin $stateResources }).Count -gt 0) {
        Stop-Lifecycle 'el state de recuperación no contiene todos los recursos esperados del backend.'
    }

    $rgState = $stateDocument.resources | Where-Object { $_.type -eq 'azurerm_resource_group' -and $_.name -eq 'state' } | Select-Object -First 1
    $storageState = $stateDocument.resources | Where-Object { $_.type -eq 'azurerm_storage_account' -and $_.name -eq 'state' } | Select-Object -First 1
    if ($rgState.instances[0].attributes.name -cne 'rg-tangamandapio-tfstate-wus' -or
        $storageState.instances[0].attributes.name -cne 'sttangamatfstate261014') {
        Stop-Lifecycle 'el state local no corresponde al backend esperado de Tangamandapio.'
    }

    $script:bootstrapRoot = $stateDirectory
    Write-Host 'Se recuperará el backend con el state local verificado; no se volverán a crear recursos.'
    Initialize-Backend $stateRoot -Reconfigure -RetryCount 8
    Invoke-Terraform $stateRoot @('state', 'push', $resolvedStateFile)
    $remoteStateResources = @(& $TerraformPath "-chdir=$stateRoot" 'state' 'list')
    if ($LASTEXITCODE -ne 0 -or $remoteStateResources -notcontains 'azurerm_resource_group.state') {
        Stop-Lifecycle 'no se pudo verificar el state remoto; conserva el state de bootstrap para recuperación.'
    }

    $script:bootstrapSucceeded = $true
    Write-Host 'Backend remoto y state verificados. Ya puedes continuar con up.'
}

try {
    switch ($Action) {
        'bootstrap-state' {
            # This root is intentionally separate and is never destroyed by `down`.
            $localState = Join-Path $stateRoot 'terraform.tfstate'
            $localBackup = Join-Path $stateRoot 'terraform.tfstate.backup'
            if ((Test-Path -LiteralPath $localState) -or (Test-Path -LiteralPath $localBackup)) {
                Stop-Lifecycle 'hay state local de bootstrap. Verifica y migra ese state antes de inicializar otra copia.'
            }
            $backendGroupState = (& $az.Source group exists --name 'rg-tangamandapio-tfstate-wus' --output tsv 2>$null)
            if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($backendGroupState)) {
                Stop-Lifecycle 'no se pudo verificar si ya existe el grupo del backend; no se inicializará un state vacío.'
            }
            if ($backendGroupState.Trim().ToLowerInvariant() -ne 'false') {
                if ($backendGroupState.Trim().ToLowerInvariant() -eq 'true' -and $BootstrapStatePath) {
                    Complete-StateBackend $BootstrapStatePath
                    break
                }
                Stop-Lifecycle 'el grupo del backend ya existe o el resultado fue inesperado. Para recuperar un bootstrap parcial, indica -BootstrapStatePath con el state local guardado.'
            }
            if ($BootstrapStatePath) {
                Stop-Lifecycle 'se indicó un state de recuperación, pero el grupo del backend no existe; no se usará un state anterior para crear recursos.'
            }
            Write-Host "Suscripción verificada: $actualSubscriptionId"
            Write-Host 'Se preparará el backend remoto de Terraform; este almacenamiento tiene costo y se conserva durante down.'

            # Bootstrap the storage account from a clean local-only root. The committed
            # backend.tf points at the storage account being created, so planning in the
            # source root can accidentally reuse stale .terraform backend metadata.
            $bootstrapRoot = Join-Path ([IO.Path]::GetTempPath()) ("tangamandapio-tfstate-$([guid]::NewGuid().ToString('N'))")
            New-Item -ItemType Directory -Path $bootstrapRoot | Out-Null
            Get-ChildItem -LiteralPath $stateRoot -File |
                Where-Object { $_.Extension -eq '.tf' -and $_.Name -ne 'backend.tf' } |
                Copy-Item -Destination $bootstrapRoot
            $lockFile = Join-Path $stateRoot '.terraform.lock.hcl'
            if (Test-Path -LiteralPath $lockFile) {
                Copy-Item -LiteralPath $lockFile -Destination $bootstrapRoot
            }

            Invoke-Terraform $bootstrapRoot @('init', '-backend=false', '-input=false', '-lockfile=readonly')
            Invoke-Terraform $bootstrapRoot @('validate')
            Invoke-Terraform $bootstrapRoot @('plan', '-input=false', "-out=$planPath")
            Invoke-Terraform $bootstrapRoot @('show', '-no-color', $planPath)
            Confirm-Apply 'Escribe BOOTSTRAP STATE para crear el backend remoto' 'BOOTSTRAP STATE'
            Invoke-Terraform $bootstrapRoot @('apply', '-input=false', $planPath)

            $bootstrapState = Join-Path $bootstrapRoot 'terraform.tfstate'
            if (-not (Test-Path -LiteralPath $bootstrapState) -or (Get-Item -LiteralPath $bootstrapState).Length -eq 0) {
                Stop-Lifecycle 'Terraform no produjo el state local del backend; no se intentará migrar un state vacío.'
            }
            Complete-StateBackend $bootstrapState
            Write-Host 'Backend remoto inicializado. Ejecuta un plan normal antes de continuar con up.'
        }
        'up' {
            $resolvedVarFile = (Resolve-Path -LiteralPath $VarFile -ErrorAction Stop).Path
            $resourceGroupMatch = [regex]::Match((Get-Content -LiteralPath $resolvedVarFile -Raw), '(?m)^\s*resource_group_name\s*=\s*"([^"]+)"')
            if (-not $resourceGroupMatch.Success) { Stop-Lifecycle 'el archivo tfvars debe declarar resource_group_name.' }
            Write-Host "Suscripción verificada: $actualSubscriptionId"
            Write-Host "Alcance: raíz azure-rebuild, grupo $($resourceGroupMatch.Groups[1].Value). El backend Terraform y otras raíces no se modifican."

            $packagePath = Build-FunctionPackage

            Initialize-Backend $mainRoot
            Invoke-Terraform $mainRoot @('validate')
            Invoke-Terraform $mainRoot @('plan', '-input=false', "-var-file=$resolvedVarFile", "-var=function_package_path=$packagePath", "-out=$planPath")
            Invoke-Terraform $mainRoot @('show', '-no-color', $planPath)
            Confirm-Apply 'Revisa el plan. Escribe APPLY para crear/actualizar Azure' 'APPLY'
            Invoke-Terraform $mainRoot @('apply', '-input=false', $planPath)
            Write-Host 'Apply completado. Ejecuta el smoke funcional y revisa costes/estado del grupo.'
        }
        'down' {
            $resolvedVarFile = (Resolve-Path -LiteralPath $VarFile -ErrorAction Stop).Path
            $resourceGroupMatch = [regex]::Match((Get-Content -LiteralPath $resolvedVarFile -Raw), '(?m)^\s*resource_group_name\s*=\s*"([^"]+)"')
            if (-not $resourceGroupMatch.Success) { Stop-Lifecycle 'el archivo tfvars debe declarar resource_group_name.' }
            $resourceGroupName = $resourceGroupMatch.Groups[1].Value
            Write-Host "Suscripción verificada: $actualSubscriptionId"
            Write-Host "Se destruirán únicamente los recursos de la raíz azure-rebuild en $resourceGroupName."
            Write-Host 'El backend remoto de state, azure-flex-private, azure-p2s-vpn y aws-azure-vpn no se destruyen con este comando.'

            # The root validates this required file variable even for a destroy plan.
            # Rebuild the current package locally so teardown also works from a clean checkout.
            $packagePath = Build-FunctionPackage
            Initialize-Backend $mainRoot
            Invoke-Terraform $mainRoot @('plan', '-destroy', '-input=false', "-var-file=$resolvedVarFile", "-var=function_package_path=$packagePath", "-out=$planPath")
            Invoke-Terraform $mainRoot @('show', '-no-color', $planPath)
            Confirm-Apply "Revisa el plan. Escribe DESTROY $resourceGroupName para eliminar esos recursos" "DESTROY $resourceGroupName"
            Invoke-Terraform $mainRoot @('apply', '-input=false', $planPath)
            Write-Host 'Recursos de azure-rebuild eliminados. El state backend sigue activo para permitir una reconstrucción.'
        }
    }
}
finally {
    if (Test-Path -LiteralPath $planPath) { Remove-Item -LiteralPath $planPath -Force }
    if ($bootstrapRoot -and (Test-Path -LiteralPath $bootstrapRoot)) {
        if ($bootstrapSucceeded) {
            Remove-Item -LiteralPath $bootstrapRoot -Recurse -Force
        }
        elseif (Test-Path -LiteralPath (Join-Path $bootstrapRoot 'terraform.tfstate')) {
            Write-Warning "Bootstrap dejó state local para recuperación en: $bootstrapRoot"
        }
        else {
            Remove-Item -LiteralPath $bootstrapRoot -Recurse -Force
        }
    }
}
