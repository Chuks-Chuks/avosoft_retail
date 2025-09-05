# infrastructure/providers.tf

terraform {
  required_version = ">= 1.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
  }
}

# OCI Provider Configuration
provider "oci" {
  tenancy_ocid     = var.oci_tenancy_ocid
  user_ocid        = var.oci_user_ocid
  private_key_path = var.oci_private_key_path
  fingerprint      = var.oci_fingerprint
  region           = var.oci_region
}

# AWS Provider Configuration (for S3)
provider "aws" {
  region = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}
