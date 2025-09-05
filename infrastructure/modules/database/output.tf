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