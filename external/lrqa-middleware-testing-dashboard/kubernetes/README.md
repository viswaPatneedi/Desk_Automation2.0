# Kubernetes Deployment Guide for RDK Device Testing Dashboard

## Prerequisites

1. **Kubernetes cluster** (v1.19+)
   - Minikube, k3s, or cloud provider (EKS, GKE, AKS)
2. **kubectl** configured and connected to your cluster
3. **Docker image** built and pushed to a registry
4. **Persistent storage** provider in your cluster
5. **Ingress controller** (nginx, traefik) if using Ingress

## Quick Start

### 1. Build and Push Docker Image

```bash
# Build the Docker image
docker build -t your-registry/rdk-testing-dashboard:latest .

# Push to your container registry
docker push your-registry/rdk-testing-dashboard:latest

# Or for local development with Minikube
eval $(minikube docker-env)
docker build -t rdk-testing-dashboard:latest .
```

### 2. Update Kubernetes Configuration

Edit the following files before deployment:

**kubernetes/deployment.yaml**
```yaml
# Line 26: Update image name
image: your-registry/rdk-testing-dashboard:latest
```

**kubernetes/secret.yaml**
```yaml
# Update with your actual credentials
SMTP_USERNAME: "your-email@gmail.com"
SMTP_PASSWORD: "your-app-password"
SECRET_KEY: "generate-a-random-secret-key"
```

**kubernetes/ingress.yaml** (if using)
```yaml
# Line 32: Update domain
host: rdk-testing.example.com
```

### 3. Deploy to Kubernetes

```bash
# Apply all manifests in order
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/init-data-job.yaml  # Initialize data files
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/ingress.yaml  # Optional
```

Or deploy everything at once:
```bash
kubectl apply -f kubernetes/
```

### 4. Verify Deployment

```bash
# Check namespace
kubectl get all -n rdk-testing

# Check pod status
kubectl get pods -n rdk-testing

# Check logs
kubectl logs -f deployment/rdk-testing-dashboard -n rdk-testing

# Check persistent volumes
kubectl get pvc -n rdk-testing
```

### 5. Access the Application

**Option A: Port Forward (Development)**
```bash
kubectl port-forward -n rdk-testing svc/rdk-testing-service 5000:5000
# Access at http://localhost:5000
```

**Option B: NodePort (Bare Metal)**
```bash
# Uncomment NodePort section in service.yaml
kubectl apply -f kubernetes/service.yaml
# Access at http://<node-ip>:30500
```

**Option C: LoadBalancer (Cloud)**
```bash
# Uncomment LoadBalancer section in service.yaml
kubectl apply -f kubernetes/service.yaml
kubectl get svc -n rdk-testing  # Get external IP
# Access at http://<external-ip>
```

**Option D: Ingress (Production)**
```bash
# Ensure ingress controller is installed
kubectl apply -f kubernetes/ingress.yaml
# Access at http://rdk-testing.example.com
```

## Network Configuration

### Device Access
The application needs SSH access to test devices on your network.

**Option 1: Same Network (Recommended)**
- Deploy cluster on same network as test devices
- Pods can directly reach device IPs (10.0.0.x)

**Option 2: Network Policy**
```yaml
# Create network policy allowing egress to device network
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-device-access
  namespace: rdk-testing
spec:
  podSelector:
    matchLabels:
      app: device-testing-dashboard
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 10.0.0.0/24  # Your device network
    ports:
    - protocol: TCP
      port: 10022  # SSH port
```

**Option 3: External Service**
```yaml
# Create external service for iTach IR blaster
apiVersion: v1
kind: Service
metadata:
  name: itach-ir-external
  namespace: rdk-testing
spec:
  type: ExternalName
  externalName: 10.0.0.33  # iTach IP
  ports:
  - port: 4998
```

## Configuration Management

### Update Secrets
```bash
# Update SMTP credentials
kubectl create secret generic rdk-secrets \
  --from-literal=SMTP_USERNAME='new-email@gmail.com' \
  --from-literal=SMTP_PASSWORD='new-password' \
  --from-literal=SMTP_FROM_EMAIL='new-email@gmail.com' \
  --from-literal=SECRET_KEY='new-secret-key' \
  --dry-run=client -o yaml | kubectl apply -n rdk-testing -f -

# Restart deployment to pick up changes
kubectl rollout restart deployment/rdk-testing-dashboard -n rdk-testing
```

### Update ConfigMap
```bash
# Edit configuration
kubectl edit configmap rdk-config -n rdk-testing

# Restart deployment
kubectl rollout restart deployment/rdk-testing-dashboard -n rdk-testing
```

### Copy IR Keycodes to Persistent Volume
```bash
# Copy your ir_keycodes.json to the pod
kubectl cp ir_keycodes.json rdk-testing/rdk-testing-dashboard-<pod-id>:/app/ir_keycodes.json
```

## Persistent Data Management

### Backup Data
```bash
# Backup all data files
kubectl exec -n rdk-testing deployment/rdk-testing-dashboard -- tar czf /tmp/backup.tar.gz \
  devices.json jobs.json device_job_queue.json device_locks.json \
  saved_sequences.json app_state.json ir_keycodes.json reset_codes.json

# Copy backup to local
kubectl cp rdk-testing/rdk-testing-dashboard-<pod-id>:/tmp/backup.tar.gz ./backup.tar.gz
```

### Restore Data
```bash
# Copy backup to pod
kubectl cp ./backup.tar.gz rdk-testing/rdk-testing-dashboard-<pod-id>:/tmp/backup.tar.gz

# Extract
kubectl exec -n rdk-testing deployment/rdk-testing-dashboard -- \
  tar xzf /tmp/backup.tar.gz -C /app
```

## Scaling Considerations

### Single Replica (Default)
- **Recommended** for file-based state management
- Uses `strategy.type: Recreate` to ensure one pod at a time
- Device locks and job queues work correctly

### Multiple Replicas (Advanced)
To scale beyond 1 replica, you need:
1. **External database** (PostgreSQL/MySQL) instead of JSON files
2. **Redis** for distributed locks and job queues
3. **Shared storage** (ReadWriteMany PVC) or object storage (S3)

```yaml
# Example: Use NFS for shared storage
apiVersion: v1
kind: PersistentVolume
metadata:
  name: rdk-shared-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteMany
  nfs:
    server: nfs-server.example.com
    path: "/exports/rdk-data"
```

## Monitoring and Logging

### Health Checks
```bash
# Check liveness probe
kubectl exec -n rdk-testing deployment/rdk-testing-dashboard -- curl http://localhost:5000/health

# Check readiness probe
kubectl describe pod -n rdk-testing -l app=device-testing-dashboard
```

### View Logs
```bash
# Real-time logs
kubectl logs -f deployment/rdk-testing-dashboard -n rdk-testing

# Previous pod logs (if crashed)
kubectl logs deployment/rdk-testing-dashboard -n rdk-testing --previous

# All logs
kubectl logs -n rdk-testing --all-containers=true -l app=device-testing-dashboard
```

### Resource Usage
```bash
# Check resource consumption
kubectl top pod -n rdk-testing

# Check node allocation
kubectl describe node | grep -A 5 "Allocated resources"
```

## Troubleshooting

### Pod Not Starting
```bash
# Check pod events
kubectl describe pod -n rdk-testing -l app=device-testing-dashboard

# Check pod status
kubectl get pods -n rdk-testing -o wide

# Check logs
kubectl logs -n rdk-testing deployment/rdk-testing-dashboard
```

### Storage Issues
```bash
# Check PVC status
kubectl get pvc -n rdk-testing

# Check PV status
kubectl get pv

# Describe PVC for events
kubectl describe pvc rdk-data-pvc -n rdk-testing
```

### Network Issues
```bash
# Test SSH connectivity from pod
kubectl exec -n rdk-testing deployment/rdk-testing-dashboard -- \
  ssh -p 10022 root@10.0.0.250 'echo "SSH working"'

# Test iTach connectivity
kubectl exec -n rdk-testing deployment/rdk-testing-dashboard -- \
  nc -zv 10.0.0.33 4998
```

### Permission Issues
```bash
# Check file permissions in pod
kubectl exec -n rdk-testing deployment/rdk-testing-dashboard -- \
  ls -la /app/*.json

# Fix permissions
kubectl exec -n rdk-testing deployment/rdk-testing-dashboard -- \
  chown -R 1000:1000 /app
```

## Security Best Practices

1. **Use Secrets** for sensitive data (SMTP, SSH passwords)
2. **Network Policies** to restrict pod communication
3. **RBAC** for access control
4. **Pod Security Standards** (restricted mode)
5. **TLS** for Ingress with cert-manager
6. **Regular Updates** of base image and dependencies

### Example: Enable TLS with cert-manager
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Update ingress.yaml annotations and apply
kubectl apply -f kubernetes/ingress.yaml
```

## Cleanup

```bash
# Delete all resources
kubectl delete -f kubernetes/

# Or delete namespace (removes everything)
kubectl delete namespace rdk-testing

# Delete PersistentVolumes (if needed)
kubectl delete pv <pv-name>
```

## Production Checklist

- [ ] Docker image pushed to private registry
- [ ] Secrets updated with real credentials
- [ ] Resource limits configured appropriately
- [ ] Persistent volumes sized correctly
- [ ] Network policies configured
- [ ] Ingress/LoadBalancer configured
- [ ] TLS certificates configured
- [ ] Monitoring and alerting set up
- [ ] Backup strategy implemented
- [ ] Disaster recovery plan documented

## Support

For issues specific to Kubernetes deployment:
1. Check pod logs: `kubectl logs -n rdk-testing deployment/rdk-testing-dashboard`
2. Check events: `kubectl get events -n rdk-testing --sort-by='.lastTimestamp'`
3. Verify network connectivity to test devices
4. Review resource constraints and adjust as needed
