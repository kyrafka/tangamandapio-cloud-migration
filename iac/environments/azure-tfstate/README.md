# Azure Terraform state backend

This isolated bootstrap root provisions a dedicated, low-cost Standard LRS
storage account outside the WMS resource group. The state container is private;
shared-key authorization and anonymous blob access are disabled. Access uses
Microsoft Entra ID and the `Storage Blob Data Contributor` role. Blob versioning
and 30-day blob/container soft delete protect recovery. `prevent_destroy` guards
the resource group, account and state container against accidental teardown.

The bootstrap root initially has a local state so it can create the account
that stores Terraform state. That state can contain sensitive provider
attributes (including storage-account credentials), so it must never be
committed or printed. After the first apply, this root migrates its state to
`azure-tfstate-bootstrap.tfstate` in the protected remote container. Keep the
pre-migration local state and backup as restricted recovery artifacts until
the remote copy is independently verified.

The storage account uses its public endpoint so the authorized operator can run
Terraform from the workstation. The container is not public and the backend
uses Entra authentication, not an account key. A private endpoint/firewall
allow-list is a future hardening step once a stable private runner or VPN exists.

## Bootstrap and verification

From this directory, authenticate to the intended Azure for Students
subscription. For normal operation, the remote backend should already exist:

```powershell
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
```

For a genuinely fresh rebuild where the backend account does not exist, use a
clean checkout with no local state file and bootstrap locally first:

```powershell
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
terraform plan -out=tfstate-bootstrap.tfplan
terraform show -no-color tfstate-bootstrap.tfplan
terraform apply tfstate-bootstrap.tfplan
terraform init -migrate-state -force-copy
```

Review the saved plan before applying. It must create only this dedicated
resource group, storage account, role assignment and private container. Do not
apply a plan containing deletion or replacement of existing WMS resources.

After the bootstrap is verified, migrate this root with
`terraform init -migrate-state`. Then migrate the existing `azure-rebuild` root
with the same command; it uses its own key, `azure-rebuild.tfstate`. For both
roots, verify the blob exists through Entra-authenticated access, run
`terraform state list` without exposing state contents, and require a normal
plan to report `No changes`. Keep all pre-migration state and backup files
restricted and ignored by Git until remote state and recovery procedures are
verified. Never use `terraform state pull` in a shared or logged terminal.

The backend account keeps its public blob endpoint enabled for access from the
authorized workstation, but its container is private and anonymous access,
shared-key auth, local users, and cross-tenant replication are disabled. Access
is authorized by Entra ID and scoped RBAC. A private endpoint/firewall allowlist
is a future hardening step once a stable private runner or VPN exists.
