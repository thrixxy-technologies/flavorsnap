#!/bin/bash

# Database Backup Automation Script
BACKUP_DIR="/backups/db"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
DATABASE_NAME="flavorsnap"
BACKUP_FILE="$BACKUP_DIR/$DATABASE_NAME-backup-$TIMESTAMP.sql.gz"

mkdir -p $BACKUP_DIR

echo "Starting backup of $DATABASE_NAME..."

pg_dump -h localhost -U flavorsnap $DATABASE_NAME | gzip > $BACKUP_FILE

if [ $? -eq 0 ]; then
    echo "Backup successful: $BACKUP_FILE"
    # Keep only the last 7 days of backups
    find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
else
    echo "Backup failed!"
    exit 1
fi

# Upload to S3 (optional)
# aws s3 cp $BACKUP_FILE s3://flavorsnap-backups/database/
