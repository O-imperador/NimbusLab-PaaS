terraform {
  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"   # Correct provider source
      version = "2.9.9"
    }
  }
}

variable "proxmox_api_url" {
  description = "Proxmox API URL"
  type        = string
}

variable "proxmox_api_token_id" {
  description = "Proxmox API Token ID (or root@pam)"
  type        = string
}

variable "proxmox_api_token_secret" {
  description = "Proxmox API Token Secret (or password)"
  type        = string
  sensitive   = true
}

provider "proxmox" {
  pm_api_url      = var.proxmox_api_url
  pm_user         = var.proxmox_api_token_id
  pm_password     = var.proxmox_api_token_secret
  pm_tls_insecure = true
}


resource "proxmox_lxc" "ubuntu_lxc" {
  target_node = "proxhost"
  hostname    = var.lxc_name
  password    = var.lxc_password
  cores       = 2
  memory      = 2048
  unprivileged = true

  ostemplate = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"

  rootfs {
    storage = "local-lvm"
    size    = "8G"
  }

  features {
    nesting = true
    fuse    = true
  }

  network {
    name   = "eth0"
    bridge = "vmbr0"
    ip     = "dhcp"
  }
}
