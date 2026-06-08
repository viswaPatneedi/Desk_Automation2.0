# Docker Build and Cloud Deployment Guide

## Docker Image Built Successfully! ✅

The RDK Testing Dashboard Docker image has been built with:
- ✅ Python virtual environment (`/app/venv`)
- ✅ Email service support (Gmail SMTP)
- ✅ All dependencies installed
- ✅ Tesseract OCR for AI vision
- ✅ Production-ready with Gunicorn

## Image Details

```bash
Image Name: rdk-testing-dashboard
Tags: latest, 20260114
Size: ~6.58GB
Python: 3.11
Base: python:3.11-slim (Debian Trixie)
```

## Quick Start - Local Testing

### 1. Run the Container Locally

```bash
# Basic run (without email)
sudo docker run -d \
  -p 5000:5000 \
  --name rdk-testing \
  rdk-testing-dashboard:latest

# Run with email configured
sudo docker run -d \
  -p 5000:5000 \
  -e SENDER_PASSWORD="your-gmail-app-password" \
  -v $(pwd)/devices.json:/app/devices.json \
  -v $(pwd)/jobs.json:/app/jobs.json \
  -v $(pwd)/iteration_logs:/app/iteration_logs \
  -v $(pwd)/screenshots:/app/screenshots \
  --name rdk-testing \
  rdk-testing-dashboard:latest

# Access the application
http://localhost:5000
```

### 2. Using Docker Compose (Recommended)

```bash
# Create .env file with your email password
cp .env.example .env
nano .env  # Add your Gmail app password

# Start the application
sudo docker-compose up -d

# View logs
sudo docker-compose logs -f

# Stop the application
sudo docker-compose down
```

## Cloud Deployment Options

### Option 1: AWS ECS/ECR

#### Step 1: Tag and Push to ECR

```bash
# Login to AWS ECR
aws ecr get-login-password --region us-east-1 | \
  sudo docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name rdk-testing-dashboard

# Tag the image
sudo docker tag rdk-testing-dashboard:latest \
  <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/rdk-testing-dashboard:latest

# Push to ECR
sudo docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/rdk-testing-dashboard:latest
```

#### Step 2: Deploy to ECS

1. Create ECS cluster
2. Create task definition with:
   - Image: `<your-account-id>.dkr.ecr.us-east-1.amazonaws.com/rdk-testing-dashboard:latest`
   - Port: 5000
   - Environment variables (add your email password as secret)
3. Create ECS service
4. Configure Application Load Balancer

### Option 2: Google Cloud Platform (GCP)

```bash
# Authenticate with GCP
gcloud auth login
gcloud config set project <your-project-id>

# Tag and push to Google Container Registry
sudo docker tag rdk-testing-dashboard:latest gcr.io/<your-project-id>/rdk-testing-dashboard:latest
sudo docker push gcr.io/<your-project-id>/rdk-testing-dashboard:latest

# Deploy to Cloud Run
gcloud run deploy rdk-testing-dashboard \
  --image gcr.io/<your-project-id>/rdk-testing-dashboard:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5000 \
  --set-env-vars "SMTP_SERVER=smtp.gmail.com,SMTP_PORT=587,SENDER_EMAIL=cperdkemiddleware@gmail.com" \
  --set-secrets "SENDER_PASSWORD=gmail-app-password:latest"
```

### Option 3: Azure Container Instances

```bash
# Login to Azure
az login

# Create resource group
az group create --name rdk-testing-rg --location eastus

# Create Azure Container Registry
az acr create --resource-group rdk-testing-rg \
  --name rdktestingacr --sku Basic

# Login to ACR
az acr login --name rdktestingacr

# Tag and push
sudo docker tag rdk-testing-dashboard:latest rdktestingacr.azurecr.io/rdk-testing-dashboard:latest
sudo docker push rdktestingacr.azurecr.io/rdk-testing-dashboard:latest

# Deploy container instance
az container create \
  --resource-group rdk-testing-rg \
  --name rdk-testing-container \
  --image rdktestingacr.azurecr.io/rdk-testing-dashboard:latest \
  --dns-name-label rdk-testing \
  --ports 5000 \
  --environment-variables \
    SMTP_SERVER=smtp.gmail.com \
    SMTP_PORT=587 \
    SENDER_EMAIL=cperdkemiddleware@gmail.com \
  --secure-environment-variables \
    SENDER_PASSWORD=<your-gmail-app-password>
```

### Option 4: Docker Hub (Public Registry)

```bash
# Login to Docker Hub
sudo docker login

# Tag the image
sudo docker tag rdk-testing-dashboard:latest <your-dockerhub-username>/rdk-testing-dashboard:latest

# Push to Docker Hub
sudo docker push <your-dockerhub-username>/rdk-testing-dashboard:latest

# Now anyone can pull and run
docker run -d -p 5000:5000 \
  -e SENDER_PASSWORD="your-password" \
  <your-dockerhub-username>/rdk-testing-dashboard:latest
```

### Option 5: DigitalOcean App Platform

```bash
# Push to Docker Hub or DigitalOcean Container Registry first
# Then use DigitalOcean UI or CLI

doctl apps create --spec digitalocean-app-spec.yaml
```

Create `digitalocean-app-spec.yaml`:
```yaml
name: rdk-testing-dashboard
services:
  - name: web
    image:
      registry_type: DOCKER_HUB
      repository: <your-dockerhub-username>/rdk-testing-dashboard
      tag: latest
    envs:
      - key: SMTP_SERVER
        value: smtp.gmail.com
      - key: SMTP_PORT
        value: "587"
      - key: SENDER_EMAIL
        value: cperdkemiddleware@gmail.com
      - key: SENDER_PASSWORD
        value: <your-gmail-app-password>
        type: SECRET
    http_port: 5000
    instance_count: 1
    instance_size_slug: basic-xs
```

## Environment Variables for Cloud Deployment

Always configure these environment variables in your cloud platform:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=cperdkemiddleware@gmail.com
SENDER_PASSWORD=<your-16-char-gmail-app-password>
SECRET_KEY=<generate-a-secure-random-key>
```

## Security Best Practices

1. **Never commit passwords**: Use secrets management
   - AWS: Secrets Manager
   - GCP: Secret Manager
   - Azure: Key Vault
   - Docker: Docker Secrets

2. **Use HTTPS**: Configure SSL/TLS certificates

3. **Firewall**: Restrict access to port 5000

4. **Persistent Storage**: Mount volumes for:
   - `devices.json`
   - `jobs.json`
   - `iteration_logs/`
   - `screenshots/`

## Verify Running Container

```bash
# Check container status
sudo docker ps

# View logs
sudo docker logs rdk-testing

# Execute commands inside container
sudo docker exec -it rdk-testing /bin/bash

# Check virtual environment
sudo docker exec rdk-testing /app/venv/bin/python --version

# Test health endpoint
curl http://localhost:5000/health
```

## Troubleshooting

### Container won't start
```bash
sudo docker logs rdk-testing
sudo docker inspect rdk-testing
```

### Email not working
```bash
# Check environment variables
sudo docker exec rdk-testing env | grep SENDER

# Test email config inside container
sudo docker exec -it rdk-testing /app/venv/bin/python
>>> import os
>>> print(os.environ.get('SENDER_PASSWORD'))
```

### Permission issues
```bash
# Fix file permissions
sudo chown -R 1000:1000 ./iteration_logs ./screenshots
```

## Updating the Application

```bash
# Rebuild image
sudo docker build -t rdk-testing-dashboard:latest .

# Stop old container
sudo docker stop rdk-testing
sudo docker rm rdk-testing

# Start new container
sudo docker run -d -p 5000:5000 --name rdk-testing rdk-testing-dashboard:latest
```

## Cost Optimization

- **AWS ECS Fargate**: Pay per vCPU/GB per hour
- **GCP Cloud Run**: Pay per request + idle time
- **Azure Container Instances**: Pay per second
- **DigitalOcean**: Fixed monthly pricing starting at $5/month

## Next Steps

1. Choose your cloud platform
2. Set up container registry
3. Push the Docker image
4. Configure environment variables (especially email password)
5. Deploy the container
6. Set up domain and SSL certificate
7. Configure backup for persistent data

---

**Built on**: January 14, 2026  
**Docker Version**: 28.2.2  
**Image Size**: 6.58GB  
**Status**: ✅ Ready for Production Deployment
