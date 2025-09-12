# avosoft_retail/infrastructure/main.tf


# Call network module
module "network" {
  source = "./modules/network"

  compartment_id    = var.compartment_id
  region           = var.oci_region
  vcn_cidr_block   = var.vcn_cidr_block
  public_subnet_cidr = var.public_subnet_cidr
}

# Add these to your existing main.tf

module "database" {
  source = "./modules/database"

  aws_access_key     = var.aws_access_key
  aws_secret_key     = var.aws_secret_key
  aws_db_user        = var.aws_db_user
  aws_db_password    = var.aws_db_password
  aws_db_name        = var.aws_db_name
  publicly_accessible = true # Set to false for production
}

module "compute" {
  source = "./modules/compute"
  
  compartment_id     = var.compartment_id
  subnet_id          = module.network.public_subnet_id
  availability_domain = data.oci_identity_availability_domain.ad.name
  
  # Add these new variables for AWS database connection
  aws_db_host     = module.database.rds_address
  aws_db_name     = var.aws_db_name
  aws_db_user     = var.aws_db_user
  aws_db_password = var.aws_db_password
}


# Get availability domain
data "oci_identity_availability_domain" "ad" {
  compartment_id = var.oci_tenancy_ocid
  ad_number      = 1
}