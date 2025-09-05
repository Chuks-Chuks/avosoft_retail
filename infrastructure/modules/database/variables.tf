variable "aws_db_user" {
  description = "Username for the master DB user"
  type        = string
  sensitive   = true
}

variable "aws_db_password" {
  description = "Password for the master DB user"
  type        = string
  sensitive   = true
}

variable "aws_db_name" {
  description = "The name of the database to create"
  type        = string
  default     = "avosoft_retail"
}

variable "publicly_accessible" {
  description = "Whether the database should be publicly accessible"
  type        = bool
  default     = true
}


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