#!/bin/bash
# Quick deployment script for Kubernetes

set -e

echo "🚀 RDK Testing Dashboard - Kubernetes Deployment Script"
echo "========================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl first.${NC}"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster. Please configure kubectl.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ kubectl configured and cluster accessible${NC}"
echo ""

# Prompt for configuration
read -p "Enter your Docker image (e.g., your-registry/rdk-testing-dashboard:latest): " DOCKER_IMAGE
read -p "Enter your domain for Ingress (or press Enter to skip): " DOMAIN
read -p "Deploy with Ingress? (y/n): " USE_INGRESS

echo ""
echo -e "${YELLOW}📝 Configuration Summary:${NC}"
echo "Docker Image: $DOCKER_IMAGE"
echo "Domain: ${DOMAIN:-Not configured}"
echo "Use Ingress: ${USE_INGRESS}"
echo ""
read -p "Continue with deployment? (y/n): " CONTINUE

if [ "$CONTINUE" != "y" ]; then
    echo "Deployment cancelled."
    exit 0
fi

# Update deployment image
if [ ! -z "$DOCKER_IMAGE" ]; then
    echo -e "${YELLOW}📝 Updating deployment image...${NC}"
    sed -i.bak "s|image: rdk-testing-dashboard:latest|image: $DOCKER_IMAGE|g" kubernetes/deployment.yaml
fi

# Update ingress domain
if [ ! -z "$DOMAIN" ]; then
    echo -e "${YELLOW}📝 Updating ingress domain...${NC}"
    sed -i.bak "s|rdk-testing.example.com|$DOMAIN|g" kubernetes/ingress.yaml
fi

# Create namespace
echo -e "${YELLOW}📦 Creating namespace...${NC}"
kubectl apply -f kubernetes/namespace.yaml

# Create secrets (prompt for values)
echo -e "${YELLOW}🔐 Setting up secrets...${NC}"
read -p "Enter SMTP username: " SMTP_USER
read -sp "Enter SMTP password: " SMTP_PASS
echo ""
read -p "Enter SMTP from email: " SMTP_FROM
read -sp "Enter Flask secret key (or press Enter to generate): " SECRET_KEY
echo ""

if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(openssl rand -base64 32)
    echo "Generated random secret key"
fi

kubectl create secret generic rdk-secrets \
    --from-literal=SMTP_USERNAME="$SMTP_USER" \
    --from-literal=SMTP_PASSWORD="$SMTP_PASS" \
    --from-literal=SMTP_FROM_EMAIL="$SMTP_FROM" \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    -n rdk-testing --dry-run=client -o yaml | kubectl apply -f -

# Apply remaining manifests
echo -e "${YELLOW}🎯 Applying Kubernetes manifests...${NC}"
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/init-data-job.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml

if [ "$USE_INGRESS" = "y" ]; then
    kubectl apply -f kubernetes/ingress.yaml
fi

# Wait for deployment
echo -e "${YELLOW}⏳ Waiting for deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/rdk-testing-dashboard -n rdk-testing || true

# Show status
echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📊 Deployment Status:"
kubectl get all -n rdk-testing

echo ""
echo "📋 Access Methods:"
echo "1. Port Forward (Development):"
echo "   kubectl port-forward -n rdk-testing svc/rdk-testing-service 5000:5000"
echo "   Then access: http://localhost:5000"
echo ""
if [ "$USE_INGRESS" = "y" ] && [ ! -z "$DOMAIN" ]; then
    echo "2. Ingress (Production):"
    echo "   http://$DOMAIN"
    echo ""
fi

echo "📝 Useful Commands:"
echo "View logs:    kubectl logs -f deployment/rdk-testing-dashboard -n rdk-testing"
echo "Get pods:     kubectl get pods -n rdk-testing"
echo "Describe pod: kubectl describe pod -n rdk-testing -l app=device-testing-dashboard"
echo "Delete all:   kubectl delete namespace rdk-testing"
echo ""
echo -e "${GREEN}🎉 Done!${NC}"
