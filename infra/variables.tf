variable "tenancy_ocid" { type = string }
variable "user_ocid" { type = string }
variable "fingerprint" { type = string }
variable "private_key" { type = string }
variable "region" { type = string }
variable "compartment_ocid" { type = string }
variable "ssh_public_key" { type = string }
variable "bucket_name" {
  type    = string
  default = "goa-trip-memories-bucket"
}