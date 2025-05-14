provider "oci" {}

resource "tls_private_key" "public_private_key_pair" {
  algorithm = "RSA"
}

data "oci_core_images" "gpu_images" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "8"
  shape                    = var.shape
  state                    = "AVAILABLE"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"

  filter {
    name   = "launch_mode"
    values = ["NATIVE"]
  }
  filter {
    name = "display_name"
    values = ["\\w*GPU\\w*"]
    regex = true
  }
}

resource "oci_core_instance" "this" {
	agent_config {
		is_management_disabled = "false"
		is_monitoring_disabled = "false"
		plugins_config {
			desired_state = "DISABLED"
			name = "Vulnerability Scanning"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "Oracle Java Management Service"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "OS Management Service Agent"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "OS Management Hub Agent"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "Management Agent"
		}
		plugins_config {
			desired_state = "ENABLED"
			name = "Custom Logs Monitoring"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "Compute RDMA GPU Monitoring"
		}
		plugins_config {
			desired_state = "ENABLED"
			name = "Compute Instance Run Command"
		}
		plugins_config {
			desired_state = "ENABLED"
			name = "Compute Instance Monitoring"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "Compute HPC RDMA Auto-Configuration"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "Compute HPC RDMA Authentication"
		}
		plugins_config {
			desired_state = "ENABLED"
			name = "Cloud Guard Workload Protection"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "Block Volume Management"
		}
		plugins_config {
			desired_state = "DISABLED"
			name = "Bastion"
		}
	}

	availability_config {
		is_live_migration_preferred = "false"
		recovery_action = "RESTORE_INSTANCE"
	}

	availability_domain = var.ad
	compartment_id = var.compartment_ocid
	
	create_vnic_details {
		assign_ipv6ip = "false"
		assign_private_dns_record = "true"
		#assign_public_ip =  "true"
		assign_public_ip = local.is_sn_private ? "false" : "true"
		subnet_id = var.use_existent_vcn ? var.subnet_id : oci_core_subnet.subnets[0].id
	}
	
	display_name = var.vm_display_name
	
	instance_options {
		are_legacy_imds_endpoints_disabled = "false"
	}
	
	# does not works for BM
	is_pv_encryption_in_transit_enabled = length(regexall("BM",var.shape)) > 0 ? false : true
	
	metadata = {
		ssh_authorized_keys = tls_private_key.public_private_key_pair.public_key_openssh
		user_data           = data.cloudinit_config.config.rendered
	}
	shape = var.shape
	source_details {
		boot_volume_size_in_gbs = "250"
		boot_volume_vpus_per_gb = "10"
		source_id = data.oci_core_images.gpu_images.images[0].id
		source_type = "image"
	}
	freeform_tags = {"GPU_TAG" = var.gpu_tag_val}
}



