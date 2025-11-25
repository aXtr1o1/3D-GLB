# 3D-GLB Deployment Guide

**Project:** 3D-GLB  
**Version:** 1.0.0  
**Platform:** AWS EC2 Ubuntu 22.04 with GPU  
**Document Date:** October 26, 2025

## Overview

This guide documents the deployment of the 3D-GLB avatar generation platform on AWS EC2 infrastructure. The system processes front-facing selfie photographs through a 20-stage AI/ML pipeline to generate low-polygon GLB 3D avatars for VR and metaverse applications.

- **Processing Time:** 3-5 minutes per avatar
- **Infrastructure:** Single GPU-enabled EC2 instance
- **Storage:** Supabase cloud platform

---

## Production Requirements

### AWS Infrastructure

| Component | Specification |
|-----------|---------------|
| Instance Type | g4dn.xlarge |
| vCPUs | 4 |
| RAM | 16 GB |
| GPU | NVIDIA Tesla T4 (16GB VRAM) |
| Storage | 100GB GP3 EBS volume |
| Operating System | Ubuntu 22.04 LTS |

### Software Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| CUDA | 11.7 | GPU acceleration |
| Python | 3.7.9 | Legacy AI models (DECA, HairMapper) |
| Python | 3.11.0 | FastAPI backend |
| Blender | 2.79 | 3D rendering and GLB export |
| pyenv | 2.3+ | Python version management |
| FastAPI/Uvicorn | Latest | API server |
| Node.js | 18 LTS | Frontend runtime |
| PM2 | Latest | Process management |

### External Services

**Supabase:** Cloud storage and database
- Account required (Pro plan recommended: $25/month)
- Region should match EC2 instance region

**GitHub:** Private repository access
- Organizational credentials required

**Google Drive:** Model checkpoint download
- URL: https://drive.google.com/file/d/1CAcvtqD8XTkjr9C-6G4L12dkQVDZxQkz/view
- Size: ~15GB

---

## Deployment Procedure

### Phase 1: AWS Instance Setup

#### 1.1 Launch EC2 Instance

Configure instance with:
- AMI: Ubuntu Server 22.04 LTS (64-bit x86)
- Instance type: g4dn.xlarge
- Storage: 100GB GP3 volume
- Security group: Configure as needed
- Key pair: Generate or select existing RSA key

#### 1.2 Network Configuration

Allocate and associate Elastic IP to instance via EC2 console.

#### 1.3 Initial Connection

```bash
ssh -i /path/to/keypair.pem ubuntu@<ELASTIC_IP>
```

---

### Phase 2: System Configuration

#### 2.1 System Update

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl wget vim htop unzip \
  software-properties-common ca-certificates gnupg lsb-release
```

#### 2.2 NVIDIA CUDA 11.7

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt update
sudo apt install -y cuda-11-7
```

Configure environment:

```bash
echo 'export PATH=/usr/local/cuda-11.7/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.7/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
echo 'export CUDA_HOME=/usr/local/cuda-11.7' >> ~/.bashrc
source ~/.bashrc
```

Verify:

```bash
nvidia-smi
nvcc --version
```

#### 2.3 Python Environment Manager (pyenv)

Install dependencies:

```bash
sudo apt install -y libssl-dev libbz2-dev libreadline-dev libsqlite3-dev \
  libncursesw5-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
  tk-dev zlib1g-dev
```

Install pyenv:

```bash
curl https://pyenv.run | bash
```

Configure:

```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc
```

#### 2.4 Python Versions

```bash
pyenv install 3.7.9
pyenv install 3.11.0
```

#### 2.5 Blender 2.79

```bash
cd /tmp
wget https://download.blender.org/release/Blender2.79/blender-2.79-linux-glibc219-x86_64.tar.bz2
sudo tar -xjf blender-2.79-linux-glibc219-x86_64.tar.bz2 -C /opt/
sudo mv /opt/blender-2.79-linux-glibc219-x86_64 /opt/blender-2.79
sudo ln -s /opt/blender-2.79/blender /usr/local/bin/blender
```

Verify:

```bash
blender --version
```

#### 2.6 System Libraries

```bash
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 \
  libxrender-dev ffmpeg libcairo2-dev libgirepository1.0-dev \
  cmake libopenblas-dev liblapack-dev
```

---

### Phase 3: Application Deployment

#### 3.1 Repository Clone

```bash
cd ~
git clone <REPOSITORY_URL_API>
git clone <REPOSITORY_URL_FRONTEND>
```

#### 3.2 Python Dependencies

For Python 3.7.9:

```bash
cd ~/3D-GLB
pyenv local 3.7.9
pip install --upgrade pip
pip install -r requirements37.txt
```

For Python 3.11.0:

```bash
pyenv local 3.11.0
pip install --upgrade pip
pip install -r requirements311.txt
```

#### 3.3 Directory Structure Verification

Verify that the following directories exist in the repository:

```bash
ls -la DECA/data/
ls -la hair_mapper/HairMapper/ckpts/
```

If these directories are empty or missing checkpoint files, proceed to the model installation step.

#### 3.4 Create Processing Directories

Create temporary processing directories not tracked in Git:

```bash
mkdir -p Texture/input
mkdir -p Blender/ready\ to\ use\ model/head
mkdir -p hair_mapper/stylegan-encoder/{aligned_images,raw_images}
mkdir -p input Blender/output
```

#### 3.5 Model Checkpoint Installation

If model checkpoints are not present in the repository, download and install them:

```bash
pyenv local 3.11.0
pip install --upgrade pip gdown
```

Download model archive:

```bash
cd /tmp
gdown https://drive.google.com/uc?id=1CAcvtqD8XTkjr9C-6G4L12dkQVDZxQkz
```

Extract archive:

```bash
unzip 1CAcvtqD8XTkjr9C-6G4L12dkQVDZxQkz
```

Install DECA model checkpoints:

```bash
cd /tmp
cp -r DECA_data/* ~/3D-GLB/DECA/data/
```

Verify DECA installation:

```bash
ls -lh ~/3D-GLB/DECA/data/
```

Expected files:
- deca_model.tar
- flame2020.pkl
- head_template.obj
- landmark_embedding.npy
- mean_texture.jpg
- texture_data_256.npy
- uv_face_eye_mask.png
- uv_face_mask.png

Install HairMapper model checkpoints:

```bash
cd /tmp
cp -r hairmapper_ckpts/* ~/3D-GLB/hair_mapper/HairMapper/ckpts/
```

Verify HairMapper installation:

```bash
ls -lh ~/3D-GLB/hair_mapper/HairMapper/ckpts/
```

Expected checkpoint files (.pt or .pth format).

Clean up temporary files:

```bash
cd /tmp
rm -rf DECA_data hairmapper_ckpts 1CAcvtqD8XTkjr9C-6G4L12dkQVDZxQkz
```

#### 3.6 Environment Configuration

Create .env file:

```bash
cd ~/3D-GLB
nano .env
```

Required variables:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
SUPABASE_ANON_KEY=<anon_key>
SUPABASE_BUCKET=three-d-outputs
SUPABASE_PREFIX=blender/outputs
PYTHON_37_PATH=/home/ubuntu/.pyenv/versions/3.7.9/bin/python
PYTHON_311_PATH=/home/ubuntu/.pyenv/versions/3.11.0/bin/python
CUDA_HOME=/usr/local/cuda-11.7
MAX_WORKERS=1
```

Secure the file:

```bash
chmod 600 .env
```

---

### Phase 4: Supabase Setup

#### 4.1 Project Creation

Access https://supabase.com and create new project:
- Name: 3d-glb-storage
- Region: Match EC2 region
- Plan: Pro ($25/month for production)

#### 4.2 API Credentials

Navigate to Settings → API and document:
- Project URL (for SUPABASE_URL)
- anon/public key (for SUPABASE_ANON_KEY)
- service_role key (for SUPABASE_SERVICE_ROLE_KEY)

#### 4.3 Storage Bucket

Navigate to Storage section:

1. Create bucket: `three-d-outputs`
2. Enable "Public bucket"
3. Configure policies:
   - Public SELECT policy
   - Authenticated INSERT policy

#### 4.4 Database Table

Navigate to Table Editor and create `avatars` table:

**Columns:**
- `id` (uuid, primary key, auto-generated)
- `job_id` (text, nullable)
- `gender` (text, check constraint: 'male' or 'female')
- `filename` (text, required)
- `storage_bucket` (text, required)
- `storage_key` (text, required)
- `content_type` (text)
- `size_bytes` (bigint)
- `public_url` (text)
- `signed_url` (text)
- `created_at` (timestamp with time zone, default now())

**Indexes:**
- Index on `gender` column
- Index on `created_at` (descending)

**Row Level Security:**
- Enable RLS
- Create public SELECT policy
- Create authenticated INSERT policy

---

### Phase 5: Frontend (React) & PM2 Orchestration

#### 5.0 Prerequisites (Node.js on Ubuntu 22.04)

Install Node LTS (recommended: Node 18) and core tools:

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs build-essential
```

Verify:

```bash
node -v
npm -v
```

#### 5.1 PM2 & Static Server

Install PM2 globally (process manager) and serve (static file server for CRA builds):

```bash
sudo npm install -g pm2 serve
pm2 -v
```

You'll use PM2 to run:
- **Backend:** Uvicorn command (FastAPI)
- **Frontend:** serve -s build (production, static)

#### 5.2 Frontend Environment

In your frontend repo (CRA 5), set the API base so the browser calls your backend:

```bash
cd ~/3D-GLB-FRONTEND  # adjust to your path
echo 'REACT_APP_API_BASE_URL=http://<ELASTIC_IP>:8000' > .env
```

#### 5.3 Install & Build

```bash
# Install dependencies
npm install

# Build optimized static assets into ./build
npm run build
```

#### 5.4 Start Frontend with PM2

Exposes the frontend at port 3000:

```bash
# From the frontend root (so "build" exists):
pm2 start npx --name 3D-GLB-FRONTEND -- serve -s build -l 3000

# If build isn't done yet:
pm2 start npm --name 3D-GLB-FRONTEND -- start
```

**Configuration:**
- Name: 3D-GLB-FRONTEND
- Port: 3000 (adjust if you want a different public port)

Verify:

```bash
curl -I http://localhost:3000
```

From a browser: `http://<ELASTIC_IP>:3000`

> **Note:** Consider putting NGINX in front to serve 80/443 and reverse-proxy to 3000/8000. (You can add this later.)

#### 5.5 Start Backend with PM2 (FastAPI/Uvicorn)

Your backend already reads .env. Use the Python 3.11 interpreter path:

```bash
cd ~/3D-GLB

# Make sure your Python 3.11 deps are installed
pyenv local 3.11.0
pip install --upgrade pip
pip install -r requirements311.txt

# Start FastAPI via Uvicorn on :8000 under PM2
# (Use full Python path so PM2 restarts reliably.)
pm2 start "$(which python3.11)" \
  --name 3D-GLB-API \
  --interpreter none \
  -- -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Verify backend:

```bash
curl http://localhost:8000/docs
```

From a browser: `http://<ELASTIC_IP>:8000/docs`

#### 5.6 PM2 Autostart on Reboot

```bash
# Generate startup unit
pm2 startup systemd -u ubuntu --hp /home/ubuntu

# Persist the current process list
pm2 save
```

---

## PM2 Operations (Cheat Sheet)

```bash
# List processes
pm2 ls

# Logs (combined)
pm2 logs <pid>

# Specific logs
pm2 logs 3D-GLB-API
pm2 logs 3D-GLB-FRONTEND

# Restart / stop / delete
pm2 restart 3D-GLB-API
pm2 restart 3D-GLB-FRONTEND
pm2 stop 3D-GLB-API
pm2 delete 3D-GLB-FRONTEND

# Re-save process list after changes
pm2 save
```

---

## Frontend ↔ Backend Connectivity Test

**Backend:** Watch GPU usage while generating an avatar:

```bash
watch -n 1 nvidia-smi
```

Test endpoint:

```bash
curl -X POST "http://<ELASTIC_IP>:8000/upload" \
  -F "gender=male" \
  -F "file=@/path/to/selfie.jpg"
```

**Frontend:** Open `http://<ELASTIC_IP>:3000` and use the UI; network tab requests should hit `REACT_APP_API_BASE_URL` (port 8000).

---

## Update Procedure

### Backend

```bash
cd ~/3D-GLB
git pull origin main
pyenv local 3.11.0
pip install -r requirements311.txt
pm2 restart 3D-GLB-API
```

### Frontend

```bash
cd ~/3D-GLB-FRONTEND
git pull origin main
npm ci
npm run build
pm2 restart 3D-GLB-FRONTEND
```

---

## Simple NGINX Reverse Proxy (Optional)

You can skip this now. Add later for cleaner URLs and TLS.

- **Frontend:** `https://yourdomain` → proxy → `http://127.0.0.1:3000`
- **Backend:** `https://yourdomain/api` → proxy → `http://127.0.0.1:8000`

This also lets you close SG ports 3000/8000 publicly and only expose 80/443.

---

## Production Checklist

### Pre-Deployment

- [ ] AWS EC2 g4dn.xlarge instance launched
- [ ] Elastic IP allocated and associated
- [ ] Security group configured correctly
- [ ] Supabase account created
- [ ] GitHub repository access confirmed
- [ ] SSH key pair secured

### Post-Deployment (Backend)

- [ ] CUDA 11.7 installed and verified (`nvidia-smi`)
- [ ] Python 3.7.9 and 3.11.0 installed
- [ ] Blender 2.79 installed and accessible
- [ ] Model checkpoints deployed (15GB)
- [ ] `.env` file configured with Supabase credentials
- [ ] All Python dependencies installed
- [ ] Supabase bucket created and policies configured
- [ ] Database table created with proper schema
- [ ] API accessible at port 8000
- [ ] Test avatar generation completed successfully

### Post-Deployment (Frontend)

- [ ] Node 18 LTS installed
- [ ] PM2 and serve installed globally
- [ ] `.env` in frontend has `REACT_APP_API_BASE_URL=http://<ELASTIC_IP>:8000`
- [ ] `npm ci && npm run build` completed successfully
- [ ] Frontend started with PM2
- [ ] Frontend accessible at `http://<ELASTIC_IP>:3000`
- [ ] PM2 startup + save completed

### Security

- [ ] SSH access restricted to known IPs
- [ ] `.env` file permissions set to 600
- [ ] Supabase `service_role_key` confidential
- [ ] Security group follows least privilege
- [ ] EBS encryption enabled

---

## Cost Estimate

### Monthly Operating Cost (24/7)

| Item | Cost |
|------|------|
| EC2 g4dn.xlarge | $390 |
| Supabase (optional) | $25 |
| **Total** | **~$415** |

### Cost Optimization

- **Reserved Instance:** 40-60% savings (1-3 year commitment)
- **Scheduled operation:** Stop during off-hours

---

## Support

For issues or questions, please contact the development team or refer to the project documentation.

---

**Document Version:** 1.0.0  
**Last Updated:** October 26, 2025
