$script:RepoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$script:LifecycleScript = Join-Path $script:RepoRoot 'iac\environments\azure-rebuild\lifecycle.ps1'

function global:Read-Host {
    param([string]$Prompt)
    return 'BOOTSTRAP STATE'
}

function global:TestTerraform {
    $arguments = @($args)
    $rootArgument = $arguments | Where-Object { $_ -like '-chdir=*' } | Select-Object -First 1
    if (-not $rootArgument) {
        $global:LASTEXITCODE = 2
        return
    }

    $root = $rootArgument.Substring(7)
    $terraformArguments = @($arguments | Where-Object { $_ -notlike '-chdir=*' })
    $operation = $terraformArguments | Where-Object { $_ -notlike '-*' } | Select-Object -First 1
    if ($operation -eq 'state' -and $terraformArguments.Count -gt 1) {
        $operation += " $($terraformArguments[1])"
    }
    Add-Content -LiteralPath $env:TANGAMA_TERRAFORM_LOG -Value "$operation|$root|$($terraformArguments -join '|')"

    if ($operation -eq 'plan' -and (Test-Path -LiteralPath (Join-Path $root 'backend.tf'))) {
        $global:LASTEXITCODE = 1
        return
    }

    if ($operation -eq 'plan') {
        $planArgument = $terraformArguments | Where-Object { $_ -like '-out=*' } | Select-Object -First 1
        if ($planArgument) {
            Set-Content -LiteralPath $planArgument.Substring(5) -Value 'test-plan'
        }
    }
    elseif ($operation -eq 'apply') {
        @'
{"version":4,"resources":[
 {"type":"azurerm_resource_group","name":"state","instances":[{"attributes":{"name":"rg-tangamandapio-tfstate-wus"}}]},
 {"type":"azurerm_storage_account","name":"state","instances":[{"attributes":{"name":"sttangamatfstate261014","resource_group_name":"rg-tangamandapio-tfstate-wus"}}]},
 {"type":"azurerm_role_assignment","name":"backend_writer","instances":[{"attributes":{"role_definition_name":"Storage Blob Data Contributor"}}]},
 {"type":"azurerm_storage_container","name":"state","instances":[{"attributes":{"name":"tfstate"}}]}
]}
'@ | Set-Content -LiteralPath (Join-Path $root 'terraform.tfstate')
    }
    elseif ($operation -eq 'state push') {
        if ($terraformArguments.Count -lt 3 -or -not (Test-Path -LiteralPath $terraformArguments[2])) {
            $global:LASTEXITCODE = 1
            return
        }
    }
    elseif ($operation -eq 'state list') {
        Write-Output 'azurerm_resource_group.state'
    }

    $global:LASTEXITCODE = 0
}

Describe 'Azure bootstrap-state lifecycle' {
    It 'creates backend state without planning against a stale remote backend' {
        $tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("tangama-bootstrap-test-" + [guid]::NewGuid().ToString('N'))
        $fakeBin = Join-Path $tempRoot 'bin'
        New-Item -ItemType Directory -Force -Path $fakeBin | Out-Null
        $oldPath = $env:PATH
        $oldTerraformLog = $env:TANGAMA_TERRAFORM_LOG
        $oldGroupExists = $env:TANGAMA_AZ_GROUP_EXISTS
        $env:PATH = "$fakeBin;$oldPath"
        $env:TANGAMA_TERRAFORM_LOG = Join-Path $tempRoot 'terraform.log'
        $env:TANGAMA_AZ_GROUP_EXISTS = 'false'
        @'
@echo off
if "%1"=="account" if "%2"=="show" echo 1480b165-7420-4bed-a201-5ecadd7104d0
if "%1"=="group" if "%2"=="exists" if "%TANGAMA_AZ_GROUP_EXISTS%"=="true" (echo true) else (echo false)
exit /b 0
'@ | Set-Content -LiteralPath (Join-Path $fakeBin 'az.cmd') -Encoding Ascii

        $failure = $null
        try {
            & $script:LifecycleScript bootstrap-state `
                -ExpectedSubscriptionId '1480b165-7420-4bed-a201-5ecadd7104d0' `
                -TerraformPath 'TestTerraform' 2>&1 | Out-Null
        }
        catch {
            $failure = $_.Exception.Message
        }

        $operations = @(Get-Content -LiteralPath $env:TANGAMA_TERRAFORM_LOG -ErrorAction SilentlyContinue)
        $tempPlans = @($operations | Where-Object { $_ -match '^plan\|' })
        $statePush = @($operations | Where-Object { $_ -match '^state push\|' })
        $stateList = @($operations | Where-Object { $_ -match '^state list\|' })

        $failure | Should Be $null
        $tempPlans.Count | Should Be 1
        (Test-Path -LiteralPath (Join-Path (($tempPlans[0] -split '\|')[1]) 'backend.tf')) | Should Be $false
        $statePush.Count | Should Be 1
        $stateList.Count | Should Be 1

        $env:PATH = $oldPath
        $env:TANGAMA_TERRAFORM_LOG = $oldTerraformLog
        $env:TANGAMA_AZ_GROUP_EXISTS = $oldGroupExists
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }

    It 'resumes a created backend from the retained local state after a partial bootstrap' {
        $tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("tangama-bootstrap-resume-test-" + [guid]::NewGuid().ToString('N'))
        $fakeBin = Join-Path $tempRoot 'bin'
        $recoveryRoot = Join-Path ([IO.Path]::GetTempPath()) ("tangamandapio-tfstate-" + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Force -Path $fakeBin, $recoveryRoot | Out-Null
        $oldPath = $env:PATH
        $oldTerraformLog = $env:TANGAMA_TERRAFORM_LOG
        $oldGroupExists = $env:TANGAMA_AZ_GROUP_EXISTS
        $env:PATH = "$fakeBin;$oldPath"
        $env:TANGAMA_TERRAFORM_LOG = Join-Path $tempRoot 'terraform.log'
        $env:TANGAMA_AZ_GROUP_EXISTS = 'true'
        @'
@echo off
if "%1"=="account" if "%2"=="show" echo 1480b165-7420-4bed-a201-5ecadd7104d0
if "%1"=="group" if "%2"=="exists" if "%TANGAMA_AZ_GROUP_EXISTS%"=="true" (echo true) else (echo false)
exit /b 0
'@ | Set-Content -LiteralPath (Join-Path $fakeBin 'az.cmd') -Encoding Ascii

        $recoveryState = Join-Path $recoveryRoot 'terraform.tfstate'
        @'
{"version":4,"resources":[
 {"type":"azurerm_resource_group","name":"state","instances":[{"attributes":{"name":"rg-tangamandapio-tfstate-wus"}}]},
 {"type":"azurerm_storage_account","name":"state","instances":[{"attributes":{"name":"sttangamatfstate261014","resource_group_name":"rg-tangamandapio-tfstate-wus"}}]},
 {"type":"azurerm_role_assignment","name":"backend_writer","instances":[{"attributes":{"role_definition_name":"Storage Blob Data Contributor"}}]},
 {"type":"azurerm_storage_container","name":"state","instances":[{"attributes":{"name":"tfstate"}}]}
]}
'@ | Set-Content -LiteralPath $recoveryState -Encoding Ascii

        $failure = $null
        try {
            & $script:LifecycleScript bootstrap-state `
                -ExpectedSubscriptionId '1480b165-7420-4bed-a201-5ecadd7104d0' `
                -TerraformPath 'TestTerraform' `
                -BootstrapStatePath $recoveryState 2>&1 | Out-Null
        }
        catch {
            $failure = $_.Exception.Message
        }

        $operations = @(Get-Content -LiteralPath $env:TANGAMA_TERRAFORM_LOG -ErrorAction SilentlyContinue)
        $statePush = @($operations | Where-Object { $_ -match '^state push\|' })
        $stateList = @($operations | Where-Object { $_ -match '^state list\|' })
        $failure | Should Be $null
        $statePush.Count | Should Be 1
        $stateList.Count | Should Be 1
        (Test-Path -LiteralPath $recoveryRoot) | Should Be $false

        $env:PATH = $oldPath
        $env:TANGAMA_TERRAFORM_LOG = $oldTerraformLog
        $env:TANGAMA_AZ_GROUP_EXISTS = $oldGroupExists
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
