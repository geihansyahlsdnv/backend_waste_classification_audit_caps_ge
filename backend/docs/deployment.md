# Dokumentasi Deployment

## Persyaratan Sistem

### Hardware Minimum
- CPU: 4 cores
- RAM: 8GB
- Storage: 20GB
- GPU (opsional): NVIDIA GPU dengan CUDA support

### Software
- Docker dan Docker Compose
- NVIDIA Container Toolkit (jika menggunakan GPU)
- Git

## Environment Variables

Buat file `.env` di root project dengan variabel berikut:

```env
# Database
DATABASE_URL=postgresql://user:password@db:5432/waste_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_user
MINIO_SECRET_KEY=minio_password
MINIO_BUCKET_NAME=models

# Security
JWT_SECRET_KEY=your-secret-key-here  # Ganti dengan secret key yang aman
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Model
MODEL_WEIGHTS_PATH=http://minio:9000/models/yolov8s_final.pt

# CORS
ALLOWED_ORIGINS=["http://localhost:3000"]  # Sesuaikan dengan URL frontend
```

## Langkah Deployment

1. Clone repository:
```bash
git clone <repository-url>
cd backend
```

2. Setup environment:
```bash
cp .env.example .env
# Edit .env sesuai kebutuhan
```

3. Build dan jalankan container:
```bash
# Tanpa GPU
docker-compose up -d

# Dengan GPU
docker-compose -f docker-compose.gpu.yml up -d
```

4. Jalankan database migration:
```bash
docker-compose exec backend alembic upgrade head
```

5. Upload model ke MinIO:
```bash
# Buka MinIO Console di http://localhost:9001
# Login dengan MINIO_ACCESS_KEY dan MINIO_SECRET_KEY
# Buat bucket 'models'
# Upload file model YOLOv8
```

## Monitoring

1. Metrics dapat diakses di:
   - `/metrics` - Prometheus metrics
   - `/health` - Health check status

2. Log dapat diakses dengan:
```bash
docker-compose logs -f backend
```

## Scaling

Untuk scaling horizontal:

1. Update jumlah replicas di docker-compose:
```yaml
services:
  backend:
    deploy:
      replicas: 3
```

2. Tambahkan load balancer (contoh: Nginx):
```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
    }
}
```

## Backup

1. Database backup:
```bash
docker-compose exec db pg_dump -U user waste_db > backup.sql
```

2. MinIO backup:
```bash
docker-compose exec minio mc mirror /data /backup
```

## Troubleshooting

### Common Issues

1. Database Connection Error
```bash
# Check database status
docker-compose ps db
# Check logs
docker-compose logs db
```

2. Model Loading Error
```bash
# Verify model exists in MinIO
docker-compose exec minio mc ls models/
# Check backend logs
docker-compose logs backend
```

3. Performance Issues
- Check monitoring metrics di `/metrics`
- Review log untuk slow queries
- Verifikasi resource usage dengan `docker stats`

### Security Best Practices

1. Update secret keys secara berkala
2. Aktifkan HTTPS di production
3. Regular security updates
4. Implement rate limiting
5. Monitor suspicious activities

## CI/CD Pipeline (GitHub Actions)

```yaml
name: CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=app
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Add deployment steps here
```