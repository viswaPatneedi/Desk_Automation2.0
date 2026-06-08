# Docker Deployment Guide

This guide explains how to deploy the RDK Testing Dashboard using Docker.

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 1.29 or later
- At least 2GB of available disk space

## Quick Start

### 1. Build and Start the Application

```bash
# Build and start the container
docker-compose up -d

# Or build explicitly first
docker-compose build
docker-compose up -d
```

The application will be available at `http://localhost:5000`

### 2. View Logs

```bash
# View real-time logs
docker-compose logs -f

# View logs for web service only
docker-compose logs -f web
```

### 3. Stop the Application

```bash
# Stop containers
docker-compose down

# Stop and remove volumes (WARNING: This will delete data)
docker-compose down -v
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
SECRET_KEY=your-unique-secret-key
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

### Data Persistence

The following directories and files are mounted as volumes to persist data:

- `devices.json` - Device registry
- `jobs.json` - Job definitions
- `device_job_queue.json` - Job queue state
- `device_locks.json` - Device lock state
- `saved_sequences.json` - Saved test sequences
- `iteration_logs/` - Execution logs
- `screenshots/` - Screenshot captures

These files persist even when containers are stopped or removed (unless you use `docker-compose down -v`).

## Production Deployment

### Using Custom Port

Edit `docker-compose.yml` to change the port mapping:

```yaml
ports:
  - "8080:5000"  # Host port 8080 -> Container port 5000
```

### Running Behind a Reverse Proxy (Nginx/Apache)

1. Change port binding to localhost only:

```yaml
ports:
  - "127.0.0.1:5000:5000"
```

2. Configure your reverse proxy to forward to `localhost:5000`

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # For SSE (Server-Sent Events) log streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```

### SSL/HTTPS

For production, use a reverse proxy (Nginx) with Let's Encrypt SSL certificates, or modify the docker-compose.yml to include SSL certificates.

## Maintenance

### Update Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup Data

```bash
# Backup all data files
docker-compose exec web tar -czf /tmp/backup.tar.gz \
    devices.json jobs.json device_job_queue.json \
    device_locks.json saved_sequences.json \
    iteration_logs screenshots

# Copy backup out of container
docker cp rdk-testing-dashboard:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz
```

### Restore Data

```bash
# Copy backup into container
docker cp ./backup-20260112.tar.gz rdk-testing-dashboard:/tmp/backup.tar.gz

# Extract backup
docker-compose exec web tar -xzf /tmp/backup.tar.gz -C /app
```

### Shell Access

```bash
# Access container shell
docker-compose exec web bash

# Or using docker directly
docker exec -it rdk-testing-dashboard bash
```

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker-compose logs web
```

### Permission Issues

Ensure the host directories have proper permissions:
```bash
chmod -R 755 iteration_logs screenshots
```

### Port Already in Use

If port 5000 is already in use, change it in `docker-compose.yml`:
```yaml
ports:
  - "5001:5000"  # Use port 5001 instead
```

### Health Check Failing

Check if the application is responding:
```bash
docker-compose exec web curl http://localhost:5000/health
```

### SSH Connectivity Issues

The container needs network access to SSH into your test devices (port 10022 by default). Ensure:
- Devices are reachable from the Docker host
- Firewall rules allow connections
- Network mode is appropriate (default bridge should work)

## Docker Commands Reference

```bash
# Build without cache
docker-compose build --no-cache

# Start in foreground (see logs directly)
docker-compose up

# Start in background (detached)
docker-compose up -d

# Stop containers
docker-compose stop

# Start stopped containers
docker-compose start

# Restart containers
docker-compose restart

# Remove containers (keeps volumes)
docker-compose down

# Remove containers and volumes (WARNING: deletes data)
docker-compose down -v

# View container status
docker-compose ps

# View resource usage
docker stats rdk-testing-dashboard
```

## Architecture Notes

- The application runs with Gunicorn (4 workers) for production-grade performance
- Health checks ensure the container is healthy
- Automatic restart on failure (unless-stopped policy)
- All device operations are performed via SSH from the container
- Real-time log streaming uses Server-Sent Events (SSE)
- Tesseract OCR is included for AI vision features

## Security Considerations

1. **Change the SECRET_KEY** in production (use a strong random value)
2. **Protect SMTP credentials** - use environment variables or secrets management
3. **Secure device passwords** - stored in devices.json (consider encryption)
4. **Firewall rules** - restrict access to port 5000 if needed
5. **Regular updates** - keep base images and dependencies updated

## Support

For issues or questions, refer to the main [README.md](README.md) or project documentation.
