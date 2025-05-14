locals {
  orcl_serv_cidr    = lookup(data.oci_core_services.all_oci_services.services[0], "cidr_block")
  orcl_serv_name    = lookup(data.oci_core_services.all_oci_services.services[0], "name")
  orcl_all_serv_id  = lookup(data.oci_core_services.all_oci_services.services[0], "id")
  is_sn_private     = data.oci_core_subnet.subnet.prohibit_public_ip_on_vnic  
}

data "oci_core_services" "all_oci_services" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

data "oci_core_subnet" "subnet" {
    #Required
    subnet_id = var.use_existent_vcn ? var.subnet_id : oci_core_subnet.subnets[0].id
}


resource "oci_core_virtual_network" "vcn" {
  count          = var.use_existent_vcn ? 0 : 1
  cidr_block     = var.vcn_cidr
  compartment_id = var.compartment_ocid
  display_name   = var.vcn_name
  dns_label      = var.dns_label
}

resource "oci_core_internet_gateway" "igw" {
  count             = var.use_existent_vcn ? 0 : 1
  compartment_id    = oci_core_virtual_network.vcn[0].compartment_id
  vcn_id            = oci_core_virtual_network.vcn[0].id
  display_name      = "igw_gpu"
}

#resource "oci_core_nat_gateway" "ngw" {
#  count          = var.use_existent_vcn ? 0 : 1
#  compartment_id = oci_core_virtual_network.vcn[0].compartment_id
#  vcn_id         = oci_core_virtual_network.vcn[0].id
#  display_name   = "ngw_gpu"
#}

#esource "oci_core_service_gateway" "this" {
# count          = var.use_existent_vcn ? 0 : 1
# compartment_id = oci_core_virtual_network.vcn[0].compartment_id
# services {
#   service_id = local.orcl_all_serv_id
# }
# vcn_id       = oci_core_virtual_network.vcn[0].id
# display_name = ""
#

resource "oci_core_subnet" "subnets" {
  count                       = var.use_existent_vcn ? 0 : 1
  cidr_block                  = cidrsubnet(var.vcn_cidr, 8, 1)
  display_name                = "sngpu"
  #prohibit_public_ip_on_vnic  = var.is_subnet_private
  prohibit_public_ip_on_vnic  = false
  compartment_id              = oci_core_virtual_network.vcn[0].compartment_id
  vcn_id                      = oci_core_virtual_network.vcn[0].id
  route_table_id             = oci_core_route_table.route_table[0].id
  security_list_ids          = [oci_core_security_list.sl[0].id]
}


resource "oci_core_route_table" "route_table" {
  count                       = var.use_existent_vcn ? 0 : 1
  compartment_id = oci_core_virtual_network.vcn[0].compartment_id
  vcn_id         = oci_core_virtual_network.vcn[0].id
  display_name   = "rt_gpu"

  route_rules {
      destination       = "0.0.0.0/0"
      destination_type  =  null
      network_entity_id =  oci_core_internet_gateway.igw[0].id
    }
}

resource "oci_core_security_list" "sl" {
  count          = var.use_existent_vcn ? 0 : 1
  compartment_id = oci_core_virtual_network.vcn[0].compartment_id
  vcn_id         = oci_core_virtual_network.vcn[0].id
  display_name   = "sl_gpu"

  egress_security_rules {
      protocol    = "all"
      destination = "0.0.0.0/0"
  }

  ingress_security_rules {
      protocol    = "all"
      source      = var.allow_ingress_from
      source_type = "CIDR_BLOCK"       
  }
}

