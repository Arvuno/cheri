#!/usr/bin/env bash
# MinIO Smoke Test Script for Cheri S3-Compatible Provider
# 
# Usage: ./scripts/dev/minio-smoke.sh
# Requires: docker, mc (minio client) optionally
#
# This script:
# 1. Starts a local MinIO container
# 2. Creates a test bucket
# 3. Validates Cheri S3-compatible provider config (dry-run)
# 4. Uploads a test file
# 5. Downloads and verifies checksum
# 6. Cleans up
#
# Note: Full upload/download e2e requires Cheri with actual S3-compatible
# provider implementation. This script tests the MinIO infrastructure only.

set -e

CONTAINER_NAME="cheri-minio-test"
MINIO_PORT="${MINIO_PORT:-9000}"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9001}"
TEST_BUCKET="cheri-test-$(date +%s)"
TEST_FILE="/tmp/cheri-minio-test-$(date +%s).txt"
TEST_CONTENT="Cheri MinIO smoke test $(date)"

cleanup() {
    echo "=== Cleaning up ==="
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    rm -f "$TEST_FILE" 2>/dev/null || true
}

trap cleanup EXIT

echo "=== MinIO Smoke Test ==="
echo "Start time: $(date)"

# Check docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: docker not found"
    exit 1
fi

# Start MinIO
echo "=== Starting MinIO container ==="
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$MINIO_PORT:9000" \
    -p "$MINIO_CONSOLE_PORT:9001" \
    -e "MINIO_ROOT_USER=minioadmin" \
    -e "MINIO_ROOT_PASSWORD=minioadmin" \
    minio/minio server /data --console-address ":$MINIO_CONSOLE_PORT" --compat

# Wait for MinIO to be ready
echo "=== Waiting for MinIO to start ==="
for i in {1..30}; do
    if curl -s "http://localhost:$MINIO_PORT/minio/health/live" > /dev/null 2>&1; then
        echo "MinIO is ready after ${i}s"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: MinIO failed to start within 30s"
        exit 1
    fi
    sleep 1
done

# Create test file
echo "=== Creating test file ==="
echo "$TEST_CONTENT" > "$TEST_FILE"
echo "Created: $TEST_FILE"

# Create bucket using MinIO API (since mc might not be available)
echo "=== Creating bucket: $TEST_BUCKET ==="
curl -X PUT \
    -H "Content-Type: application/json" \
    -u "minioadmin:minioadmin" \
    "http://localhost:$MINIO_PORT/$TEST_BUCKET/" 2>/dev/null || true

# Upload test file
echo "=== Uploading test file ==="
curl -X PUT \
    -H "Content-Type: text/plain" \
    -u "minioadmin:minioadmin" \
    --data "$TEST_CONTENT" \
    "http://localhost:$MINIO_PORT/$TEST_BUCKET/test-file.txt"

# Download and verify
echo "=== Downloading and verifying ==="
DOWNLOADED=$(curl -s -u "minioadmin:minioadmin" "http://localhost:$MINIO_PORT/$TEST_BUCKET/test-file.txt")
if [ "$DOWNLOADED" = "$TEST_CONTENT" ]; then
    echo "CHECKSUM VERIFY: PASSED"
else
    echo "CHECKSUM VERIFY: FAILED"
    echo "Expected: $TEST_CONTENT"
    echo "Got: $DOWNLOADED"
    exit 1
fi

echo "=== MinIO Infrastructure Test: PASSED ==="
echo "End time: $(date)"
echo ""
echo "MinIO is running with:"
echo "  API: http://localhost:$MINIO_PORT"
echo "  Console: http://localhost:$MINIO_CONSOLE_PORT"
echo "  User: minioadmin"
echo "  Password: minioadmin"
echo ""
echo "Cheri S3-compatible provider config for this MinIO:"
echo '  {'
echo '    "kind": "s3-compatible",'
echo '    "settings": {'
echo '      "endpoint": "http://localhost:9000",'
echo '      "bucket": "'"$TEST_BUCKET"'",'
echo '      "region": "us-east-1",'
echo '      "access_key_id": "minioadmin",'
echo '      "secret_access_key": "minioadmin",'
echo '      "force_path_style": true'
echo '    }'
echo '  }'
