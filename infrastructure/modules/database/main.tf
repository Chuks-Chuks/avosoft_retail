resource "aws_security_group" "db_sg" {
  name_prefix = "avosoft-db-sg"
  description = "Security group for Avosoft RDS database"

  # Allow PostgreSQL access from ANYWHERE (you can restrict this later)
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allows from anywhere - okay for testing
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "avosoft-database-sg"
  }
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
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  
  tags = {
    Name = "avosoft-retail-database"
    Environment = "Production"
  }
}
