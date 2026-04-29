#!/bin/bash

# FlavorSnap Backup Script
# Automated backup system for data and model files
# Author: FlavorSnap Team
# Version: 1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="flavorsnap_backup_${TIMESTAMP}"
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    local deps=("tar" "gzip" "rsync" "sha256sum")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            error_exit "Required dependency '$dep' is not installed"
        fi
    done
    
    log "All dependencies are available"
}

# Create backup directory structure
create_backup_structure() {
    log "Creating backup directory structure..."
    
    local backup_path="${BACKUP_DIR}/${BACKUP_NAME}"
    mkdir -p "$backup_path"/{models,dataset,uploads,config,scripts,database,logs}
    
    echo "$backup_path"
}

# Backup model files
backup_models() {
    local backup_path="$1"
    log "Backing up model files..."
    
    # Main model file
    if [[ -f "${PROJECT_ROOT}/model.pth" ]]; then
        cp "${PROJECT_ROOT}/model.pth" "$backup_path/models/"
        log "Copied model.pth"
    else
        log "WARNING: model.pth not found"
    fi
    
    # Food classes file
    if [[ -f "${PROJECT_ROOT}/food_classes.txt" ]]; then
        cp "${PROJECT_ROOT}/food_classes.txt" "$backup_path/models/"
        log "Copied food_classes.txt"
    else
        log "WARNING: food_classes.txt not found"
    fi
    
    # Model registry and related files
    if [[ -d "${PROJECT_ROOT}/ml-model-api" ]]; then
        find "${PROJECT_ROOT}/ml-model-api" -name "*.py" -path "*/model*" -exec cp {} "$backup_path/models/" \;
        log "Copied model-related Python files"
    fi
}

# Backup dataset
backup_dataset() {
    local backup_path="$1"
    log "Backing up dataset..."
    
    if [[ -d "${PROJECT_ROOT}/dataset" ]]; then
        rsync -av --exclude="*.tmp" --exclude="*.cache" "${PROJECT_ROOT}/dataset/" "$backup_path/dataset/"
        log "Backed up dataset directory"
    else
        log "WARNING: dataset directory not found"
    fi
}

# Backup user uploads
backup_uploads() {
    local backup_path="$1"
    log "Backing up user uploads..."
    
    if [[ -d "${PROJECT_ROOT}/uploads" ]]; then
        rsync -av --exclude="*.tmp" "${PROJECT_ROOT}/uploads/" "$backup_path/uploads/"
        log "Backed up uploads directory"
    else
        log "WARNING: uploads directory not found"
    fi
}

# Backup configuration files
backup_config() {
    local backup_path="$1"
    log "Backing up configuration files..."
    
    # Package.json files
    find "$PROJECT_ROOT" -name "package.json" -not -path "*/node_modules/*" -exec cp {} "$backup_path/config/" \;
    
    # Requirements files
    find "$PROJECT_ROOT" -name "requirements.txt" -exec cp {} "$backup_path/config/" \;
    
    # Environment files (if they exist)
    find "$PROJECT_ROOT" -name ".env*" -not -name ".env.example" -exec cp {} "$backup_path/config/" \;
    
    # Configuration files
    local config_files=("Cargo.toml" "tsconfig.json" "next.config.ts" "eslint.config.mjs")
    for config_file in "${config_files[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${config_file}" ]]; then
            cp "${PROJECT_ROOT}/${config_file}" "$backup_path/config/"
        fi
        if [[ -f "${PROJECT_ROOT}/frontend/${config_file}" ]]; then
            cp "${PROJECT_ROOT}/frontend/${config_file}" "$backup_path/config/"
        fi
    done
    
    log "Backed up configuration files"
}

# Backup important scripts
backup_scripts() {
    local backup_path="$1"
    log "Backing up important scripts..."
    
    # Backup scripts directory
    if [[ -d "$SCRIPT_DIR" ]]; then
        cp -r "$SCRIPT_DIR" "$backup_path/scripts/"
        log "Backed up scripts directory"
    fi
    
    # Setup scripts
    find "$PROJECT_ROOT" -name "setup.*" -exec cp {} "$backup_path/scripts/" \;
    
    # Training notebook
    if [[ -f "${PROJECT_ROOT}/train_model.ipynb" ]]; then
        cp "${PROJECT_ROOT}/train_model.ipynb" "$backup_path/scripts/"
    fi
    
    log "Backed up scripts and notebooks"
}

# Backup database files (if any)
backup_database() {
    local backup_path="$1"
    log "Backing up database files..."
    
    # Look for common database files
    local db_patterns=("*.db" "*.sqlite" "*.sqlite3" "*.sql")
    
    for pattern in "${db_patterns[@]}"; do
        find "$PROJECT_ROOT" -name "$pattern" -not -path "*/node_modules/*" -not -path "*/.git/*" -exec cp {} "$backup_path/database/" \;
    done
    
    # Check for any data directories
    if [[ -d "${PROJECT_ROOT}/data" ]]; then
        rsync -av "${PROJECT_ROOT}/data/" "$backup_path/database/"
    fi
    
    log "Backed up database files"
}

# Create backup metadata
create_metadata() {
    local backup_path="$1"
    log "Creating backup metadata..."
    
    cat > "$backup_path/backup_info.json" << EOF
{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$TIMESTAMP",
    "created_by": "$(whoami)",
    "hostname": "$(hostname)",
    "project_root": "$PROJECT_ROOT",
    "git_branch": "$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo 'unknown')",
    "git_commit": "$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "backup_version": "1.0.0",
    "total_size_mb": "$(du -sm "$backup_path" | cut -f1)",
    "file_count": "$(find "$backup_path" -type f | wc -l)"
}
EOF
    
    log "Created backup metadata"
}

# Create checksums
create_checksums() {
    local backup_path="$1"
    log "Creating file checksums..."
    
    find "$backup_path" -type f -not -name "checksums.sha256" -exec sha256sum {} \; > "$backup_path/checksums.sha256"
    log "Created SHA256 checksums"
}

# Compress backup
compress_backup() {
    local backup_path="$1"
    log "Compressing backup..."
    
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    
    local compressed_size=$(du -sm "${BACKUP_NAME}.tar.gz" | cut -f1)
    log "Backup compressed: ${BACKUP_NAME}.tar.gz (${compressed_size}MB)"
    
    # Remove uncompressed directory
    rm -rf "$BACKUP_NAME"
    
    echo "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
}

# Cleanup old backups
cleanup_old_backups() {
    local keep_count="${1:-7}"
    log "Cleaning up old backups (keeping last $keep_count)..."
    
    cd "$BACKUP_DIR"
    ls -t flavorsnap_backup_*.tar.gz 2>/dev/null | tail -n +$((keep_count + 1)) | xargs -r rm -f
    
    log "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"
    log "Verifying backup integrity..."
    
    # Test tar file
    if ! tar -tzf "$backup_file" > /dev/null 2>&1; then
        error_exit "Backup file is corrupted or incomplete"
    fi
    
    log "Backup integrity verified"
}

# Send notification (optional)
send_notification() {
    local status="$1"
    local backup_file="$2"
    
    # This is a placeholder for notification system
    # You can integrate with email, Slack, Discord, etc.
    log "Backup $status: $backup_file"
    
    # Example webhook call (commented out):
    # curl -X POST -H 'Content-type: application/json' \
    #     --data "{\"text\":\"FlavorSnap backup $status: $(basename "$backup_file")\"}" \
    #     "YOUR_WEBHOOK_URL"
}

# Main backup function
main() {
    log "Starting FlavorSnap backup process..."
    
    # Parse command line arguments
    local keep_count=7
    local skip_cleanup=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --keep-count)
                keep_count="$2"
                shift 2
                ;;
            --skip-cleanup)
                skip_cleanup=true
                shift
                ;;
            --help)
                echo "Usage: $0 [--keep-count N] [--skip-cleanup]"
                echo "  --keep-count N: Keep last N backups (default: 7)"
                echo "  --skip-cleanup: Skip cleanup of old backups"
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done
    
    # Execute backup steps
    check_dependencies
    
    local backup_path
    backup_path=$(create_backup_structure)
    
    backup_models "$backup_path"
    backup_dataset "$backup_path"
    backup_uploads "$backup_path"
    backup_config "$backup_path"
    backup_scripts "$backup_path"
    backup_database "$backup_path"
    
    create_metadata "$backup_path"
    create_checksums "$backup_path"
    
    local backup_file
    backup_file=$(compress_backup "$backup_path")
    
    verify_backup "$backup_file"
    
    if [[ "$skip_cleanup" != "true" ]]; then
        cleanup_old_backups "$keep_count"
    fi
    
    log "Backup completed successfully: $backup_file"
    send_notification "completed" "$backup_file"
    
    echo "Backup completed: $backup_file"
}

# Run main function with all arguments
main "$@"
