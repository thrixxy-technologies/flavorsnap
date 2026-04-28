#!/bin/bash

# FlavorSnap Recovery Script
# Automated recovery procedures for data and model files
# Author: FlavorSnap Team
# Version: 1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_FILE="${BACKUP_DIR}/recovery_$(date +"%Y%m%d_%H%M%S").log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log_error "$1"
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
    
    log_success "All dependencies are available"
}

# List available backups
list_backups() {
    log "Listing available backups..."
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        return 1
    fi
    
    local backups=($(ls -t "$BACKUP_DIR"/flavorsnap_backup_*.tar.gz 2>/dev/null || true))
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        log_warning "No backup files found"
        return 1
    fi
    
    echo -e "\n${BLUE}Available backups:${NC}"
    for i in "${!backups[@]}"; do
        local backup_file="${backups[$i]}"
        local basename=$(basename "$backup_file" .tar.gz)
        local size=$(du -sh "$backup_file" | cut -f1)
        local date=$(stat -c %y "$backup_file" 2>/dev/null || stat -f %Sm "$backup_file" 2>/dev/null || echo "unknown")
        
        echo -e "  ${GREEN}$((i+1)).${NC} $basename (${size}) - $date"
    done
    
    echo ""
}

# Extract backup
extract_backup() {
    local backup_file="$1"
    local extract_dir="$2"
    
    log "Extracting backup: $(basename "$backup_file")"
    
    if [[ ! -f "$backup_file" ]]; then
        error_exit "Backup file not found: $backup_file"
    fi
    
    mkdir -p "$extract_dir"
    
    if ! tar -xzf "$backup_file" -C "$extract_dir"; then
        error_exit "Failed to extract backup file"
    fi
    
    log_success "Backup extracted to: $extract_dir"
}

# Verify backup integrity
verify_backup_integrity() {
    local backup_dir="$1"
    
    log "Verifying backup integrity..."
    
    # Check checksums
    if [[ -f "$backup_dir/checksums.sha256" ]]; then
        cd "$backup_dir"
        if sha256sum -c checksums.sha256 > /dev/null 2>&1; then
            log_success "Checksum verification passed"
        else
            error_exit "Checksum verification failed - backup may be corrupted"
        fi
    else
        log_warning "No checksum file found - skipping integrity check"
    fi
    
    # Check metadata
    if [[ -f "$backup_dir/backup_info.json" ]]; then
        log_success "Backup metadata found"
    else
        log_warning "No backup metadata found"
    fi
}

# Create backup of current state before recovery
create_pre_recovery_backup() {
    log "Creating pre-recovery backup..."
    
    local pre_recovery_backup="${BACKUP_DIR}/pre_recovery_$(date +"%Y%m%d_%H%M%S")"
    mkdir -p "$pre_recovery_backup"
    
    # Backup critical files that might be overwritten
    local critical_files=("model.pth" "food_classes.txt")
    for file in "${critical_files[@]}"; do
        if [[ -f "${PROJECT_ROOT}/$file" ]]; then
            cp "${PROJECT_ROOT}/$file" "$pre_recovery_backup/"
        fi
    done
    
    # Backup directories
    local critical_dirs=("dataset" "uploads" "ml-model-api")
    for dir in "${critical_dirs[@]}"; do
        if [[ -d "${PROJECT_ROOT}/$dir" ]]; then
            cp -r "${PROJECT_ROOT}/$dir" "$pre_recovery_backup/"
        fi
    done
    
    log_success "Pre-recovery backup created: $pre_recovery_backup"
}

# Recover model files
recover_models() {
    local backup_dir="$1"
    local force="${2:-false}"
    
    log "Recovering model files..."
    
    local recovered_files=()
    
    # Recover main model file
    if [[ -f "$backup_dir/models/model.pth" ]]; then
        if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/model.pth" ]]; then
            cp "$backup_dir/models/model.pth" "${PROJECT_ROOT}/"
            recovered_files+=("model.pth")
            log_success "Recovered model.pth"
        else
            log_warning "model.pth already exists (use --force to overwrite)"
        fi
    else
        log_warning "model.pth not found in backup"
    fi
    
    # Recover food classes file
    if [[ -f "$backup_dir/models/food_classes.txt" ]]; then
        if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/food_classes.txt" ]]; then
            cp "$backup_dir/models/food_classes.txt" "${PROJECT_ROOT}/"
            recovered_files+=("food_classes.txt")
            log_success "Recovered food_classes.txt"
        else
            log_warning "food_classes.txt already exists (use --force to overwrite)"
        fi
    else
        log_warning "food_classes.txt not found in backup"
    fi
    
    # Recover model-related Python files
    if [[ -d "$backup_dir/models" ]]; then
        find "$backup_dir/models" -name "*.py" -exec basename {} \; | while read -r py_file; do
            if [[ -f "$backup_dir/models/$py_file" ]]; then
                if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/ml-model-api/$py_file" ]]; then
                    mkdir -p "${PROJECT_ROOT}/ml-model-api/"
                    cp "$backup_dir/models/$py_file" "${PROJECT_ROOT}/ml-model-api/"
                    log_success "Recovered $py_file"
                fi
            fi
        done
    fi
    
    if [[ ${#recovered_files[@]} -gt 0 ]]; then
        log_success "Model recovery completed. Files recovered: ${recovered_files[*]}"
    else
        log_warning "No model files were recovered"
    fi
}

# Recover dataset
recover_dataset() {
    local backup_dir="$1"
    local force="${2:-false}"
    
    log "Recovering dataset..."
    
    if [[ ! -d "$backup_dir/dataset" ]]; then
        log_warning "Dataset not found in backup"
        return 0
    fi
    
    if [[ "$force" == "true" ]] || [[ ! -d "${PROJECT_ROOT}/dataset" ]]; then
        rsync -av "$backup_dir/dataset/" "${PROJECT_ROOT}/dataset/"
        log_success "Dataset recovered successfully"
    else
        log_warning "Dataset directory already exists (use --force to overwrite)"
    fi
}

# Recover uploads
recover_uploads() {
    local backup_dir="$1"
    local force="${2:-false}"
    
    log "Recovering user uploads..."
    
    if [[ ! -d "$backup_dir/uploads" ]]; then
        log_warning "Uploads not found in backup"
        return 0
    fi
    
    if [[ "$force" == "true" ]] || [[ ! -d "${PROJECT_ROOT}/uploads" ]]; then
        mkdir -p "${PROJECT_ROOT}/uploads"
        rsync -av "$backup_dir/uploads/" "${PROJECT_ROOT}/uploads/"
        log_success "User uploads recovered successfully"
    else
        log_warning "Uploads directory already exists (use --force to overwrite)"
    fi
}

# Recover configuration files
recover_config() {
    local backup_dir="$1"
    local force="${2:-false}"
    
    log "Recovering configuration files..."
    
    if [[ ! -d "$backup_dir/config" ]]; then
        log_warning "Configuration files not found in backup"
        return 0
    fi
    
    local recovered_configs=()
    
    # Recover package.json files
    find "$backup_dir/config" -name "package.json" -exec basename {} \; | while read -r config_file; do
        if [[ -f "$backup_dir/config/$config_file" ]]; then
            if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/$config_file" ]]; then
                cp "$backup_dir/config/$config_file" "${PROJECT_ROOT}/"
                recovered_configs+=("$config_file")
            fi
        fi
    done
    
    # Recover requirements.txt
    if [[ -f "$backup_dir/config/requirements.txt" ]]; then
        if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/ml-model-api/requirements.txt" ]]; then
            mkdir -p "${PROJECT_ROOT}/ml-model-api/"
            cp "$backup_dir/config/requirements.txt" "${PROJECT_ROOT}/ml-model-api/"
            recovered_configs+=("requirements.txt")
        fi
    fi
    
    # Recover other config files
    local config_files=("Cargo.toml" "tsconfig.json" "next.config.ts" "eslint.config.mjs")
    for config_file in "${config_files[@]}"; do
        if [[ -f "$backup_dir/config/$config_file" ]]; then
            if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/$config_file" ]]; then
                cp "$backup_dir/config/$config_file" "${PROJECT_ROOT}/"
                recovered_configs+=("$config_file")
            fi
            if [[ -f "$backup_dir/config/$config_file" ]] && [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/frontend/$config_file" ]]; then
                mkdir -p "${PROJECT_ROOT}/frontend/"
                cp "$backup_dir/config/$config_file" "${PROJECT_ROOT}/frontend/"
                recovered_configs+=("frontend/$config_file")
            fi
        fi
    done
    
    if [[ ${#recovered_configs[@]} -gt 0 ]]; then
        log_success "Configuration recovery completed. Files recovered: ${recovered_configs[*]}"
    else
        log_warning "No configuration files were recovered"
    fi
}

# Recover scripts
recover_scripts() {
    local backup_dir="$1"
    local force="${2:-false}"
    
    log "Recovering scripts..."
    
    if [[ ! -d "$backup_dir/scripts" ]]; then
        log_warning "Scripts not found in backup"
        return 0
    fi
    
    # Recover scripts directory
    if [[ "$force" == "true" ]] || [[ ! -d "$SCRIPT_DIR" ]] || [[ $(ls -A "$SCRIPT_DIR" 2>/dev/null | wc -l) -eq 0 ]]; then
        rsync -av "$backup_dir/scripts/" "$SCRIPT_DIR/"
        log_success "Scripts recovered successfully"
    else
        log_warning "Scripts directory already contains files (use --force to overwrite)"
    fi
    
    # Recover setup scripts
    find "$backup_dir/scripts" -name "setup.*" -exec basename {} \; | while read -r script_file; do
        if [[ -f "$backup_dir/scripts/$script_file" ]]; then
            if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/$script_file" ]]; then
                cp "$backup_dir/scripts/$script_file" "${PROJECT_ROOT}/"
                log_success "Recovered $script_file"
            fi
        fi
    done
    
    # Recover training notebook
    if [[ -f "$backup_dir/scripts/train_model.ipynb" ]]; then
        if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/train_model.ipynb" ]]; then
            cp "$backup_dir/scripts/train_model.ipynb" "${PROJECT_ROOT}/"
            log_success "Recovered train_model.ipynb"
        fi
    fi
}

# Recover database files
recover_database() {
    local backup_dir="$1"
    local force="${2:-false}"
    
    log "Recovering database files..."
    
    if [[ ! -d "$backup_dir/database" ]]; then
        log_warning "Database files not found in backup"
        return 0
    fi
    
    local recovered_db_files=()
    
    # Recover database files
    find "$backup_dir/database" -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" -o -name "*.sql" \) -exec basename {} \; | while read -r db_file; do
        if [[ -f "$backup_dir/database/$db_file" ]]; then
            if [[ "$force" == "true" ]] || [[ ! -f "${PROJECT_ROOT}/$db_file" ]]; then
                cp "$backup_dir/database/$db_file" "${PROJECT_ROOT}/"
                recovered_db_files+=("$db_file")
            fi
        fi
    done
    
    # Recover data directory
    if [[ -d "$backup_dir/database/data" ]]; then
        if [[ "$force" == "true" ]] || [[ ! -d "${PROJECT_ROOT}/data" ]]; then
            mkdir -p "${PROJECT_ROOT}/data"
            rsync -av "$backup_dir/database/data/" "${PROJECT_ROOT}/data/"
            recovered_db_files+=("data/")
        fi
    fi
    
    if [[ ${#recovered_db_files[@]} -gt 0 ]]; then
        log_success "Database recovery completed. Files recovered: ${recovered_db_files[*]}"
    else
        log_warning "No database files were recovered"
    fi
}

# Set proper permissions
set_permissions() {
    log "Setting proper permissions..."
    
    # Set executable permissions for scripts
    find "$SCRIPT_DIR" -name "*.sh" -exec chmod +x {} \;
    
    # Set readable permissions for model files
    if [[ -f "${PROJECT_ROOT}/model.pth" ]]; then
        chmod 644 "${PROJECT_ROOT}/model.pth"
    fi
    
    if [[ -f "${PROJECT_ROOT}/food_classes.txt" ]]; then
        chmod 644 "${PROJECT_ROOT}/food_classes.txt"
    fi
    
    # Set proper permissions for data directories
    if [[ -d "${PROJECT_ROOT}/dataset" ]]; then
        chmod -R 755 "${PROJECT_ROOT}/dataset"
    fi
    
    if [[ -d "${PROJECT_ROOT}/uploads" ]]; then
        chmod -R 755 "${PROJECT_ROOT}/uploads"
    fi
    
    log_success "Permissions set successfully"
}

# Validate recovery
validate_recovery() {
    local backup_dir="$1"
    
    log "Validating recovery..."
    
    local validation_errors=0
    
    # Check critical files
    local critical_files=("model.pth" "food_classes.txt")
    for file in "${critical_files[@]}"; do
        if [[ -f "$backup_dir/models/$file" ]] && [[ ! -f "${PROJECT_ROOT}/$file" ]]; then
            log_error "Critical file not recovered: $file"
            ((validation_errors++))
        fi
    done
    
    # Check directories
    local critical_dirs=("dataset" "uploads")
    for dir in "${critical_dirs[@]}"; do
        if [[ -d "$backup_dir/$dir" ]] && [[ ! -d "${PROJECT_ROOT}/$dir" ]]; then
            log_warning "Directory not recovered: $dir"
        fi
    done
    
    if [[ $validation_errors -eq 0 ]]; then
        log_success "Recovery validation passed"
        return 0
    else
        log_error "Recovery validation failed with $validation_errors errors"
        return 1
    fi
}

# Generate recovery report
generate_recovery_report() {
    local backup_dir="$1"
    local backup_file="$2"
    local recovery_start="$3"
    
    local recovery_end=$(date +"%Y-%m-%d %H:%M:%S")
    local report_file="${BACKUP_DIR}/recovery_report_$(date +"%Y%m%d_%H%M%S").json"
    
    cat > "$report_file" << EOF
{
    "recovery_info": {
        "backup_file": "$(basename "$backup_file")",
        "backup_timestamp": "$(jq -r '.timestamp' "$backup_dir/backup_info.json" 2>/dev/null || echo 'unknown')",
        "recovery_start": "$recovery_start",
        "recovery_end": "$recovery_end",
        "recovered_by": "$(whoami)",
        "hostname": "$(hostname)"
    },
    "recovered_items": {
        "models": $(find "$backup_dir/models" -type f | wc -l),
        "dataset_files": $(find "$backup_dir/dataset" -type f 2>/dev/null | wc -l),
        "upload_files": $(find "$backup_dir/uploads" -type f 2>/dev/null | wc -l),
        "config_files": $(find "$backup_dir/config" -type f 2>/dev/null | wc -l),
        "scripts": $(find "$backup_dir/scripts" -type f 2>/dev/null | wc -l),
        "database_files": $(find "$backup_dir/database" -type f 2>/dev/null | wc -l)
    },
    "validation": {
        "status": "completed",
        "timestamp": "$recovery_end"
    }
}
EOF
    
    log_success "Recovery report generated: $report_file"
}

# Interactive recovery mode
interactive_recovery() {
    echo -e "\n${BLUE}=== FlavorSnap Interactive Recovery ===${NC}\n"
    
    list_backups
    
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    echo -n "Select backup number (or 'q' to quit): "
    read -r selection
    
    if [[ "$selection" == "q" ]]; then
        log "Recovery cancelled by user"
        return 0
    fi
    
    if ! [[ "$selection" =~ ^[0-9]+$ ]]; then
        error_exit "Invalid selection"
    fi
    
    local backups=($(ls -t "$BACKUP_DIR"/flavorsnap_backup_*.tar.gz 2>/dev/null))
    local selected_index=$((selection - 1))
    
    if [[ $selected_index -lt 0 ]] || [[ $selected_index -ge ${#backups[@]} ]]; then
        error_exit "Invalid backup selection"
    fi
    
    local selected_backup="${backups[$selected_index]}"
    
    echo -e "\n${YELLOW}Selected backup: $(basename "$selected_backup")${NC}"
    echo -n "Continue with recovery? (y/N): "
    read -r confirm
    
    if [[ "$confirm" != "y" ]] && [[ "$confirm" != "Y" ]]; then
        log "Recovery cancelled by user"
        return 0
    fi
    
    echo -n "Overwrite existing files? (y/N): "
    read -r overwrite
    
    local force="false"
    if [[ "$overwrite" == "y" ]] || [[ "$overwrite" == "Y" ]]; then
        force="true"
    fi
    
    perform_recovery "$selected_backup" "$force"
}

# Perform recovery
perform_recovery() {
    local backup_file="$1"
    local force="${2:-false}"
    local recovery_start=$(date +"%Y-%m-%d %H:%M:%S")
    
    log "Starting recovery from: $(basename "$backup_file")"
    
    # Create temporary extraction directory
    local temp_dir="${BACKUP_DIR}/temp_recovery_$(date +"%Y%m%d_%H%M%S")"
    
    # Extract and verify backup
    extract_backup "$backup_file" "$temp_dir"
    verify_backup_integrity "$temp_dir"
    
    # Create pre-recovery backup
    if [[ "$force" == "true" ]]; then
        create_pre_recovery_backup
    fi
    
    # Perform recovery
    recover_models "$temp_dir" "$force"
    recover_dataset "$temp_dir" "$force"
    recover_uploads "$temp_dir" "$force"
    recover_config "$temp_dir" "$force"
    recover_scripts "$temp_dir" "$force"
    recover_database "$temp_dir" "$force"
    
    # Set permissions and validate
    set_permissions
    
    if validate_recovery "$temp_dir"; then
        log_success "Recovery completed successfully"
        generate_recovery_report "$temp_dir" "$backup_file" "$recovery_start"
    else
        log_error "Recovery validation failed"
        return 1
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_success "Recovery process completed"
}

# Show help
show_help() {
    cat << EOF
FlavorSnap Recovery Script v1.0.0

Usage: $0 [OPTIONS] [BACKUP_FILE]

OPTIONS:
    --interactive, -i    Interactive recovery mode
    --force, -f          Force overwrite existing files
    --list, -l           List available backups
    --help, -h           Show this help message

EXAMPLES:
    $0 --interactive                    # Interactive recovery
    $0 --list                          # List available backups
    $0 /path/to/backup.tar.gz          # Recover from specific backup
    $0 --force /path/to/backup.tar.gz  # Force overwrite existing files

EOF
}

# Main function
main() {
    local interactive=false
    local force=false
    local list_only=false
    local backup_file=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interactive|-i)
                interactive=true
                shift
                ;;
            --force|-f)
                force=true
                shift
                ;;
            --list|-l)
                list_only=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            -*)
                error_exit "Unknown option: $1"
                ;;
            *)
                backup_file="$1"
                shift
                ;;
        esac
    done
    
    # Check dependencies
    check_dependencies
    
    # Handle different modes
    if [[ "$list_only" == "true" ]]; then
        list_backups
        exit $?
    fi
    
    if [[ "$interactive" == "true" ]]; then
        interactive_recovery
        exit $?
    fi
    
    if [[ -z "$backup_file" ]]; then
        log_error "No backup file specified"
        show_help
        exit 1
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        error_exit "Backup file not found: $backup_file"
    fi
    
    perform_recovery "$backup_file" "$force"
}

# Run main function with all arguments
main "$@"
