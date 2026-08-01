output "web_vm_public_ip" {
  value = oci_core_instance.web_vm.public_ip
}

output "app_vm_public_ip" {
  value = oci_core_instance.app_vm.public_ip
}

output "bucket_name" {
  value = oci_objectstorage_bucket.photos_bucket.name
}