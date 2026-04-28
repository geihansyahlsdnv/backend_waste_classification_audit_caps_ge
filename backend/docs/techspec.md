 Tech Spec: Backend Klasifikasi Sampah & Inferensi YOLOv81. Tujuan dan Arsitektur SistemAspekDeskripsiTujuanMenyediakan RESTful API Gateway yang aman, scalable, dan berkinerja tinggi. Menjembatani Frontend (React PWA) dengan Model Inferensi YOLOv8 dan Data Storage (PostgreSQL/MinIO).ArsitekturMicroservices Modular dengan FastAPI sebagai API Gateway.Target Kinerja (SLA)[cite_start]Waktu Respons Klasifikasi Maksimum 2 detik[cite: 948, 971, 1261].Target Throughput[cite_start]Minimal 15 Frames Per Second (FPS) untuk proses inferensi kontinu[cite: 974, 1262].2. Teknologi Tumpukan (Technology Stack)KategoriKomponenVersi/SpesifikasiPeran dalam SistemBahasa PemrogramanPython$\ge$ 3.10FastAPI, Business Logic, dan ML Integration.Web FrameworkFastAPITerbaru[cite_start]Asynchronous API Gateway (RESTful API)[cite: 515, 656].ASGI ServerUvicornTerbaruServer performa tinggi untuk menjalankan FastAPI.Model & InferenceYOLOv8 (PyTorch)Terbaru[cite_start]Model Deep Learning untuk klasifikasi Recyclable vs Non-Recyclable[cite: 506, 516, 1260].DatabasePostgreSQL$\ge$ 15[cite_start]Penyimpanan data relasional: users, classification_results[cite: 517, 1139].Object StorageMinIOTerbaruS3-Compatible Object Storage untuk menyimpan bobot model YOLOv8.Cache/QueueRedisTerbaru[cite_start]In-memory Cache (Opsional) untuk lookup data cepat[cite: 1140].ContainerizationDocker & Docker ComposeTerbaru[cite_start]Memastikan portabilitas dan skalabilitas services[cite: 555, 956, 1094].3. Skema Data (Database Schema)A. Tabel Pengguna (users)Digunakan untuk Autentikasi dan Otorisasi (JWT).KolomTipe DataKebutuhanKeteranganuser_idUUID/INTPrimary KeyID unik pengguna.usernameVARCHAR(50)Unique, NOT NULLNama unik untuk login.emailVARCHAR(100)UniqueAlamat email.hashed_passwordVARCHAR(255)NOT NULLKata sandi yang sudah di-hash (Bcrypt/Argon2).roleVARCHAR(20)NOT NULLPeran: operator (lapangan), admin (price manager), developer (tim dev)B. Tabel Hasil Klasifikasi (classification_results)Digunakan untuk Monitoring dan Riwayat Deteksi.KolomTipe DataKebutuhanKeteranganresult_idUUID/INTPrimary KeyID unik hasil.user_idUUID/INTForeign KeyMengaitkan hasil dengan pengguna.waste_type_idUUID/INTForeign KeyLink ke jenis sampah (untuk pricing).labelVARCHAR(50)NOT NULLRecyclable atau Non-Recyclable.confidenceFLOATNOT NULLTingkat kepercayaan model (0.0 - 1.0).estimated_volumeFLOATNULLEstimasi volume/berat dari model.actual_volumeFLOATNULLVolume aktual hasil input user (editable).volume_unitVARCHAR(20)NOT NULLUnit (default: kg).estimated_priceDECIMAL(10,2)NULLHarga otomatis calculated (volume × waste_type.price).timestampTIMESTAMPNOT NULLWaktu deteksi.image_urlVARCHAR(255)NULLURL citra di MinIO.processing_time_msINTNULLWaktu inferensi. dengan pricing.JWT Valid (user/operator)Harus ≤ 2 detik./api/historyGETMengambil riwayat klasifikasi pengguna.JWT ValidMendukung pagination./api/statsGETMenampilkan statistik agregat klasifikasi + revenue.JWT ValidData di-cache (Redis)./api/waste-typeGETPURL list jenis sampah dengan harga aktual.JWT ValidPublic endpoint./api/waste-types/{id}/pricePATCHUpdate harga sampah (operator price manager)operator onlyAudit trail di price_history./api/price-historyGETView audit trail update harga.admin/supervisor/operatorTracking who changed what./api/classification/{id}/volumePATCHUpdate actual volume hasil (user bisa correct)user/admin/supervisorRecalc harga otomatis./minio/modelGETUnduh bobot model dari MinIO (saat startup).Internal/Service TokenDipicu saat startup backend

C. Tabel Jenis Sampah (waste_types) - BARU
Master data sampah dengan pricing.KolomTipe DataKebutuhanKeteranganwaste_type_idUUID/INTPrimary KeyID unik jenis sampah.nameVARCHAR(100)Unique, NOT NULLNama: "Plastik PET", "Kertas", dll.categoryVARCHAR(20)NOT NULLRecyclable atau Non-Recyclable.unitVARCHAR(20)NOT NULLUnit harga (kg, liter, pcs).current_priceDECIMAL(10,2)NULLHarga aktual di pasar.currencyVARCHAR(3)NOT NULLMata uang (IDR, USD, dll).is_activeBOOLEANNOT NULLStatus aktif.created_atTIMESTAMPNOT NULLCapstone waktu create.

D. Tabel History Harga (price_history) - BARU
Audit trail update harga oleh operator.KolomTipe DataKebutuhanKeteranganprice_history_idUUID/INTPrimary KeyID unik record.waste_type_idUUID/INTForeign KeyReferensi ke waste_types.old_priceDECIMAL(10,2)NULLHarga lama.new_priceDECIMAL(10,2)NULLHarga baru.updated_by_idUUID/INTForeign KeyUser yang update (operator role).updated_atTIMESTAMPNOT NULLCapstone waktu update.reasonVARCHAR(255)NULLAlasan update (opsional).4. Spesifikasi API Endpoint (RESTful)Semua endpoints dilindungi dengan HTTPS dan JWT.A. Autentikasi dan PenggunaEndpointMetodeDeskripsiInput (Body)OutputStatus Code/auth/registerPOSTPendaftaran akun pengguna baru.username, email, passwordmessage: success201/auth/loginPOSTAutentikasi dan mengembalikan JWT Token (klaim termasuk user_id, role).username atau email, passwordaccess_token200B. Fungsi Inti Klasifikasi dan DataEndpointMetodeDeskripsiOtorisasiCatatan Kinerja/api/classifyPOSTMenerima file gambar dan menjalankan inferensi YOLOv8.JWT Valid[cite_start]Harus $\le 2$ detik[cite: 948]./api/historyGETMengambil riwayat klasifikasi pengguna.JWT ValidMendukung pagination (limit/offset)./api/statsGETMenampilkan statistik agregat klasifikasi.JWT ValidData di-cache (Redis) jika memungkinkan./minio/modelGETMengunduh bobot model dari MinIO (hanya dipanggil saat startup).Internal/Service TokenDipicu oleh backend service untuk loading model.5. Struktur Proyek Backend/backend/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   ├── classification.py  # Endpoint /api/classify
│   │   │   └── stats.py
│   │   └── dependencies.py        # JWT validation & RBAC logic
│   ├── core/
│   │   ├── config.py              # Environment Vars, MODEL_PATH/URL
│   │   └── security.py            # JWT, Bcrypt Hashing
│   ├── db/
│   │   ├── models.py              # PostgreSQL Models
│   │   └── session.py
│   ├── services/
│   │   ├── **inference.py** # PENTING: Class untuk loading & running YOLOv8
│   │   └── minio_client.py        # Klien untuk mengunduh bobot dari MinIO
│   └── main.py                    # FastAPI Startup & Events
├── Dockerfile
└── requirements.txt
6. Kebutuhan Non-Fungsional Utama & ImplementasiNF-IDAspekImplementasi BackendNF-04Response Time ($\le 2s$)Menggunakan FastAPI Asynchronous untuk I/O. Memuat model YOLOv8 ke memori sekali saat startup (@app.on_event("startup")).NF-06Security (JWT, HTTPS)Implementasi Middleware JWT di FastAPI. [cite_start]Menggunakan Bcrypt/Argon2 untuk password hashing[cite: 889].NF-08Scalability (Horizontal)Stateless API di dalam Docker Container. [cite_start]Dapat dengan mudah diduplikasi di belakang Load Balancer[cite: 529, 955].InferensiModel LoadingModul minio_client.py mengunduh bobot model (misalnya yolov8s.pt) ke penyimpanan lokal saat startup kontainer; inference.py memuat file tersebut ke PyTorch/GPU.7. Konfigurasi Docker Compose ModularFile ini menjalankan semua services yang dibutuhkan di lingkungan lokal.YAMLversion: '3.8'

services:
  # 1. Backend Service (FastAPI + YOLO Inference)
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: waste-classifier-backend
    restart: always
    # 🚨 PENTING: Gunakan runtime NVIDIA jika perlu akses GPU untuk inferensi cepat
    # runtime: nvidia 
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    
    ports:
      - "8000:8000"
    environment:
      # --- Koneksi Internal ---
      DATABASE_URL: postgresql+asyncpg://user:password@db:5432/waste_db
      REDIS_HOST: redis
      MINIO_ENDPOINT: minio:9000
      # --- Konfigurasi ML/Model ---
      MODEL_WEIGHTS_PATH: http://minio:9000/models/yolov8s_final.pt 
      # --- Konfigurasi Keamanan ---
      JWT_SECRET_KEY: ${JWT_SECRET_KEY} 

    depends_on:
      - db
      - redis
      - minio

  # 2. Database Service (PostgreSQL)
  db:
    image: postgres:15-alpine
    container_name: waste-classifier-db
    restart: always
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: waste_db
    volumes:
      - db_data:/var/lib/postgresql/data/

  # 3. Cache Service (Redis)
  redis:
    image: redis:7-alpine
    container_name: waste-classifier-redis
    restart: always

  # 4. Object Storage Service (MinIO)
  minio:
    image: minio/minio:latest
    container_name: waste-classifier-minio
    restart: always
    ports:
      - "9000:9000" # MinIO API
      - "9001:9001" # MinIO Console Web UI
    environment:
      MINIO_ROOT_USER: minio_user
      MINIO_ROOT_PASSWORD: minio_password
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data # Untuk menyimpan file bobot YOLOv8

volumes:
  db_data:
  minio_data: