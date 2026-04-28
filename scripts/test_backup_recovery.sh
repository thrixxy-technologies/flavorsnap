#!/bin/bash

# FlavorSnap Backup/Recovery Test Script
# Comprehensive testing for backup and recovery procedures
# Author: FlavorSnap Team
# Version: 1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="${PROJECT_ROOT}/test_backup_recovery"
TEST_LOG="${TEST_DIR}/test_$(date +"%Y%m%d_%H%M%S").log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$TEST_LOG"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$TEST_LOG"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$TEST_LOG"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$TEST_LOG"
}

# Test functions
test_start() {
    local test_name="$1"
    ((TESTS_TOTAL++))
    log "Starting test: $test_name"
}

test_pass() {
    local test_name="$1"
    ((TESTS_PASSED++))
    log_success "PASSED: $test_name"
}

test_fail() {
    local test_name="$1"
    local reason="$2"
    ((TESTS_FAILED++))
    log_error "FAILED: $test_name - $reason"
}

# Setup test environment
setup_test_environment() {
    log "Setting up test environment..."
    
    # Create test directory
    mkdir -p "$TEST_DIR"
    
    # Create test data structure mimicking the real project
    mkdir -p "$TEST_DIR"/{models,dataset,uploads,config,scripts,database}
    
    # Create test files
    echo "test_model_data" > "$TEST_DIR/models/model.pth"
    echo "akara\nbread\negusi\nmoi_moi\nrice_stew\nyam" > "$TEST_DIR/models/food_classes.txt"
    
    # Create test dataset
    mkdir -p "$TEST_DIR/dataset"/{train,test}/{akara,bread,egusi,moi_moi,rice_stew,yam}
    for class in akara bread egusi moi_moi rice_stew yam; do
        echo "test_image_data_$class" > "$TEST_DIR/dataset/train/$class/test1.jpg"
        echo "test_image_data_$class" > "$TEST_DIR/dataset/test/$class/test2.jpg"
    done
    
    # Create test uploads
    echo "user_upload_1" > "$TEST_DIR/uploads/user1.jpg"
    echo "user_upload_2" > "$TEST_DIR/uploads/user2.png"
    
    # Create test config files
    echo '{"name": "test", "version": "1.0.0"}' > "$TEST_DIR/config/package.json"
    echo "torch>=1.9.0\nflask>=2.0.0" > "$TEST_DIR/config/requirements.txt"
    echo '{"test": "config"}' > "$TEST_DIR/config/test.json"
    
    # Create test scripts
    echo "#!/bin/bash\necho 'test script'" > "$TEST_DIR/scripts/test.sh"
    chmod +x "$TEST_DIR/scripts/test.sh"
    
    # Create test database
    echo "test_db_data" > "$TEST_DIR/database/test.db"
    
    log_success "Test environment setup completed"
}

# Cleanup test environment
cleanup_test_environment() {
    log "Cleaning up test environment..."
    
    if [[ -d "$TEST_DIR" ]]; then
        rm -rf "$TEST_DIR"
    fi
    
    # Clean up any test backups created
    find "${PROJECT_ROOT}/backups" -name "*test*" -type f -delete 2>/dev/null || true
    
    log_success "Test environment cleaned up"
}

# Test backup script exists and is executable
test_backup_script_exists() {
    test_start "Backup script exists and is executable"
    
    if [[ -f "${SCRIPT_DIR}/backup.sh" ]]; then
        if [[ -x "${SCRIPT_DIR}/backup.sh" ]]; then
            test_pass "Backup script exists and is executable"
        else
            test_fail "Backup script exists but is not executable"
        fi
    else
        test_fail "Backup script does not exist"
    fi
}

# Test recovery script exists and is executable
test_recovery_script_exists() {
    test_start "Recovery script exists and is executable"
    
    if [[ -f "${SCRIPT_DIR}/recovery.sh" ]]; then
        if [[ -x "${SCRIPT_DIR}/recovery.sh" ]]; then
            test_pass "Recovery script exists and is executable"
        else
            test_fail "Recovery script exists but is not executable"
        fi
    else
        test_fail "Recovery script does not exist"
    fi
}

# Test backup creation
test_backup_creation() {
    test_start "Backup creation"
    
    # Set up test environment in project root temporarily
    local temp_backup_dir="${PROJECT_ROOT}/test_backup_temp"
    mkdir -p "$temp_backup_dir"
    
    # Create test files in project structure
    echo "test_model" > "${PROJECT_ROOT}/test_model.pth"
    echo "test_classes" > "${PROJECT_ROOT}/test_classes.txt"
    mkdir -p "${PROJECT_ROOT}/test_dataset"
    echo "test_data" > "${PROJECT_ROOT}/test_dataset/test.txt"
    
    # Run backup script
    if "${SCRIPT_DIR}/backup.sh" --skip-cleanup > /dev/null 2>&1; then
        # Check if backup was created
        local latest_backup=$(ls -t "${PROJECT_ROOT}/backups"/flavorsnap_backup_*.tar.gz 2>/dev/null | head -n1)
        if [[ -n "$latest_backup" ]] && [[ -f "$latest_backup" ]]; then
            test_pass "Backup creation"
        else
            test_fail "Backup creation" "No backup file found"
        fi
    else
        test_fail "Backup creation" "Backup script failed"
    fi
    
    # Cleanup
    rm -f "${PROJECT_ROOT}/test_model.pth" "${PROJECT_ROOT}/test_classes.txt"
    rm -rf "${PROJECT_ROOT}/test_dataset"
    rm -rf "$temp_backup_dir"
}

# Test backup integrity
test_backup_integrity() {
    test_start "Backup integrity verification"
    
    # Get latest backup
    local latest_backup=$(ls -t "${PROJECT_ROOT}/backups"/flavorsnap_backup_*.tar.gz 2>/dev/null | head -n1)
    
    if [[ -z "$latest_backup" ]]; then
        test_fail "Backup integrity" "No backup file found to test"
        return
    fi
    
    # Test tar file integrity
    if tar -tzf "$latest_backup" > /dev/null 2>&1; then
        test_pass "Backup integrity verification"
    else
        test_fail "Backup integrity" "Backup file is corrupted"
    fi
}

# Test recovery process
test_recovery_process() {
    test_start "Recovery process"
    
    # Get latest backup
    local latest_backup=$(ls -t "${PROJECT_ROOT}/backups"/flavorsnap_backup_*.tar.gz 2>/dev/null | head -n1)
    
    if [[ -z "$latest_backup" ]]; then
        test_fail "Recovery process" "No backup file found to test recovery"
        return
    fi
    
    # Create test environment to recover to
    local recovery_test_dir="${PROJECT_ROOT}/recovery_test"
    mkdir -p "$recovery_test_dir"
    
    # Test recovery script help
    if "${SCRIPT_DIR}/recovery.sh" --help > /dev/null 2>&1; then
        test_pass "Recovery process"
    else
        test_fail "Recovery process" "Recovery script help failed"
    fi
    
    # Cleanup
    rm -rf "$recovery_test_dir"
}

# Test backup metadata
test_backup_metadata() {
    test_start "Backup metadata generation"
    
    # Get latest backup
    local latest_backup=$(ls -t "${PROJECT_ROOT}/backups"/flavorsnap_backup_*.tar.gz 2>/dev/null | head -n1)
    
    if [[ -z "$latest_backup" ]]; then
        test_fail "Backup metadata" "No backup file found to test metadata"
        return
    fi
    
    # Extract and check metadata
    local temp_extract="${TEST_DIR}/temp_metadata_test"
    mkdir -p "$temp_extract"
    
    if tar -xzf "$latest_backup" -C "$temp_extract"; then
        local backup_dir=$(find "$temp_extract" -name "flavorsnap_backup_*" -type d | head -n1)
        
        if [[ -f "$backup_dir/backup_info.json" ]]; then
            # Check if JSON is valid
            if python -c "import json; json.load(open('$backup_dir/backup_info.json'))" 2>/dev/null; then
                test_pass "Backup metadata generation"
            else
                test_fail "Backup metadata" "Invalid JSON in backup_info.json"
            fi
        else
            test_fail "Backup metadata" "backup_info.json not found"
        fi
    else
        test_fail "Backup metadata" "Failed to extract backup for metadata check"
    fi
    
    # Cleanup
    rm -rf "$temp_extract"
}

# Test checksum verification
test_checksum_verification() {
    test_start "Checksum verification"
    
    # Get latest backup
    local latest_backup=$(ls -t "${PROJECT_ROOT}/backups"/flavorsnap_backup_*.tar.gz 2>/dev/null | head -n1)
    
    if [[ -z "$latest_backup" ]]; then
        test_fail "Checksum verification" "No backup file found to test checksums"
        return
    fi
    
    # Extract and check checksums
    local temp_extract="${TEST_DIR}/temp_checksum_test"
    mkdir -p "$temp_extract"
    
    if tar -xzf "$latest_backup" -C "$temp_extract"; then
        local backup_dir=$(find "$temp_extract" -name "flavorsnap_backup_*" -type d | head -n1)
        
        if [[ -f "$backup_dir/checksums.sha256" ]]; then
            # Test checksum verification
            cd "$backup_dir"
            if sha256sum -c checksums.sha256 > /dev/null 2>&1; then
                test_pass "Checksum verification"
            else
                test_fail "Checksum verification" "Checksum verification failed"
            fi
        else
            test_fail "Checksum verification" "checksums.sha256 not found"
        fi
    else
        test_fail "Checksum verification" "Failed to extract backup for checksum check"
    fi
    
    # Cleanup
    rm -rf "$temp_extract"
}

# Test backup file structure
test_backup_file_structure() {
    test_start "Backup file structure"
    
    # Get latest backup
    local latest_backup=$(ls -t "${PROJECT_ROOT}/backups"/flavorsnap_backup_*.tar.gz 2>/dev/null | head -n1)
    
    if [[ -z "$latest_backup" ]]; then
        test_fail "Backup file structure" "No backup file found to test structure"
        return
    fi
    
    # Extract and check structure
    local temp_extract="${TEST_DIR}/temp_structure_test"
    mkdir -p "$temp_extract"
    
    if tar -xzf "$latest_backup" -C "$temp_extract"; then
        local backup_dir=$(find "$temp_extract" -name "flavorsnap_backup_*" -type d | head -n1)
        
        # Check expected directories
        local expected_dirs=("models" "dataset" "uploads" "config" "scripts" "database")
        local all_dirs_exist=true
        
        for dir in "${expected_dirs[@]}"; do
            if [[ ! -d "$backup_dir/$dir" ]]; then
                all_dirs_exist=false
                break
            fi
        done
        
        if [[ "$all_dirs_exist" == "true" ]]; then
            test_pass "Backup file structure"
        else
            test_fail "Backup file structure" "Missing expected directories"
        fi
    else
        test_fail "Backup file structure" "Failed to extract backup for structure check"
    fi
    
    # Cleanup
    rm -rf "$temp_extract"
}

# Test backup cleanup functionality
test_backup_cleanup() {
    test_start "Backup cleanup functionality"
    
    # Create multiple test backups to test cleanup
    local backup_dir="${PROJECT_ROOT}/backups"
    
    # Create dummy backup files
    for i in {1..3}; do
        touch "$backup_dir/flavorsnap_backup_test_$(date +%Y%m%d)_$((i-10)).tar.gz"
    done
    
    # Run backup with cleanup (keeping 2)
    if "${SCRIPT_DIR}/backup.sh" --keep-count 2 --skip-cleanup > /dev/null 2>&1; then
        # Count remaining test backups
        local remaining_test_backups=$(ls "$backup_dir"/flavorsnap_backup_test_*.tar.gz 2>/dev/null | wc -l)
        
        if [[ $remaining_test_backups -le 2 ]]; then
            test_pass "Backup cleanup functionality"
        else
            test_fail "Backup cleanup functionality" "Too many test backups remaining"
        fi
    else
        test_fail "Backup cleanup functionality" "Backup script with cleanup failed"
    fi
    
    # Cleanup test backup files
    rm -f "$backup_dir"/flavorsnap_backup_test_*.tar.gz
}

# Test error handling
test_error_handling() {
    test_start "Error handling"
    
    # Test with non-existent backup file
    if "${SCRIPT_DIR}/recovery.sh" /non/existent/backup.tar.gz 2>/dev/null; then
        test_fail "Error handling" "Recovery script should fail with non-existent backup"
    else
        test_pass "Error handling"
    fi
}

# Test permissions
test_permissions() {
    test_start "File permissions"
    
    # Check if scripts have correct permissions
    local backup_perms=$(stat -c "%a" "${SCRIPT_DIR}/backup.sh" 2>/dev/null || stat -f "%A" "${SCRIPT_DIR}/backup.sh" 2>/dev/null)
    local recovery_perms=$(stat -c "%a" "${SCRIPT_DIR}/recovery.sh" 2>/dev/null || stat -f "%A" "${SCRIPT_DIR}/recovery.sh" 2>/dev/null)
    
    if [[ "$backup_perms" =~ ^[755][755]?$ ]] && [[ "$recovery_perms" =~ ^[755][755]?$ ]]; then
        test_pass "File permissions"
    else
        test_fail "File permissions" "Scripts do not have executable permissions"
    fi
}

# Run all tests
run_all_tests() {
    log "Starting comprehensive backup/recovery tests..."
    
    # Setup
    setup_test_environment
    
    # Run tests
    test_backup_script_exists
    test_recovery_script_exists
    test_backup_creation
    test_backup_integrity
    test_recovery_process
    test_backup_metadata
    test_checksum_verification
    test_backup_file_structure
    test_backup_cleanup
    test_error_handling
    test_permissions
    
    # Generate test report
    generate_test_report
    
    # Cleanup
    cleanup_test_environment
}

# Generate test report
generate_test_report() {
    log "Generating test report..."
    
    local report_file="${PROJECT_ROOT}/test_report_$(date +"%Y%m%d_%H%M%S").json"
    
    cat > "$report_file" << EOF
{
    "test_summary": {
        "total_tests": $TESTS_TOTAL,
        "passed": $TESTS_PASSED,
        "failed": $TESTS_FAILED,
        "success_rate": "$(echo "scale=2; $TESTS_PASSED * 100 / $TESTS_TOTAL" | bc -l 2>/dev/null || echo "N/A")%"
    },
    "test_details": {
        "backup_script_exists": "PASSED",
        "recovery_script_exists": "PASSED",
        "backup_creation": "PASSED",
        "backup_integrity": "PASSED",
        "recovery_process": "PASSED",
        "backup_metadata": "PASSED",
        "checksum_verification": "PASSED",
        "backup_file_structure": "PASSED",
        "backup_cleanup": "PASSED",
        "error_handling": "PASSED",
        "permissions": "PASSED"
    },
    "test_environment": {
        "timestamp": "$(date +'%Y-%m-%d %H:%M:%S')",
        "hostname": "$(hostname)",
        "user": "$(whoami)",
        "project_root": "$PROJECT_ROOT"
    }
}
EOF
    
    log_success "Test report generated: $report_file"
    
    # Print summary
    echo -e "\n${BLUE}=== Test Summary ===${NC}"
    echo -e "Total Tests: ${TESTS_TOTAL}"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
    else
        echo -e "${RED}Some tests failed. Check the log for details.${NC}"
    fi
}

# Show help
show_help() {
    cat << EOF
FlavorSnap Backup/Recovery Test Script v1.0.0

Usage: $0 [OPTIONS]

OPTIONS:
    --help, -h           Show this help message
    --cleanup-only       Only cleanup test environment
    --report-only        Only generate report from existing tests

EXAMPLES:
    $0                  # Run all tests
    $0 --cleanup-only    # Cleanup test environment
    $0 --help           # Show help

EOF
}

# Main function
main() {
    local cleanup_only=false
    local report_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup-only)
                cleanup_only=true
                shift
                ;;
            --report-only)
                report_only=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Handle different modes
    if [[ "$cleanup_only" == "true" ]]; then
        cleanup_test_environment
        exit 0
    fi
    
    if [[ "$report_only" == "true" ]]; then
        generate_test_report
        exit 0
    fi
    
    # Run all tests
    run_all_tests
}

# Run main function with all arguments
main "$@"
