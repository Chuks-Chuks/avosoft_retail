# Assuming you have AWS provider configured already


# Data source to reference your EXISTING security group
data "aws_security_group" "existing" {
  name = "avosoft-server-sg" 
}

# Create AWS PostgreSQL RDS instance using existing security group
resource "aws_db_instance" "avosoft_db" {
  identifier             = "avosoft-retail-db"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "15"
  username               = var.aws_db_user
  password               = var.aws_db_password
  db_name                = var.aws_db_name
  parameter_group_name   = "default.postgres15"
  skip_final_snapshot    = true
  publicly_accessible    = var.publicly_accessible
  vpc_security_group_ids = [var.security_group_id]
  
  tags = {
    Name = "avosoft-retail-database"
    Environment = "Production"
  }
}

# Output the connection details for OCI configuration
output "rds_endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = aws_db_instance.avosoft_db.endpoint
  sensitive   = true
}

output "rds_address" {
  description = "The hostname of the RDS instance"
  value       = aws_db_instance.avosoft_db.address
  sensitive   = true
}

output "rds_port" {
  description = "The database port"
  value       = aws_db_instance.avosoft_db.port
}