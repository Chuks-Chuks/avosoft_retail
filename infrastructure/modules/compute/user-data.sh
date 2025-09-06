#!/bin/bash
# Update and install required packages
apt-get update
apt-get install -y python3-pip git postgresql-client

# Clone your repository
git clone https://github.com/Chuks-Chuks/avosoft_retail.git /opt/avosoft_retail

# Install Python dependencies
pip3 install -r /opt/avosoft_retail/requirements.txt

# Create a directory for application logs
mkdir -p /var/log/avosoft
chmod 755 /var/log/avosoft

# Create an environment file for the application
# NOTE: For production, use a secrets manager or inject these another way.
cat > /opt/avosoft_retail/.env << EOL
DB_HOST=${db_host}
DB_PORT=5432
DB_NAME=${db_name}
DB_USER=${db_user}
DB_PASSWORD=${db_password}
TARGET=postgres
EOL

# Set ownership and permissions for the .env file
chown ubuntu:ubuntu /opt/avosoft_retail/.env
chmod 600 /opt/avosoft_retail/.env

# Start your application services
cd /opt/avosoft_retail

# Start FastAPI app and log output
nohup python3 -m uvicorn avosoft_engine.main:app --host 0.0.0.0 --port 8000 >> /var/log/avosoft/api.log 2>&1 &

# Start Streamlit dashboard and log output
nohup streamlit run avosoft_engine/dashboard.py --server.port 8501 --server.address=0.0.0.0 >> /var/log/avosoft/dashboard.log 2>&1 &

# Create a simple health check file
echo "Application deployed successfully at $(date)" > /opt/avosoft_retail/deployment.log