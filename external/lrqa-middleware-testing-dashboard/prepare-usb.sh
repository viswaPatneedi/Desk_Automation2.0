#!/bin/bash
# USB_DEPLOYMENT_SETUP.sh - Prepare USB with all deployment files

# Run this on the DEVELOPMENT MACHINE to prepare USB

USB_MOUNT_POINT="/media/usb"
SOURCE_DIR="/home/lrqa/Desktop/viswa/Latest_Enhancement/Enhancement"

echo "=========================================="
echo "🔧 USB DEPLOYMENT PACKAGE SETUP"
echo "=========================================="
echo ""

# Check if USB is mounted
if [ ! -d "$USB_MOUNT_POINT" ]; then
    echo "⚠️  USB not mounted at $USB_MOUNT_POINT"
    echo "Please mount USB manually first:"
    echo "  mkdir -p $USB_MOUNT_POINT"
    echo "  sudo mount /dev/sda1 $USB_MOUNT_POINT"
    exit 1
fi

echo "📱 USB mounted at: $USB_MOUNT_POINT"
echo ""

# Copy deployment scripts
echo "📋 Copying deployment scripts..."
cp "$SOURCE_DIR/rpi4-deploy.sh" "$USB_MOUNT_POINT/"
chmod +x "$USB_MOUNT_POINT/rpi4-deploy.sh"
echo "   ✅ rpi4-deploy.sh copied"

cp "$SOURCE_DIR/rpi4-setup-assistant.py" "$USB_MOUNT_POINT/"
chmod +x "$USB_MOUNT_POINT/rpi4-setup-assistant.py"
echo "   ✅ rpi4-setup-assistant.py copied"

# Copy documentation
echo ""
echo "📚 Copying documentation..."
cp "$SOURCE_DIR/RPI4_TERMINAL_COMMANDS.md" "$USB_MOUNT_POINT/"
echo "   ✅ RPI4_TERMINAL_COMMANDS.md copied"

cp "$SOURCE_DIR/RPI4_COMPLETE_DEPLOYMENT_GUIDE.md" "$USB_MOUNT_POINT/" 2>/dev/null || \
  echo "   ℹ️  RPI4_COMPLETE_DEPLOYMENT_GUIDE.md not found (optional)"

# Copy configuration files
echo ""
echo "⚙️  Copying configuration files..."
cp "$SOURCE_DIR/docker-compose.yml" "$USB_MOUNT_POINT/"
echo "   ✅ docker-compose.yml copied"

cp "$SOURCE_DIR/requirements.txt" "$USB_MOUNT_POINT/"
echo "   ✅ requirements.txt copied"

# Verify Docker image export
echo ""
echo "🐳 Checking Docker image..."
if ls "$SOURCE_DIR/lrqa-middleware-latest.tar" >/dev/null 2>&1; then
    echo "   ✅ Docker image found: $(ls -lh $SOURCE_DIR/lrqa-middleware-latest.tar | awk '{print $5}')"
    echo "   📋 Copying Docker image to USB (this may take 5-10 minutes)..."
    cp "$SOURCE_DIR/lrqa-middleware-latest.tar" "$USB_MOUNT_POINT/"
    echo "   ✅ Docker image copied"
elif ls "$SOURCE_DIR/lrqa-middleware-latest.tar.gz" >/dev/null 2>&1; then
    echo "   ✅ Docker image (compressed): $(ls -lh $SOURCE_DIR/lrqa-middleware-latest.tar.gz | awk '{print $5}')"
    echo "   📋 Copying Docker image to USB..."
    cp "$SOURCE_DIR/lrqa-middleware-latest.tar.gz" "$USB_MOUNT_POINT/"
    echo "   ✅ Docker image copied"
else
    echo "   ⚠️  Docker image not found"
    echo "   Run this first: sudo docker save -o lrqa-middleware-latest.tar lrqa-middleware:latest"
fi

echo ""
echo "=========================================="
echo "📦 USB DEPLOYMENT PACKAGE READY"
echo "=========================================="
echo ""
echo "USB Contents:"
ls -lh "$USB_MOUNT_POINT"
echo ""
echo "✅ Next steps:"
echo "1. Safely eject USB"
echo "2. Connect USB to new R-Pi 4"
echo "3. See RPI4_TERMINAL_COMMANDS.md for deployment instructions"
echo ""
