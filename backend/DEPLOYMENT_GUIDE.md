# Deployment Guide - GCP VM (hargai.site / 34.101.46.140)

## Prerequisites

- GCP VM instance with Ubuntu 20.04/22.04 LTS
- Static IP: 34.101.46.140
- Domain: hargai.site (DNS records pointing to the IP)
- SSH access to the VM
- Root or sudo privileges

## Step 1: Initial VM Setup

### Connect to your GCP VM:
```bash
gcloud compute ssh waste-classifier-vm --zone=us-central1-a
# Or use direct SSH
ssh -i your-private-key ubuntu@34.101.46.140
```

### Update system packages:
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Docker and Docker Compose:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Install SSL Certificate with Let's Encrypt:
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Generate certificate
sudo certbot certonly --standalone -d hargai.site

# Follow prompts and provide your email
# Certificates will be stored in: /etc/letsencrypt/live/hargai.site/

# Create directory for nginx
mkdir -p ./ssl

# Copy certificates (with sudo)
sudo cp /etc/letsencrypt/live/hargai.site/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/hargai.site/privkey.pem ./ssl/key.pem
sudo chown $USER:$USER ./ssl/*.pem
chmod 644 ./ssl/*.pem
```

## Step 2: Clone and Setup Backend

```bash
# Create project directory
mkdir -p ~/projects
cd ~/projects

# Clone your backend repository
git clone https://github.com/your-repo/backend_waste_classification.git
cd backend_waste_classification/backend

# Create production environment file
cp .env.production .env

# Edit .env and update secrets (IMPORTANT!)
nano .env
# - Change JWT_SECRET_KEY to a strong random string
# - Update database credentials
# - Update MinIO credentials
```

### Generate secure JWT secret:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 3: Deploy with Docker Compose

```bash
# Build and start all services
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose logs -f backend

# Check service status
docker-compose ps

# Verify health endpoint
curl http://localhost:8000/health
```

## Step 4: DNS Configuration (in your domain registrar)

Add these DNS records for hargai.site:

```
Type    | Name           | Value
--------|-----------------|------------------
A       | @              | 34.101.46.140
A       | www            | 34.101.46.140
CNAME   | api            | hargai.site
```

Wait for DNS propagation (5-30 minutes).

## Step 5: Verify Deployment

### Test the API endpoints:

```bash
# Test HTTP (should redirect to HTTPS)
curl -i http://hargai.site/

# Test HTTPS
curl -i https://hargai.site/
curl -i https://hargai.site/health
curl -i https://hargai.site/docs

# Test with IP
curl -i https://34.101.46.140/
```

### Check SSL certificate:
```bash
curl -v https://hargai.site/ 2>&1 | grep -i "certificate"

# Or use openssl
openssl s_client -connect hargai.site:443 -showcerts
```

## Step 6: Configure Frontend CORS

Update your frontend `.env` to point to the backend:

```env
VITE_API_BASE_URL=https://hargai.site
REACT_APP_API_BASE_URL=https://hargai.site
```

## Step 7: Monitoring and Maintenance

### View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f db
docker-compose logs -f redis
```

### Check disk space:
```bash
df -h
docker system df
```

### Auto-renew SSL certificates:
```bash
# Create renewal script
sudo crontab -e

# Add this line (runs daily)
0 2 * * * sudo certbot renew --quiet && sudo cp /etc/letsencrypt/live/hargai.site/fullchain.pem /path/to/project/ssl/cert.pem && sudo cp /etc/letsencrypt/live/hargai.site/privkey.pem /path/to/project/ssl/key.pem && sudo chown $USER:$USER /path/to/project/ssl/*.pem && docker-compose -f docker-compose.production.yml restart nginx
```

### Restart services:
```bash
docker-compose -f docker-compose.production.yml restart backend
docker-compose -f docker-compose.production.yml restart nginx
```

## Step 8: PWA Debugging & Management

### Access Metrics and Logs:
```bash
# Prometheus metrics (restricted to localhost)
curl http://localhost/metrics

# Application health
curl https://hargai.site/health

# API documentation
https://hargai.site/docs
https://hargai.site/redoc
```

### Remote Debugging:
```bash
# SSH tunnel to access local services
ssh -i your-key -L 8000:localhost:8000 -L 5432:localhost:5432 ubuntu@34.101.46.140

# Then connect from your local machine
curl http://localhost:8000/health
psql -h localhost -U waste_user -d waste_db
```

### Enable detailed logging (optional):
```bash
# SSH into VM
ssh ubuntu@34.101.46.140

# Edit docker-compose.production.yml to add:
environment:
  LOG_LEVEL: DEBUG

# Restart
docker-compose restart backend

# Follow logs
docker-compose logs -f backend
```

### Database backup:
```bash
# Create backup
docker-compose exec db pg_dump -U waste_user waste_db > backup_$(date +%Y%m%d).sql

# Restore from backup
cat backup_20240516.sql | docker-compose exec -T db psql -U waste_user waste_db
```

### Monitor with Nginx:
```bash
# Check Nginx status
docker-compose logs -f nginx

# View request logs
docker exec waste-classifier-nginx tail -f /var/log/nginx/access.log
```

## Troubleshooting

### Backend not starting
```bash
docker-compose logs backend
# Check .env file for missing variables
# Ensure all services are running: docker-compose ps
```

### SSL certificate issues
```bash
# Check certificate validity
openssl x509 -in ./ssl/cert.pem -text -noout

# Force renewal
sudo certbot renew --force-renewal
```

### Database connection errors
```bash
docker-compose exec db psql -U waste_user -c "SELECT 1"
# Check DATABASE_URL in .env
```

### CORS errors in frontend
```bash
# Verify CORS configuration in .env
# Frontend must use https://hargai.site (not http or IP)
# Check browser console for specific errors
```

## Security Recommendations

1. **Change default credentials** in .env
2. **Enable firewall** on GCP:
   ```bash
   gcloud compute firewall-rules create waste-classifier-allow-web \
     --allow tcp:80,tcp:443 \
     --target-tags waste-classifier
   ```

3. **Setup automated backups** using Google Cloud Storage:
   ```bash
   docker-compose exec db pg_dump -U waste_user waste_db | \
     gsutil cp - gs://your-bucket/backups/db_$(date +%Y%m%d).sql.gz
   ```

4. **Monitor with Google Cloud Monitoring**

5. **Enable rate limiting** in Nginx (optional):
   - Add to nginx.conf under http block:
   ```
   limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
   limit_req zone=api burst=20 nodelay;
   ```

## Quick Reference Commands

```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# Stop all services
docker-compose -f docker-compose.production.yml down

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Restart specific service
docker-compose -f docker-compose.production.yml restart backend

# Check service health
docker-compose -f docker-compose.production.yml ps

# Access database
docker-compose exec db psql -U waste_user waste_db

# Clear Docker cache (if needed)
docker system prune -a
```
