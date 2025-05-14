output "VM_PUB_IP" {
	value = oci_core_instance.this.public_ip
}

output "VM_PRIV_IP" {
  value = oci_core_instance.this.private_ip
}
