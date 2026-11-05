mock_provider "azurerm" {}

run "pilot_has_no_public_inbound_or_cloud_routes" {
  command = plan
  variables {
    subscription_id = "1480b165-7420-4bed-a201-5ecadd7104d0"
    ssh_public_key  = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA dummy"
  }
  assert {
    condition     = azurerm_network_security_rule.deny_inbound.direction == "Inbound" && azurerm_network_security_rule.deny_inbound.access == "Deny" && azurerm_network_security_rule.deny_inbound.source_address_prefix == "*"
    error_message = "The pilot must explicitly deny unsolicited inbound traffic."
  }
  assert {
    condition     = azurerm_network_interface.router.ip_forwarding_enabled
    error_message = "The subnet router NIC must support forwarding."
  }
}

run "backup_has_distinct_resource_names" {
  command = plan
  variables {
    subscription_id = "1480b165-7420-4bed-a201-5ecadd7104d0"
    ssh_public_key  = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA dummy"
    name_suffix     = "backup"
  }
  assert {
    condition     = azurerm_linux_virtual_machine.router.name == "vm-tangama-ts-backup"
    error_message = "The backup must have its own VM name."
  }
  assert {
    condition     = azurerm_public_ip.router.name == "pip-tangama-tailscale-backup"
    error_message = "The backup must have its own public IP name."
  }
}
