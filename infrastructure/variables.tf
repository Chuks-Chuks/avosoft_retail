# infrastructure/variables.tf

# OCI Variables
variable "oci_tenancy_ocid" {
  description = "OCI Tenancy OCID"
  type        = string
}

variable "oci_user_ocid" {
  description = "OCI User OCID"
  type        = string
}

variable "oci_private_key_path" {
  description = "Path to OCI private key"
  type        = string
  default     = "~/.oci/oci_api_key.pem"
}

variable "oci_fingerprint" {
  description = "OCI API key fingerprint"
  type        = string
}

variable "oci_region" {
  description = "OCI region"
  type        = string
  default     = "uk-london-1"
}

variable "compartment_id" {
  description = "Compartment OCID"
  type        = string
}

# AWS Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "aws_access_key" {
  description = "AWS access key"
  type        = string
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS secret key"
  type        = string
  sensitive   = true
}

# Network Variables
variable "vcn_cidr_block" {
  description = "VCN CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Public subnet CIDR block"
  type        = string
  default     = "10.0.1.0/24"
}



variable "aws_db_name" {
  description = "AWS PostgreSQL database name"
  type        = string
}

variable "aws_db_user" {
  description = "AWS PostgreSQL database user"
  type        = string
  sensitive   = true
}

variable "aws_db_password" {
  description = "AWS PostgreSQL database password"
  type        = string
  sensitive   = true
}
