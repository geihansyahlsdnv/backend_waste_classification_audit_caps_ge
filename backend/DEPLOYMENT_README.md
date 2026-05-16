# Deployment & PWA Management

## Quick Start (TL;DR)

You have:
- **Domain**: hargai.site
- **GCP VM IP**: 34.101.46.140
- **Backend**: FastAPI + PostgreSQL + Redis + MinIO

### Deploy in 5 Steps:

1. **SSH to VM and run initial setup**:
   ```bash
   ssh -i your-key ubuntu@34.101.46.140
   curl -O https://raw.githubusercontent.com/your-repo/backend/main/gcp_setup.sh
   bash gcp_setup.sh
   ```

2. **Configure DNS**: Add A records to hargai.site → 34.101.46.140

3. **Request SSL Certificate**:
   ```bash
   sudo certbot certonly --standalone -d hargai.site
   mkdir -p ssl
   sudo cp /etc/letsencrypt/live/hargai.site/fullchain.pem ./ssl/cert.pem
   sudo cp /etc/letsencrypt/live/hargai.site/privkey.pem ./ssl/key.pem
   sudo chown $USER:$USER ./ssl/*.pem
   ```

4. **Setup and Deploy**:
   ```bash
   cp .env.production .env
   # Edit .env with your secrets
   bash deploy.sh init
   bash deploy.sh start
   ```

5. **Verify**:
   ```bash
   curl https://hargai.site/health
   # Visit https://hargai.site/docs for API documentation
   ```

## Documentation Files

| File | Purpose |
|------|---------|
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Comprehensive deployment instructions |
| [PWA_DEBUGGING_GUIDE.md](PWA_DEBUGGING_GUIDE.md) | Debugging, monitoring, and PWA management |
| [deploy.sh](deploy.sh) | Automated deployment management script |
| [gcp_setup.sh](gcp_setup.sh) | Initial GCP VM setup automation |
| [docker-compose.production.yml](docker-compose.production.yml) | Production Docker Compose configuration |
| [nginx.conf](nginx.conf) | Nginx reverse proxy & SSL configuration |
| [.env.production](.env.production) | Production environment template |

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│         GCP VM (34.101.46.140)              │
├─────────────────────────────────────────────┤
│  hargai.site:443 (HTTPS + SSL)              │
│  ↓                                          │
│  ┌─────────────────────────────────────┐   │
│  │ Nginx (Reverse Proxy & SSL)         │   │
│  └────────────────┬────────────────────┘   │
│                   ↓                        │
│  ┌─────────────────────────────────────┐   │
│  │ FastAPI Backend (Port 8000)         │   │
│  ├─────────────────────────────────────┤   │
│  │ Services:                           │   │
│  │ • PostgreSQL Database               │   │
│  │ • Redis Cache                       │   │
│  │ • MinIO Object Storage              │   │
│  │ • YOLOv8 Inference                  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## Environment Configuration

### Production Secrets (in .env):
```bash
# These should be strong, unique values
JWT_SECRET_KEY=<generate-with: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
POSTGRES_PASSWORD=<strong-password>
MINIO_ROOT_PASSWORD=<strong-password>
```

### Frontend Configuration:
Frontend must use: **`https://hargai.site`** (not IP address)
```env
VITE_API_BASE_URL=https://hargai.site
REACT_APP_API_BASE_URL=https://hargai.site
```

## Management Commands

### Using the Deploy Script
```bash
cd ~/projects/backend_waste_classification/backend

# Initialize (first time only)
bash deploy.sh init

# Start services
bash deploy.sh start

# Stop services
bash deploy.sh stop

# Restart services
bash deploy.sh restart

# View logs
bash deploy.sh logs          # Last 50 lines
bash deploy.sh logs -f       # Follow in real-time

# Check status
bash deploy.sh status
```

### Direct Docker Commands
```bash
# View all services
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f backend

# Access database
docker-compose -f docker-compose.production.yml exec db psql -U waste_user -d waste_db

# Check resource usage
docker stats

# Restart individual service
docker-compose -f docker-compose.production.yml restart backend
```

## API Access & Testing

### Health Check
```bash
curl https://hargai.site/health
```

### API Documentation
- **Swagger UI**: https://hargai.site/docs
- **ReDoc**: https://hargai.site/redoc

### Authentication
```bash
# Register
curl -X POST https://hargai.site/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Pass123!","full_name":"User"}'

# Login
curl -X POST https://hargai.site/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"Pass123!"}'
```

## PWA Debugging

### Check Backend Health
```bash
# From any machine
curl -v https://hargai.site/health

# SSH tunnel for internal access
ssh -i your-key -L 8000:localhost:8000 ubuntu@34.101.46.140
curl http://localhost:8000/health
```

### Monitor Logs in Real-time
```bash
ssh -i your-key ubuntu@34.101.46.140
cd ~/projects/backend_waste_classification/backend
bash deploy.sh logs -f
```

### Database Access & Debugging
```bash
# SSH tunnel for database
ssh -i your-key -L 5432:localhost:5432 ubuntu@34.101.46.140

# Then from local machine
psql -h localhost -U waste_user -d waste_db
```

### View Metrics
```bash
# SSH tunnel for metrics
ssh -i your-key -L 9090:localhost:9090 ubuntu@34.101.46.140

# Access from local browser
http://localhost:9090/metrics
```

## Certificate Management

### Check Expiration
```bash
# From VM
openssl x509 -in ./ssl/cert.pem -noout -dates

# Or check remotely
echo | openssl s_client -servername hargai.site -connect hargai.site:443 2>/dev/null | openssl x509 -noout -dates
```

### Renew Certificate
```bash
ssh ubuntu@34.101.46.140
cd ~/projects/backend_waste_classification/backend

sudo certbot renew --force-renewal
sudo cp /etc/letsencrypt/live/hargai.site/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/hargai.site/privkey.pem ./ssl/key.pem
sudo chown $USER:$USER ./ssl/*.pem

docker-compose -f docker-compose.production.yml restart nginx
```

### Auto-Renewal (Cron)
```bash
# Setup automatic renewal
sudo crontab -e

# Add this line (runs daily at 2 AM):
0 2 * * * certbot renew --quiet && cp /etc/letsencrypt/live/hargai.site/fullchain.pem /home/ubuntu/projects/backend_waste_classification/backend/ssl/cert.pem && cp /etc/letsencrypt/live/hargai.site/privkey.pem /home/ubuntu/projects/backend_waste_classification/backend/ssl/key.pem && docker-compose -f /home/ubuntu/projects/backend_waste_classification/backend/docker-compose.production.yml restart nginx
```

## Troubleshooting

### Issue: "Cannot connect to API"
```bash
# 1. Check if services are running
docker-compose -f docker-compose.production.yml ps

# 2. Check logs
docker-compose -f docker-compose.production.yml logs backend

# 3. Check DNS resolution
nslookup hargai.site
# Should resolve to 34.101.46.140

# 4. Test HTTPS directly on VM
curl http://localhost:8000/health
```

### Issue: "SSL certificate error"
```bash
# Check certificate validity
openssl x509 -in ./ssl/cert.pem -noout -dates

# Verify it matches the domain
openssl x509 -in ./ssl/cert.pem -noout -text | grep "DNS:"

# Renew if needed
sudo certbot renew --force-renewal
```

### Issue: "Database connection failed"
```bash
# Check if database is running
docker-compose -f docker-compose.production.yml ps db

# Check database logs
docker-compose -f docker-compose.production.yml logs db

# Verify credentials in .env
grep DATABASE_URL .env

# Test connection
docker-compose -f docker-compose.production.yml exec db psql -U waste_user -d waste_db -c "SELECT 1"
```

### Issue: "CORS error from frontend"
```bash
# Frontend must use https://hargai.site
# Not http://, IP address, or localhost

# Verify CORS is configured
cat .env | grep ALLOWED_ORIGINS

# Check actual response headers
curl -i -H "Origin: https://hargai.site" https://hargai.site/health
```

## Monitoring & Maintenance

### Daily Checks
```bash
# SSH to VM and run
bash deploy.sh status

# This will show:
# - All services running status
# - API health check
# - Database connectivity
# - Resource usage
```

### Weekly Tasks
- Check certificate expiration date (30 days before)
- Review disk space: `df -h`
- Review database size: `docker-compose exec db du -sh /var/lib/postgresql/data/`
- Backup database: `docker-compose exec db pg_dump -U waste_user waste_db > backup_weekly.sql`

### Monthly Tasks
- Review logs for errors
- Update Docker images: `docker-compose pull && docker-compose up -d`
- Test backup/restore process
- Review API usage metrics

## Security Considerations

✅ **Already Configured**:
- HTTPS/SSL with Let's Encrypt
- JWT authentication
- CORS restrictions
- Health checks
- Docker network isolation

⚠️ **Additional Recommendations**:
1. Change all default credentials in .env
2. Enable GCP Cloud Armor for DDoS protection
3. Setup GCP Cloud Monitoring for alerts
4. Configure database backups to Cloud Storage
5. Enable audit logging in PostgreSQL
6. Use VPC and restrict SSH access

## Support & Resources

- **Full Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **PWA Debugging Guide**: [PWA_DEBUGGING_GUIDE.md](PWA_DEBUGGING_GUIDE.md)
- **API Docs**: https://hargai.site/docs
- **Docker Documentation**: https://docs.docker.com
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Let's Encrypt**: https://letsencrypt.org

## Next Steps

1. ✅ Read this document
2. ✅ Review [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. ✅ Run `gcp_setup.sh` on your GCP VM
4. ✅ Configure DNS
5. ✅ Request SSL certificate
6. ✅ Run `bash deploy.sh init`
7. ✅ Run `bash deploy.sh start`
8. ✅ Test API at https://hargai.site/docs
9. ✅ Configure frontend to use https://hargai.site
10. ✅ Launch your PWA!

---

**Created**: May 16, 2026
**Domain**: hargai.site
**IP**: 34.101.46.140
**Status**: Ready to Deploy
