terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# --- VCN & Networking ---
resource "oci_core_vcn" "goa_vcn" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "GoaTrip-VCN"
  dns_label      = "goavcn"
}

resource "oci_core_internet_gateway" "goa_ig" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.goa_vcn.id
  display_name   = "GoaTrip-IG"
}

resource "oci_core_route_table" "goa_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.goa_vcn.id
  display_name   = "GoaTrip-RT"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.goa_ig.id
  }
}

# --- Network Security Group (NSG) ---
resource "oci_core_network_security_group" "goa_nsg" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.goa_vcn.id
  display_name   = "GoaTrip-NSG"
}

# Ingress: SSH (22)
resource "oci_core_network_security_group_security_rule" "ssh" {
  network_security_group_id = oci_core_network_security_group.goa_nsg.id
  direction                 = "INGRESS"
  protocol                  = "6" # TCP
  source                    = "0.0.0.0/0"
  tcp_options {
    destination_port_range { min = 22, max = 22 }
  }
}

# Ingress: HTTP (80)
resource "oci_core_network_security_group_security_rule" "http" {
  network_security_group_id = oci_core_network_security_group.goa_nsg.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  tcp_options {
    destination_port_range { min = 80, max = 80 }
  }
}

# Ingress: Backend App API (5000)
resource "oci_core_network_security_group_security_rule" "app_port" {
  network_security_group_id = oci_core_network_security_group.goa_nsg.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  tcp_options {
    destination_port_range { min = 5000, max = 5000 }
  }
}

# Egress: Allow all outgoing traffic
resource "oci_core_network_security_group_security_rule" "egress" {
  network_security_group_id = oci_core_network_security_group.goa_nsg.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
}

# --- Subnet ---
resource "oci_core_subnet" "goa_subnet" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.goa_vcn.id
  cidr_block                 = "10.0.1.0/24"
  display_name               = "GoaTrip-Subnet"
  route_table_id             = oci_core_route_table.goa_rt.id
  prohibit_public_ip_on_vnic = false
}

# --- Ubuntu 22.04 Image Data Source ---
data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.E4.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# --- VM 1: Web Server ---
resource "oci_core_instance" "web_vm" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "Goa-Web-VM"
  shape               = "VM.Standard.E4.Flex"

  shape_config {
    ocpus         = 1
    memory_in_gbs = 4
  }

  create_vnic_details {
    subnet_id              = oci_core_subnet.goa_subnet.id
    assign_public_ip       = true
    nsg_ids                = [oci_core_network_security_group.goa_nsg.id]
    display_name           = "web-vnic"
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }
}

# --- VM 2: App & DB Server ---
resource "oci_core_instance" "app_vm" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "Goa-AppDB-VM"
  shape               = "VM.Standard.E4.Flex"

  shape_config {
    ocpus         = 1
    memory_in_gbs = 4
  }

  create_vnic_details {
    subnet_id              = oci_core_subnet.goa_subnet.id
    assign_public_ip       = true
    nsg_ids                = [oci_core_network_security_group.goa_nsg.id]
    display_name           = "app-vnic"
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }
}

# --- Object Storage Bucket ---
data "oci_objectstorage_namespace" "ns" {
  compartment_id = var.compartment_ocid
}

resource "oci_objectstorage_bucket" "photos_bucket" {
  compartment_id = var.compartment_ocid
  name           = var.bucket_name
  namespace      = data.oci_objectstorage_namespace.ns.value
  access_type    = "ObjectRead" # Publicly readable for images
}