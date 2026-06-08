#!/bin/bash
# Restore backup files

cd /home/pi/Desktop/viswa/Latest_Enhancement/Enhancement

if [ -z "$1" ]; then
    echo "Available backups:"
    ls -lh backups/*_backup_*.html 2>/dev/null || echo "No backups found"
    echo ""
    echo "Usage: ./restore_backup.sh TIMESTAMP"
    echo "Example: ./restore_backup.sh 20251217_115955"
    exit 1
fi

TIMESTAMP=$1

if [ -f "backups/index_backup_${TIMESTAMP}.html" ]; then
    cp "backups/index_backup_${TIMESTAMP}.html" templates/index.html
    echo "✓ Restored index.html from backup ${TIMESTAMP}"
fi

if [ -f "backups/results_backup_${TIMESTAMP}.html" ]; then
    cp "backups/results_backup_${TIMESTAMP}.html" templates/results.html
    echo "✓ Restored results.html from backup ${TIMESTAMP}"
fi

echo ""
echo "✓ Restore complete. Please refresh your browser."
