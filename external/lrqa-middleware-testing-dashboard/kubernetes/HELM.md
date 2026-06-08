# Helm Chart for RDK Testing Dashboard (Optional)

If you prefer using Helm for deployment, create this chart structure:

```
helm-chart/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── secret.yaml
    └── pvc.yaml
```

## Create Helm Chart

```bash
# Install Helm if not already installed
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Create chart
helm create rdk-testing-dashboard

# Copy our manifests to templates/
cp kubernetes/*.yaml rdk-testing-dashboard/templates/

# Install
helm install rdk-testing ./rdk-testing-dashboard -n rdk-testing --create-namespace

# Upgrade
helm upgrade rdk-testing ./rdk-testing-dashboard -n rdk-testing

# Uninstall
helm uninstall rdk-testing -n rdk-testing
```

## values.yaml Example

```yaml
image:
  repository: rdk-testing-dashboard
  tag: latest
  pullPolicy: IfNotPresent

replicaCount: 1

service:
  type: ClusterIP
  port: 5000

ingress:
  enabled: true
  className: nginx
  host: rdk-testing.example.com
  tls:
    enabled: false

persistence:
  data:
    size: 5Gi
  logs:
    size: 10Gi
  screenshots:
    size: 5Gi

resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

smtp:
  server: smtp.gmail.com
  port: 587
  # Set these as secrets
  username: ""
  password: ""
  fromEmail: ""

secretKey: ""  # Generate random key
```

This allows easy configuration and upgrades via Helm.
