variable "subscription_id" { type = string }
variable "ssh_public_key" { type = string }
variable "name_suffix" {
  type    = string
  default = "pilot"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,11}$", var.name_suffix))
    error_message = "Use a short lowercase resource name suffix."
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

data "azurerm_resource_group" "network" {
  name = "rg-tangama-private-network"
}

data "azurerm_subnet" "workloads" {
  name                 = "snet-private-workloads"
  virtual_network_name = "vnet-tangama-private"
  resource_group_name  = data.azurerm_resource_group.network.name
}

locals {
  tags = { Project = "Tangamandapio", Purpose = "TailscalePilot", ManagedBy = "Terraform" }
}

resource "azurerm_network_security_group" "router" {
  name                = "nsg-tangama-tailscale-${var.name_suffix}"
  location            = data.azurerm_resource_group.network.location
  resource_group_name = data.azurerm_resource_group.network.name
  tags                = local.tags
}

resource "azurerm_network_security_rule" "deny_inbound" {
  name                        = "deny-inbound-pilot"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = data.azurerm_resource_group.network.name
  network_security_group_name = azurerm_network_security_group.router.name
}

resource "azurerm_public_ip" "router" {
  name                = "pip-tangama-tailscale-${var.name_suffix}"
  location            = data.azurerm_resource_group.network.location
  resource_group_name = data.azurerm_resource_group.network.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}

resource "azurerm_network_interface" "router" {
  name                  = "nic-tangama-tailscale-${var.name_suffix}"
  location              = data.azurerm_resource_group.network.location
  resource_group_name   = data.azurerm_resource_group.network.name
  ip_forwarding_enabled = true
  ip_configuration {
    name                          = "internal"
    subnet_id                     = data.azurerm_subnet.workloads.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.router.id
  }
  tags = local.tags
}

resource "azurerm_network_interface_security_group_association" "router" {
  network_interface_id      = azurerm_network_interface.router.id
  network_security_group_id = azurerm_network_security_group.router.id
}

resource "azurerm_linux_virtual_machine" "router" {
  name                            = "vm-tangama-ts-${var.name_suffix}"
  location                        = data.azurerm_resource_group.network.location
  resource_group_name             = data.azurerm_resource_group.network.name
  size                            = "Standard_B2pts_v2"
  admin_username                  = "tangamaadmin"
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.router.id]
  admin_ssh_key {
    username   = "tangamaadmin"
    public_key = var.ssh_public_key
  }
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-arm64"
    version   = "latest"
  }
  tags       = local.tags
  depends_on = [azurerm_network_interface_security_group_association.router, azurerm_network_security_rule.deny_inbound]
}

output "router_name" { value = azurerm_linux_virtual_machine.router.name }
output "router_private_ip" { value = azurerm_network_interface.router.private_ip_address }
