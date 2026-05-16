# PWA Debugging & Management Guide

## Overview
This guide covers debugging, monitoring, and managing the Waste Classification PWA and Backend on production.

## 1. Backend Health & Status Monitoring

### Basic Health Checks
```bash
# Direct API health endpoint
curl -i https://hargai.site/health

# Expected response:
# HTTP/2 200
# {
#   "status": "healthy",
#   "timestamp": "2024-05-16T10:30:00.000Z",
#   "components": {...}
# }

# Health check from your local machine
curl -v https://hargai.site/health

# Test with DNS
nslookup hargai.site
# Should resolve to 34.101.46.140
```

### Check Service Status on VM
```bash
# SSH into VM
ssh -i your-key ubuntu@34.101.46.140

# Check all containers running
docker-compose -f docker-compose.production.yml ps

# Should show:
# NAME                      STATUS
# waste-classifier-backend  Up (healthy)
# waste-classifier-db       Up (healthy)
# waste-classifier-redis    Up (healthy)
# waste-classifier-minio    Up (healthy)
# waste-classifier-nginx    Up (healthy)
```

## 2. Accessing Logs

### View Real-time Logs
```bash
# Backend application logs
docker-compose -f docker-compose.production.yml logs -f backend

# Nginx access and errors
docker-compose -f docker-compose.production.yml logs -f nginx

# All services
docker-compose -f docker-compose.production.yml logs -f

# Last 100 lines
docker-compose -f docker-compose.production.yml logs --tail=100 backend
```

### Save Logs to File
```bash
# Export logs for analysis
docker-compose -f docker-compose.production.yml logs backend > backend.log

# Search in logs
grep "ERROR" backend.log
grep "user_id" backend.log
```

## 3. Database Debugging

### Access Database Directly
```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.production.yml exec db psql -U waste_user -d waste_db

# Common queries:
# List all tables
\dt

# Check user count
SELECT COUNT(*) FROM users;

# Recent classifications
SELECT id, user_id, created_at FROM classifications ORDER BY created_at DESC LIMIT 10;

# View table structure
\d classifications

# Exit
\q
```

### Backup Database
```bash
# Create backup
docker-compose -f docker-compose.production.yml exec db pg_dump -U waste_user waste_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker-compose -f docker-compose.production.yml exec db pg_dump -U waste_user waste_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Size check
du -h backup_*.sql.gz
```

### Restore Database
```bash
# From backup
cat backup_20240516_100000.sql | docker-compose -f docker-compose.production.yml exec -T db psql -U waste_user waste_db

# Or with gzip
gunzip -c backup_20240516_100000.sql.gz | docker-compose -f docker-compose.production.yml exec -T db psql -U waste_user waste_db
```

## 4. API Endpoint Testing

### Test Authentication
```bash
# Register new user
curl -X POST https://hargai.site/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","full_name":"Test User"}'

# Login
curl -X POST https://hargai.site/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"Test123!"}'

# Response includes access_token
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "token_type": "bearer"
# }

# Use token for authenticated requests
TOKEN="your_access_token_here"
curl -H "Authorization: Bearer $TOKEN" https://hargai.site/api/profile
```

### Test Classification Endpoint
```bash
# Upload image for classification
TOKEN="your_access_token"
curl -X POST https://hargai.site/classify \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@/path/to/waste_image.jpg"

# Expected response
# {
#   "id": "123e4567-e89b-12d3-a456-426614174000",
#   "detections": [
#     {"class": "plastic", "confidence": 0.95, "bbox": [...]},
#     {"class": "metal", "confidence": 0.87, "bbox": [...]}
#   ],
#   "timestamp": "2024-05-16T10:30:00Z"
# }
```

### Test Statistics Endpoint
```bash
TOKEN="your_access_token"

# Get user statistics
curl -H "Authorization: Bearer $TOKEN" https://hargai.site/stats/user

# Get classification history
curl -H "Authorization: Bearer $TOKEN" https://hargai.site/history

# Get dashboard data
curl -H "Authorization: Bearer $TOKEN" https://hargai.site/stats/dashboard
```

## 5. Performance & Resource Monitoring

### Check Resource Usage on VM
```bash
# CPU and Memory
docker stats waste-classifier-backend waste-classifier-db

# Disk usage
df -h
docker system df

# Network statistics
netstat -tuln | grep LISTEN
```

### Monitor API Response Times
```bash
# Time API request
time curl -s https://hargai.site/health > /dev/null

# Detailed timing
curl -w "\nTime taken: %{time_total}s\n" https://hargai.site/health

# Check multiple endpoints
for endpoint in /health /docs /api/profile; do
  echo "Testing $endpoint"
  curl -w "Time: %{time_total}s\n\n" https://hargai.site$endpoint
done
```

### View Prometheus Metrics
```bash
# Metrics are available internally (restricted to localhost)
# SSH tunnel to access
ssh -i your-key -L 9090:localhost:9090 ubuntu@34.101.46.140

# Then from local machine
curl http://localhost:9090/metrics
```

## 6. SSL Certificate Management

### Check Certificate Expiration
```bash
# From local machine
echo | openssl s_client -servername hargai.site -connect hargai.site:443 2>/dev/null | openssl x509 -noout -dates

# From VM
openssl x509 -in ./ssl/cert.pem -text -noout | grep -A2 "Not Valid"

# Check remaining days
echo "Days remaining: $(($(date -d "$(openssl x509 -in ./ssl/cert.pem -noout -enddate | grep notAfter=)" +%s) - $(date +%s)) / 86400))"
```

### Renew Certificate Manually
```bash
# SSH to VM
ssh ubuntu@34.101.46.140

cd ~/projects/backend_waste_classification/backend

# Renew certificate
sudo certbot renew --force-renewal

# Copy renewed certificates
sudo cp /etc/letsencrypt/live/hargai.site/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/hargai.site/privkey.pem ./ssl/key.pem
sudo chown $USER:$USER ./ssl/*.pem

# Reload Nginx
docker-compose -f docker-compose.production.yml restart nginx
```

## 7. Frontend PWA Debugging

### Access Frontend DevTools
```bash
# If frontend is hosted on separate VM/CDN:
# Open browser DevTools (F12 or Ctrl+Shift+I)
# Check:
# - Application tab → Manifest
# - Application tab → Service Workers
# - Network tab → Check API calls to backend
# - Console tab → Check for CORS/API errors
```

### Check Service Worker Registration
```javascript
// In browser console
navigator.serviceWorker.ready.then(registration => {
  console.log('Service Worker ready:', registration);
  console.log('Scope:', registration.scope);
});

// List all registered SWs
navigator.serviceWorker.getRegistrations().then(regs => {
  regs.forEach(reg => console.log('SW registered:', reg));
});
```

### Test PWA Installation
```javascript
// Check install prompt
window.addEventListener('beforeinstallprompt', (e) => {
  console.log('Install prompt available');
  // e.prompt() to trigger install
});

// Check if running as PWA
console.log('Display mode:', window.navigator.standalone ? 'PWA' : 'Browser');
```

### Debug API Requests from Frontend
```bash
# SSH tunnel to API
ssh -i your-key -L 3000:localhost:3000 ubuntu@34.101.46.140

# Then test locally
curl -v http://localhost:3000/api/profile

# Check CORS headers
curl -i -H "Origin: https://hargai.site" \
  -H "Access-Control-Request-Method: GET" \
  https://hargai.site/api/profile
```

## 8. Error Debugging & Troubleshooting

### Common Issues & Solutions

#### Backend not responding
```bash
# Check if service is running
docker-compose -f docker-compose.production.yml ps backend

# View logs
docker-compose -f docker-compose.production.yml logs backend

# Restart service
docker-compose -f docker-compose.production.yml restart backend

# Check network connectivity
docker-compose -f docker-compose.production.yml exec backend ping redis
```

#### Database connection error
```bash
# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Test connection
docker-compose -f docker-compose.production.yml exec db psql -U waste_user -d waste_db -c "SELECT 1"

# Check DB logs
docker-compose -f docker-compose.production.yml logs db
```

#### CORS error from frontend
```bash
# The frontend must use https://hargai.site
# Not: http://, 34.101.46.140, or localhost

# Check allowed origins
docker-compose -f docker-compose.production.yml exec backend env | grep ALLOWED_ORIGINS

# Verify request origin
curl -i -H "Origin: https://hargai.site" https://hargai.site/health
```

#### SSL/Certificate error
```bash
# Check certificate validity
openssl x509 -in ./ssl/cert.pem -noout -dates

# Verify certificate matches domain
openssl x509 -in ./ssl/cert.pem -noout -text | grep "DNS:"

# Test SSL connection
openssl s_client -connect hargai.site:443 -servername hargai.site
```

#### Image upload issues
```bash
# Check file permissions
ls -la uploads/

# Check disk space
df -h

# View file size limit in nginx
grep "client_max_body_size" nginx.conf

# Check MinIO bucket
docker-compose -f docker-compose.production.yml exec minio \
  mc ls minio/models

# Check upload logs
docker-compose -f docker-compose.production.yml logs backend | grep -i upload
```

## 9. Performance Optimization

### Enable Caching
```bash
# Clear Redis cache if needed
docker-compose -f docker-compose.production.yml exec redis redis-cli FLUSHALL

# Monitor cache hits
docker-compose -f docker-compose.production.yml exec redis redis-cli INFO stats
```

### Database Query Optimization
```bash
# Enable slow query logging
docker-compose -f docker-compose.production.yml exec db psql -U waste_user -d waste_db -c "
SET log_min_duration_statement = 1000;" # Log queries > 1 second
```

### Nginx Performance
```bash
# Check active connections
docker exec waste-classifier-nginx netstat -an | grep ESTABLISHED | wc -l

# View nginx stats
docker-compose -f docker-compose.production.yml logs nginx | tail -50
```

## 10. Automated Monitoring Setup

### Setup Health Check Script
```bash
#!/bin/bash
# save as health_check.sh

DOMAIN="hargai.site"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Running health checks..."

# Check HTTPS
if curl -sf https://$DOMAIN/health > /dev/null; then
  echo "✓ HTTPS endpoint healthy"
else
  echo "✗ HTTPS endpoint failed"
fi

# Check database
if docker-compose -f docker-compose.production.yml exec -T db psql -U waste_user -d waste_db -c "SELECT 1" > /dev/null 2>&1; then
  echo "✓ Database healthy"
else
  echo "✗ Database failed"
fi

# Check services
docker-compose -f docker-compose.production.yml ps | grep -v "Up" | grep "waste-classifier" && echo "✗ Some services down" || echo "✓ All services up"
```

### Schedule with Cron
```bash
# Add to crontab
crontab -e

# Check every 5 minutes
*/5 * * * * /path/to/health_check.sh >> /var/log/health_check.log 2>&1
```

## 11. Quick Commands Reference

```bash
# Deployment & Management
docker-compose -f docker-compose.production.yml up -d      # Start all services
docker-compose -f docker-compose.production.yml down        # Stop all services
docker-compose -f docker-compose.production.yml restart     # Restart services
docker-compose -f docker-compose.production.yml logs -f     # View logs

# Debugging
curl https://hargai.site/health                             # Test health
curl https://hargai.site/docs                               # Access API docs
ssh -L 5432:localhost:5432 ubuntu@34.101.46.140            # SSH tunnel for DB
ssh -L 9090:localhost:9090 ubuntu@34.101.46.140            # SSH tunnel for metrics

# Database
docker-compose exec db psql -U waste_user -d waste_db       # Access DB
docker-compose exec db pg_dump -U waste_user waste_db > backup.sql  # Backup

# Monitoring
docker stats                                                 # Resource usage
docker-compose ps                                           # Service status
tail -f /var/log/nginx/access.log                           # Nginx logs
```

## Support & Resources

- **API Documentation**: https://hargai.site/docs
- **Backend Logs**: Check docker logs for detailed errors
- **Database**: SSH tunnel to VM and connect with psql
- **Metrics**: Available at `/metrics` endpoint (internal only)
- **SSL Certificate**: Managed by Let's Encrypt via Certbot
