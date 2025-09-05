# infrastructure/modules/compute/variables.tf

variable "compartment_id" {
  description = "The OCID of the compartment"
  type        = string
}

variable "subnet_id" {
  description = "The OCID of the subnet to create the VNIC in"
  type        = string
}

variable "availability_domain" {
  description = "The availability domain for the instance"
  type        = string
}

# ADD THESE NEW VARIABLES FOR AWS DATABASE CONNECTION
variable "db_host" {
  description = "AWS RDS endpoint hostname"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "AWS PostgreSQL database name"
  type        = string
}

variable "db_user" {
  description = "AWS PostgreSQL database user"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "AWS PostgreSQL database password"
  type        = string
  sensitive   = true
}