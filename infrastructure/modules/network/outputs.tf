# infrastructure/modules/network/outputs.tf

output "vcn_id" {
  description = "OCID of the created VCN"
  value       = oci_core_vcn.avosoft_vcn.id
}

output "public_subnet_id" {
  description = "OCID of the public subnet"
  value       = oci_core_subnet.public_subnet.id
}

output "internet_gateway_id" {
  description = "OCID of the internet gateway"
  value       = oci_core_internet_gateway.internet_gateway.id
}

output "security_list_id" {
  description = "OCID of the security list"
  value       = oci_core_security_list.public_security_list.id
}