[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [Guid]$ExpectedSubscriptionId,

    [Parameter(Mandatory = $true)]
    [string]$Confirmation
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$expectedGroups = [ordered]@{
    'rg-tangama-wg-hub-eus'          = 'Tangamandapio'
    'rg-tangama-private-network'     = 'Tangamandapio-Cloud'
    'rg-tangamandapio-rebuild-wus'   = 'Tangamandapio-Cloud'
    'rg-tangamandapio-tfstate-wus'   = 'Tangamandapio-Cloud'
}
$confirmationPhrase = "DELETE ALL TANGAMANDAPIO $ExpectedSubscriptionId"

function Invoke-AzJson([string[]]$Arguments) {
    $result = & az @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI falló: az $($Arguments -join ' ')"
    }
    return ($result | Out-String | ConvertFrom-Json)
}

$subscriptionId = (& az account show --query id --output tsv 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($subscriptionId)) {
    throw 'Azure CLI no tiene una sesión válida; no se eliminó nada.'
}
if (-not $subscriptionId.Trim().Equals($ExpectedSubscriptionId.ToString(), [StringComparison]::OrdinalIgnoreCase)) {
    throw "La sesión apunta a otra suscripción ($($subscriptionId.Trim())); no se eliminó nada."
}

$projectGroups = @(Invoke-AzJson @(
    'group', 'list',
    '--query', "[?tags.Project=='Tangamandapio-Cloud' || tags.Project=='Tangamandapio'].{name:name,project:tags.Project}",
    '--output', 'json'
))
$unexpectedGroups = @($projectGroups | Where-Object { -not $expectedGroups.Contains($_.name) })
if ($unexpectedGroups.Count -gt 0) {
    $names = ($unexpectedGroups | ForEach-Object { $_.name }) -join ', '
    throw "Hay grupos etiquetados del proyecto fuera de la lista aprobada ($names); no se eliminó nada."
}

$targets = @()
foreach ($groupName in $expectedGroups.Keys) {
    $exists = (& az group exists --name $groupName --output tsv 2>$null)
    if ($LASTEXITCODE -ne 0) { throw "No se pudo verificar $groupName; no se eliminó nada." }
    if ($exists.Trim().ToLowerInvariant() -eq 'false') { continue }

    $group = Invoke-AzJson @(
        'group', 'show', '--name', $groupName,
        '--query', '{name:name,project:tags.Project,state:properties.provisioningState}', '--output', 'json'
    )
    if ($group.name -cne $groupName -or $group.project -cne $expectedGroups[$groupName]) {
        throw "Las etiquetas de $groupName no coinciden con el proyecto esperado; no se eliminó nada."
    }
    if ($group.state -eq 'Deleting') {
        $resourceCount = -1
    } else {
        $resourceJson = (& az resource list --resource-group $groupName --output json 2>$null)
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo inventariar $groupName; no se eliminó nada."
        }
        $resourceCount = @($resourceJson | ConvertFrom-Json).Count
    }
    $targets += [pscustomobject]@{ Name = $groupName; ResourceCount = $resourceCount }
}

if ($targets.Count -eq 0) {
    Write-Output 'No quedan grupos de recursos del proyecto en la suscripción verificada.'
    exit 0
}

Write-Host "Suscripción verificada: $ExpectedSubscriptionId"
Write-Host 'Grupos que se eliminarán y cantidad de recursos inventariados:'
$targets | Format-Table -AutoSize | Out-Host
Write-Host 'La base, los servicios, las redes, las claves de Key Vault y el backend remoto de Terraform quedarán eliminados.'
if ($Confirmation -cne $confirmationPhrase) {
    throw "Confirmación incorrecta. No se eliminó nada. La frase requerida es: $confirmationPhrase"
}

# Remove the state backend last. Start compute and network deletion without
# waiting between groups so a slow VPN gateway does not keep the portal running.
$nonStateNames = @(
    'rg-tangama-wg-hub-eus',
    'rg-tangama-private-network',
    'rg-tangamandapio-rebuild-wus'
)
$stateGroupName = 'rg-tangamandapio-tfstate-wus'
$pendingNames = @()
foreach ($groupName in $nonStateNames) {
    if ($targets.Name -notcontains $groupName) { continue }
    $state = (& az group show --name $groupName --query properties.provisioningState --output tsv 2>$null)
    if ($LASTEXITCODE -ne 0 -and $state -notmatch 'ResourceGroupNotFound') {
        throw "No se pudo comprobar el estado de $groupName antes de borrar."
    }
    if ($state -eq 'Deleting') {
        Write-Host "Eliminación ya iniciada: $groupName"
        $pendingNames += $groupName
        continue
    }
    Write-Host "Iniciando eliminación de $groupName..."
    & az group delete --name $groupName --yes --no-wait
    if ($LASTEXITCODE -ne 0) { throw "Azure no aceptó la eliminación de $groupName. Revise el estado antes de continuar." }
    $pendingNames += $groupName
}

foreach ($groupName in $pendingNames) {
    $deadline = [DateTime]::UtcNow.AddHours(2)
    do {
        Start-Sleep -Seconds 10
        $exists = (& az group exists --name $groupName --output tsv 2>$null)
        if ($LASTEXITCODE -ne 0) { throw "No se pudo verificar el borrado de $groupName." }
    } while ($exists.Trim().ToLowerInvariant() -ne 'false' -and [DateTime]::UtcNow -lt $deadline)
    if ($exists.Trim().ToLowerInvariant() -ne 'false') {
        throw "Azure todavía reporta $groupName; se detuvo el borrado para revisar el estado."
    }
    Write-Host "Eliminado: $groupName"
}

if ($targets.Name -contains $stateGroupName) {
    $exists = (& az group exists --name $stateGroupName --output tsv 2>$null)
    if ($LASTEXITCODE -ne 0) { throw "No se pudo verificar el backend $stateGroupName." }
    if ($exists.Trim().ToLowerInvariant() -ne 'false') {
        Write-Host "Eliminando al final el backend remoto $stateGroupName..."
        & az group delete --name $stateGroupName --yes --no-wait
        if ($LASTEXITCODE -ne 0) { throw "Azure no aceptó la eliminación de $stateGroupName." }
        $deadline = [DateTime]::UtcNow.AddHours(2)
        do {
            Start-Sleep -Seconds 10
            $exists = (& az group exists --name $stateGroupName --output tsv 2>$null)
            if ($LASTEXITCODE -ne 0) { throw "No se pudo verificar el borrado de $stateGroupName." }
        } while ($exists.Trim().ToLowerInvariant() -ne 'false' -and [DateTime]::UtcNow -lt $deadline)
        if ($exists.Trim().ToLowerInvariant() -ne 'false') {
            throw "Azure todavía reporta $stateGroupName; verifique el estado del backend."
        }
    }
    Write-Host "Eliminado: $stateGroupName"
}

$remainingGroups = @(Invoke-AzJson @(
    'group', 'list',
    '--query', "[?tags.Project=='Tangamandapio-Cloud' || tags.Project=='Tangamandapio'].name",
    '--output', 'json'
))
$remainingResources = @(Invoke-AzJson @(
    'resource', 'list',
    '--query', "[?tags.Project=='Tangamandapio-Cloud' || tags.Project=='Tangamandapio'].{group:resourceGroup,name:name}",
    '--output', 'json'
))
if ($remainingGroups.Count -gt 0 -or $remainingResources.Count -gt 0) {
    throw "Verificación incompleta: quedan $($remainingGroups.Count) grupos y $($remainingResources.Count) recursos etiquetados del proyecto."
}

Write-Output "AZURE_PROJECT_CLEANUP_COMPLETE subscription=$ExpectedSubscriptionId project_resource_groups=0 project_tagged_resources=0"
