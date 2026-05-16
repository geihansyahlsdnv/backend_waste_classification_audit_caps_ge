#!/bin/bash

# GCP VM Initial Setup Script
# Run this on your GCP VM after SSH connection
# Usage: bash gcp_setup.sh

set -e

echo "=========================================="
echo "GCP VM Setup for Waste Classification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Update system
echo -e "${YELLOW}Step 1: Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y
echo -e "${GREEN}✓ System updated${NC}\n"

# Step 2: Install Docker
echo -e "${YELLOW}Step 2: Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  rm get-docker.sh
  
  # Add user to docker group
  sudo usermod -aG docker $USER
  newgrp docker
else
  echo -e "${GREEN}✓ Docker already installed${NC}"
fi
echo -e "${GREEN}✓ Docker installed${NC}\n"

# Step 3: Install Docker Compose
echo -e "${YELLOW}Step 3: Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
  sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
else
  echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}\n"

# Step 4: Install Certbot for SSL
echo -e "${YELLOW}Step 4: Installing Certbot for SSL certificates...${NC}"
sudo apt install certbot python3-certbot-nginx -y
echo -e "${GREEN}✓ Certbot installed${NC}\n"

# Step 5: Setup project directory
echo -e "${YELLOW}Step 5: Setting up project directory...${NC}"
mkdir -p ~/projects
cd ~/projects
echo -e "${GREEN}✓ Project directory created at ~/projects${NC}\n"

# Step 6: Clone repository (user needs to provide)
echo -e "${YELLOW}Step 6: Repository setup${NC}"
echo "Please clone your repository here:"
echo "  cd ~/projects"
echo "  git clone <your-repo-url>"
echo "  cd backend_waste_classification/backend"
echo ""

# Step 7: Configure DNS
echo -e "${YELLOW}Step 7: DNS Configuration${NC}"
echo "Before proceeding, ensure your DNS records are configured:"
echo ""
echo "Add these records to your domain registrar (hargai.site):"
echo "  Type  | Name | Value"
echo "  ------|------|------------------"
echo "  A     | @    | 34.101.46.140"
echo "  A     | www  | 34.101.46.140"
echo ""
echo "Wait 5-30 minutes for DNS propagation."
echo ""

# Step 8: Request SSL Certificate
echo -e "${YELLOW}Step 8: SSL Certificate Setup${NC}"
echo ""
echo "When ready, run these commands in your project directory:"
echo ""
echo "  # Request certificate"
echo "  sudo certbot certonly --standalone -d hargai.site"
echo ""
echo "  # Create ssl directory"
echo "  mkdir -p ssl"
echo ""
echo "  # Copy certificates"
echo "  sudo cp /etc/letsencrypt/live/hargai.site/fullchain.pem ./ssl/cert.pem"
echo "  sudo cp /etc/letsencrypt/live/hargai.site/privkey.pem ./ssl/key.pem"
echo "  sudo chown \$USER:\$USER ./ssl/*.pem"
echo "  chmod 644 ./ssl/*.pem"
echo ""

# Step 9: Firewall setup (optional)
echo -e "${YELLOW}Step 9: GCP Firewall Setup${NC}"
echo ""
echo "Configure GCP firewall to allow HTTP/HTTPS:"
echo ""
echo "  # From your local machine with gcloud CLI:"
echo "  gcloud compute firewall-rules create allow-web \\\"
echo "    --allow=tcp:80,tcp:443 \\\"
echo "    --target-tags=http-server,https-server \\\"
echo "    --project=<your-project-id>"
echo ""

# Summary
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Configure DNS records (A records for hargai.site)"
echo "  2. Wait for DNS propagation (5-30 minutes)"
echo "  3. Clone your repository to ~/projects"
echo "  4. Request SSL certificate with certbot"
echo "  5. Setup .env file with production values"
echo "  6. Run: bash deploy.sh init"
echo "  7. Run: bash deploy.sh start"
echo ""
echo "Verification:"
echo "  docker --version"
docker --version
echo "  docker-compose --version"
docker-compose --version
echo ""
echo "For more details, see DEPLOYMENT_GUIDE.md"
