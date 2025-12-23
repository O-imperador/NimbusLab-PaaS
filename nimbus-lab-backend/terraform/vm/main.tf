terraform {
  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"
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

variable "vm_name" {}
variable "vm_password" {}

resource "proxmox_vm_qemu" "ubuntu_vm" {
  name      = var.vm_name
  target_node = "proxhost"
  cores     = 2
  memory    = 2048
  scsihw    = "virtio-scsi-pci"
  boot      = "cdn"

  os_type   = "cloud-init"
  iso       = "local:iso/jammy-server-cloudimg-amd64.img"

  network {
    model = "virtio"
    bridge = "vmbr0"
  }

  disk {
    size = "8G"
    type = "scsi"
    storage = "local-lvm"
  }

  ssh_user     = "ubuntu"
  ssh_password = var.vm_password

  ciuser  = "ubuntu"
  cipassword = var.vm_password

  lifecycle {
    ignore_changes = [network]
  }
}
