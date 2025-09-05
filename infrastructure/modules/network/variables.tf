# infrastructure/modules/network/variables.tf

variable "compartment_id" {
  description = "OCI Compartment ID"
  type        = string
}

variable "vcn_cidr_block" {
  description = "CIDR block for the VCN"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "region" {
  description = "OCI region"
  type        = string
}