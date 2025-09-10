#!/bin/bash

# PostToolUse Hook for Automatic Testing
# Triggered after Write or Edit tools are used
# Automatically runs relevant tests based on modified files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_TIMEOUT=30
MAX_PARALLEL_TESTS=2

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if auto-testing is enabled
check_auto_test_enabled() {
    local settings_file="${PROJECT_ROOT}/.claude/settings.local.json"
    if [[ -f "$settings_file" ]]; then
        local enabled=$(jq -r '.auto_test.enabled // true' "$settings_file" 2>/dev/null)
        if [[ "$enabled" == "false" ]]; then
            log "Auto-testing disabled in settings"
            exit 0
        fi
    fi
}

# Parse tool usage from environment or arguments
parse_tool_usage() {
    local tool_name="$1"
    local file_path="$2"
    
    # Only process Write and Edit tools
    if [[ "$tool_name" != "Write" && "$tool_name" != "Edit" && "$tool_name" != "MultiEdit" ]]; then
        exit 0
    fi
    
    # Skip if no file path provided
    if [[ -z "$file_path" ]]; then
        exit 0
    fi
    
    # Skip if file doesn't exist or is not a code file
    if [[ ! -f "$file_path" ]]; then
        exit 0
    fi
    
    # Only process relevant file types
    case "$file_path" in
        *.py|*.vue|*.ts|*.js) ;;
        *) exit 0 ;;
    esac
    
    echo "$file_path"
}

# Map file to corresponding tests
map_file_to_tests() {
    local file_path="$1"
    local tests=()
    
    # Backend Python files
    if [[ "$file_path" =~ backend/app/ ]]; then
        case "$file_path" in
            # Model files - run both unit and integration tests
            */models/cluster.py)
                tests+=("backend/tests/unit/models/test_cluster.py")
                tests+=("backend/tests/integration/api/test_clusters_api.py")
                ;;
            */models/table_metric.py)
                tests+=("backend/tests/unit/models/test_table_metric.py")
                tests+=("backend/tests/integration/api/test_tables_api.py")
                ;;
            */models/merge_task.py)
                tests+=("backend/tests/unit/models/test_merge_task.py")
                tests+=("backend/tests/integration/api/test_tasks_api.py")
                ;;
            */models/*.py)
                # Generic model test mapping
                local model_name=$(basename "$file_path" .py)
                tests+=("backend/tests/unit/models/test_${model_name}.py")
                ;;
                
            # API endpoint files - run integration tests
            */api/clusters.py)
                tests+=("backend/tests/integration/api/test_clusters_api.py")
                ;;
            */api/tables.py)
                tests+=("backend/tests/integration/api/test_tables_api.py")
                ;;
            */api/tasks.py)
                tests+=("backend/tests/integration/api/test_tasks_api.py")
                ;;
            */api/*.py)
                # Generic API test mapping
                local api_name=$(basename "$file_path" .py)
                tests+=("backend/tests/integration/api/test_${api_name}_api.py")
                ;;
                
            # Monitor module files - run specific unit tests
            */monitor/mysql_hive_connector.py)
                tests+=("backend/tests/unit/monitor/test_mysql_hive_connector.py")
                ;;
            */monitor/mock_hdfs_scanner.py)
                tests+=("backend/tests/unit/monitor/test_mock_hdfs_scanner.py")
                ;;
            */monitor/webhdfs_scanner.py)
                tests+=("backend/tests/unit/monitor/test_webhdfs_scanner.py")
                ;;
            */monitor/hybrid_table_scanner.py)
                tests+=("backend/tests/unit/monitor/test_hybrid_table_scanner.py")
                tests+=("backend/tests/integration/api/test_tables_api.py")
                ;;
            */monitor/*.py)
                # Generic monitor test mapping
                local filename=$(basename "$file_path" .py)
                tests+=("backend/tests/unit/monitor/test_${filename}.py")
                ;;
                
            # Configuration files - run health check and general tests
            */config/*.py)
                tests+=("backend/tests/integration/api/test_health_check.py")
                tests+=("backend/tests/unit/")
                ;;
                
            # Scheduler files - run integration tests
            */scheduler/*.py)
                tests+=("backend/tests/integration/api/test_tasks_api.py")
                tests+=("backend/tests/integration/api/test_workflow_scenarios.py")
                ;;
                
            # Main application file - run health check
            */main.py)
                tests+=("backend/tests/integration/api/test_health_check.py")
                ;;
                
            # Engine files - run workflow tests
            */engines/*.py)
                tests+=("backend/tests/integration/api/test_workflow_scenarios.py")
                ;;
        esac
        
        # Add general backend tests if no specific tests found
        if [[ ${#tests[@]} -eq 0 ]]; then
            tests+=("backend/tests/unit/")
        fi
    fi
    
    # Frontend files mapping
    if [[ "$file_path" =~ frontend/src/ ]]; then
        case "$file_path" in
            */views/Clusters.vue)
                tests+=("frontend:type-check")
                # Could add e2e tests here in the future
                ;;
            */views/Tables.vue)
                tests+=("frontend:type-check")
                ;;
            */api/*.ts)
                tests+=("frontend:type-check")
                # API client changes should trigger type checking
                ;;
            */router/*.ts)
                tests+=("frontend:type-check")
                ;;
            *)
                # Default frontend testing
                tests+=("frontend:type-check")
                ;;
        esac
    fi
    
    printf '%s\n' "${tests[@]}"
}

# Run a single test file or command
run_test() {
    local test_path="$1"
    local start_time=$(date +%s)
    
    if [[ "$test_path" == "frontend:type-check" ]]; then
        log "🔍 Running frontend type check..."
        cd "${PROJECT_ROOT}/frontend"
        if npm run type-check > /tmp/typecheck.log 2>&1; then
            success "✅ TypeScript check passed"
            return 0
        else
            error "❌ TypeScript check failed:"
            cat /tmp/typecheck.log | tail -10
            return 1
        fi
    else
        # Python test
        if [[ ! -f "${PROJECT_ROOT}/${test_path}" && ! -d "${PROJECT_ROOT}/${test_path}" ]]; then
            warning "⚠️  Test file not found: ${test_path}"
            return 0
        fi
        
        log "🧪 Running: python -m pytest ${test_path} -v"
        cd "${PROJECT_ROOT}/backend"
        
        if python -m pytest "${test_path}" -v --tb=short -q --maxfail=3 > /tmp/pytest.log 2>&1; then
            local duration=$(($(date +%s) - start_time))
            local test_count=$(grep -c "PASSED\|FAILED" /tmp/pytest.log 2>/dev/null || echo "0")
            success "✅ PASSED: ${test_count} tests in ${duration}s"
            return 0
        else
            local exit_code=$?
            error "❌ FAILED: ${test_path}"
            # Show only the most relevant error information
            if [[ -f /tmp/pytest.log ]]; then
                echo ""
                grep -A 5 -B 5 "FAILED\|ERROR\|AssertionError" /tmp/pytest.log | tail -15
                echo ""
            fi
            return $exit_code
        fi
    fi
}

# Main execution
main() {
    local tool_name="${1:-${CLAUDE_TOOL_NAME}}"
    local file_path="${2:-${CLAUDE_FILE_PATH}}"
    
    # Parse command line arguments if provided
    if [[ $# -ge 2 ]]; then
        tool_name="$1"
        file_path="$2"
    fi
    
    # Check if auto-testing is enabled
    check_auto_test_enabled
    
    # Parse and validate tool usage
    file_path=$(parse_tool_usage "$tool_name" "$file_path")
    if [[ -z "$file_path" ]]; then
        exit 0
    fi
    
    # Make file path relative to project root
    file_path=$(realpath --relative-to="$PROJECT_ROOT" "$file_path" 2>/dev/null || echo "$file_path")
    
    log "🚀 Auto-testing triggered by: ${file_path}"
    
    # Map file to tests - compatible with all shells
    tests=()
    while IFS= read -r line; do
        tests+=("$line")
    done < <(map_file_to_tests "$file_path")
    
    if [[ ${#tests[@]} -eq 0 ]]; then
        warning "⚠️  No tests found for: ${file_path}"
        exit 0
    fi
    
    # Run tests
    local failed_tests=0
    local total_tests=${#tests[@]}
    
    for test in "${tests[@]}"; do
        if ! run_test "$test"; then
            ((failed_tests++))
        fi
    done
    
    # Summary
    echo ""
    if [[ $failed_tests -eq 0 ]]; then
        success "🎉 All ${total_tests} test(s) passed! Ready for next modification."
    else
        error "💥 ${failed_tests}/${total_tests} test(s) failed. Please review and fix."
        
        # Don't exit with error - just inform the user
        warning "ℹ️  Tests failed, but continuing to allow further AI modifications..."
    fi
    
    echo ""
}

# Run main function with all arguments
main "$@"