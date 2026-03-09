#!/bin/bash

################################################################################
# AWS EC2 Deployment Script for Financial Intelligence Platform
# 
# Usage: ./deploy/aws_setup.sh [instance-type] [region] [key-pair]
# Example: ./deploy/aws_setup.sh t3.medium us-east-1 my-key-pair
################################################################################

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Configuration
INSTANCE_TYPE="${1:-t3.medium}"
REGION="${2:-us-east-1}"
KEY_PAIR="${3:-}"
INSTANCE_NAME="financial-platform"
SECURITY_GROUP_NAME="${INSTANCE_NAME}-sg"
STORAGE_SIZE="30"  # GB

# Validation
if [ -z "$KEY_PAIR" ]; then
    log_error "Key pair name is required"
    echo "Usage: $0 <instance-type> <region> <key-pair-name>"
    echo "Example: $0 t3.medium us-east-1 my-key-pair"
    exit 1
fi

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check that key pair exists in AWS
log_info "Verifying AWS key pair '$KEY_PAIR' exists in region '$REGION'..."
if ! aws ec2 describe-key-pairs --key-names "$KEY_PAIR" --region "$REGION" &> /dev/null; then
    log_error "Key pair '$KEY_PAIR' not found in region '$REGION'"
    exit 1
fi
log_success "Key pair verified"

# Get the latest Ubuntu 24.04 LTS AMI ID
log_info "Fetching latest Ubuntu 24.04 LTS AMI for region $REGION..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-noble-24.04-amd64-server-*" \
    --region "$REGION" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text)

if [ -z "$AMI_ID" ] || [ "$AMI_ID" = "None" ]; then
    log_error "Could not find Ubuntu 24.04 LTS AMI in region $REGION"
    exit 1
fi
log_success "Using AMI: $AMI_ID"

# Create security group if it doesn't exist
log_info "Setting up security group..."
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" \
    --region "$REGION" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
    log_info "Creating security group '$SECURITY_GROUP_NAME'..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SECURITY_GROUP_NAME" \
        --description "Security group for Financial Intelligence Platform" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)
    log_success "Created security group: $SG_ID"
else
    log_info "Using existing security group: $SG_ID"
fi

# Configure security group rules
log_info "Configuring security group rules..."
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region "$REGION" \
    2>/dev/null || log_warning "SSH rule already exists"

aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region "$REGION" \
    2>/dev/null || log_warning "HTTP rule already exists"

aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region "$REGION" \
    2>/dev/null || log_warning "HTTPS rule already exists"

log_success "Security group configured"

# Launch EC2 instance
log_info "Launching EC2 instance (type: $INSTANCE_TYPE, region: $REGION)..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_PAIR" \
    --security-group-ids "$SG_ID" \
    --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=$STORAGE_SIZE,VolumeType=gp3,DeleteOnTermination=true}" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --region "$REGION" \
    --query 'Instances[0].InstanceId' \
    --output text)

log_success "Instance launched: $INSTANCE_ID"

# Wait for instance to be running
log_info "Waiting for instance to start (this may take a minute)..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
log_success "Instance is running"

# Wait for status checks
log_info "Waiting for instance to pass status checks..."
sleep 10
aws ec2 wait instance-status-ok --instance-ids "$INSTANCE_ID" --region "$REGION"
log_success "Instance status checks passed"

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

log_success "Instance public IP: $PUBLIC_IP"

# Wait for SSH to be available
log_info "Waiting for SSH to be available..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$PUBLIC_IP/22" 2>/dev/null; then
        log_success "SSH is available"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    log_error "SSH timeout after 60 seconds"
    exit 1
fi

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME=$(basename "$PROJECT_ROOT")

# Create remote setup script
REMOTE_SETUP=$(mktemp)
cat > "$REMOTE_SETUP" << 'REMOTE_SCRIPT'
#!/bin/bash
set -e

echo "[INFO] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

echo "[INFO] Installing Docker..."
sudo apt-get install -y docker.io docker-compose

echo "[INFO] Configuring Docker permissions..."
sudo usermod -aG docker ubuntu
sudo systemctl enable docker
sudo systemctl start docker

echo "[INFO] Setting up project directory..."
mkdir -p /home/ubuntu/app
cd /home/ubuntu/app

echo "[INFO] Waiting for Docker to be fully ready..."
sleep 5

echo "[INFO] Creating .env file..."
cat > .env << 'ENV_FILE'
# Database Configuration
DATABASE_URL=postgresql://postgree:2007@db:5432/finDB
POSTGRES_USER=postgree
POSTGRES_PASSWORD=2007
POSTGRES_DB=finDB

# API Configuration
API_HOST=0.0.0.0
API_PORT=7860

# Airflow Configuration
AIRFLOW__CORE__LOAD_EXAMPLES=false
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://postgree:2007@db:5432/airflow_db

# Enable all features
FEATURE_ANOMALIES=true
FEATURE_FORECASTS=true
FEATURE_SENTIMENT=true
FEATURE_PORTFOLIO=true
ENV_FILE

echo "[INFO] Bringing up Docker Compose services..."
docker compose up -d

echo "[INFO] Waiting for services to initialize..."
sleep 15

echo "[INFO] Checking service health..."
docker compose ps

echo "[SUCCESS] All services are up and running!"
REMOTE_SCRIPT

# Copy and run remote setup script
log_info "Copying project files to instance (this may take a minute)..."
scp -i "$HOME/.ssh/${KEY_PAIR}.pem" -o StrictHostKeyChecking=no -r "$PROJECT_ROOT" "ubuntu@$PUBLIC_IP:/home/ubuntu/app" 2>&1 | grep -v "Warning\|Identity added" || true

log_info "Running setup on remote instance..."
scp -i "$HOME/.ssh/${KEY_PAIR}.pem" -o StrictHostKeyChecking=no "$REMOTE_SETUP" "ubuntu@$PUBLIC_IP:/tmp/setup.sh"
ssh -i "$HOME/.ssh/${KEY_PAIR}.pem" -o StrictHostKeyChecking=no "ubuntu@$PUBLIC_IP" "chmod +x /tmp/setup.sh && /tmp/setup.sh"

# Cleanup
rm "$REMOTE_SETUP"

# Display success message
log_success "Deployment complete!"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Financial Intelligence Platform Deployed!     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "📊 ${BLUE}Dashboard:${NC}        http://$PUBLIC_IP"
echo -e "🔌 ${BLUE}API:${NC}              http://$PUBLIC_IP/api"
echo -e "📖 ${BLUE}API Docs:${NC}         http://$PUBLIC_IP/docs"
echo -e "🌍 ${BLUE}Airflow:${NC}          http://$PUBLIC_IP:8080 (if enabled)"
echo -e "📈 ${BLUE}MLflow:${NC}           http://$PUBLIC_IP:5000 (if enabled)"
echo ""
echo -e "${YELLOW}Instance Details:${NC}"
echo -e "  Instance ID: $INSTANCE_ID"
echo -e "  Region:      $REGION"
echo -e "  Type:        $INSTANCE_TYPE"
echo -e "  Public IP:   $PUBLIC_IP"
echo ""
echo -e "${YELLOW}SSH Access:${NC}"
echo "  ssh -i ~/.ssh/${KEY_PAIR}.pem ubuntu@$PUBLIC_IP"
echo ""
echo -e "${YELLOW}View Logs:${NC}"
echo "  ssh -i ~/.ssh/${KEY_PAIR}.pem ubuntu@$PUBLIC_IP 'docker compose logs -f'"
echo ""
echo -e "${YELLOW}Stop Services:${NC}"
echo "  ssh -i ~/.ssh/${KEY_PAIR}.pem ubuntu@$PUBLIC_IP 'docker compose down'"
echo ""
