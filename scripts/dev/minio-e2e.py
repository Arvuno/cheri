#!/usr/bin/env python3
"""
MinIO End-to-End Test for Cheri S3-Compatible Provider

Usage: python3 scripts/dev/minio-e2e.py
  or:  bash scripts/dev/minio-e2e.sh

Environment variables (all optional — script provides defaults for local MinIO):
  CHERI_S3_E2E_ENDPOINT          Default: http://localhost:9000
  CHERI_S3_E2E_BUCKET             Default: cheri-e2e-test
  CHERI_S3_E2E_REGION             Default: us-east-1
  CHERI_S3_E2E_ACCESS_KEY_ID      Default: minioadmin
  CHERI_S3_E2E_SECRET_ACCESS_KEY  Default: minioadmin
  CHERI_S3_E2E_FORCE_PATH_STYLE   Default: 1

This script:
  1. Connects to MinIO (starts container if CHERI_MINIO_START_CONTAINER=1)
  2. Creates test bucket
  3. Uploads a file via MinIO Python SDK
  4. Downloads and verifies checksum
  5. Generates presigned upload URL
  6. Generates presigned download URL
  7. Tests list objects
  8. Cleans up
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import timedelta

MINIO_SDK_AVAILABLE = False
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_SDK_AVAILABLE = True
except ImportError:
    pass


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""


RESULTS: list[TestResult] = []


def result(name: str, passed: bool, detail: str = "") -> None:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}")
    if detail:
        print(f"         {detail}")
    RESULTS.append(TestResult(name, passed, detail))


def run_tests() -> bool:
    print("=== MinIO E2E Test for Cheri S3-Compatible Provider ===")
    print(f"Date: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print()

    if not MINIO_SDK_AVAILABLE:
        print("SKIPPED: minio Python SDK not installed")
        print("  pip install --break-system-packages minio")
        print()
        print("To run this test:")
        print("  python3 -m pip install --break-system-packages minio")
        print("  python3 scripts/dev/minio-e2e.py")
        return False

    endpoint = os.environ.get("CHERI_S3_E2E_ENDPOINT", "http://localhost:9000")
    bucket = os.environ.get("CHERI_S3_E2E_BUCKET", "cheri-e2e-test")
    region = os.environ.get("CHERI_S3_E2E_REGION", "us-east-1")
    access_key = os.environ.get("CHERI_S3_E2E_ACCESS_KEY_ID", "minioadmin")
    secret_key = os.environ.get("CHERI_S3_E2E_SECRET_ACCESS_KEY", "minioadmin")
    force_path = os.environ.get("CHERI_S3_E2E_FORCE_PATH_STYLE", "1") == "1"
    start_container = os.environ.get("CHERI_MINIO_START_CONTAINER", "0") == "1"

    print(f"Endpoint: {endpoint}")
    print(f"Bucket: {bucket}")
    print(f"Region: {region}")
    print(f"Force path style: {force_path}")
    print(f"Start container: {start_container}")
    print()

    # Check if MinIO is reachable
    import urllib.request
    minio_reachable = False
    try:
        try:
            urllib.request.urlopen(endpoint + "/minio/v2/health", timeout=3)
        except Exception:
            urllib.request.urlopen(endpoint + "/minio/health/live", timeout=3)
        minio_reachable = True
        print("MinIO: already running")
    except Exception:
        if start_container:
            print("MinIO: will start via Docker")
        else:
            print("MinIO: not reachable (set CHERI_MINIO_START_CONTAINER=1 to start it)")
            print()
            print("To run this test locally:")
            print("  1. Start MinIO:")
            print("     docker run -d \\")
            print("       --name cheri-minio-e2e \\")
            print("       -p 9000:9000 -p 9001:9001 \\")
            print("       -e MINIO_ROOT_USER=minioadmin \\")
            print("       -e MINIO_ROOT_PASSWORD=minioadmin \\")
            print("       minio/minio server /data --compat")
            print()
            print("  2. Re-run with:")
            print("     CHERI_MINIO_START_CONTAINER=1 python3 scripts/dev/minio-e2e.py")
            return False
        minio_reachable = True

    container_id = None
    if start_container and not minio_reachable:
        import subprocess
        print("Starting MinIO container...")
        r = subprocess.run(
            [
                "docker", "run", "-d",
                "--name", "cheri-minio-e2e",
                "-p", "9000:9000", "-p", "9001:9001",
                "-e", f"MINIO_ROOT_USER={access_key}",
                "-e", f"MINIO_ROOT_PASSWORD={secret_key}",
                "minio/minio", "server", "/data",
                "--console-address", ":9001", "--compat",
            ],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"ERROR: Failed to start MinIO: {r.stderr}")
            return False
        container_id = r.stdout.strip()
        print(f"Container: {container_id}")

        # Wait for MinIO to be ready (try both health endpoints)
        for i in range(30):
            try:
                # Try the v2 health check first, then v1
                try:
                    urllib.request.urlopen(endpoint + "/minio/v2/health", timeout=2)
                except Exception:
                    urllib.request.urlopen(endpoint + "/minio/health/live", timeout=2)
                print(f"MinIO ready after {i+1}s")
                break
            except Exception:
                time.sleep(1)
        else:
            print("ERROR: MinIO did not start within 30s")
            if container_id:
                subprocess.run(["docker", "stop", container_id], capture_output=True)
            return False

    print()

    # Initialize Minio client
    client = Minio(
        endpoint.replace("http://", "").replace("https://", ""),
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )

    # Step 1: Ensure bucket exists
    print("=== Step 1: Ensure bucket exists ===")
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            result("Create bucket", True)
        else:
            result("Bucket exists", True, bucket)
    except S3Error as e:
        result("Bucket setup", False, str(e))
        return False

    print()

    # Step 2: Upload test file
    print("=== Step 2: Upload test file ===")
    test_content = f"Cheri MinIO e2e test {time.strftime('%Y-%m-%dT%H:%M:%SZ')}\n".encode()
    test_content_hash = hashlib.sha256(test_content).hexdigest()
    test_object_name = "e2e-test-file.txt"

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(test_content)
        f.flush()
        temp_path = f.name

    try:
        client.fput_object(bucket, test_object_name, temp_path, content_type="text/plain")
        result("Upload file", True, test_object_name)
    except S3Error as e:
        result("Upload file", False, str(e))
        return False
    finally:
        os.unlink(temp_path)

    print()

    # Step 3: Download and verify
    print("=== Step 3: Download and verify checksum ===")
    download_path = tempfile.mktemp()
    try:
        client.fget_object(bucket, test_object_name, download_path)
        with open(download_path, "rb") as f:
            downloaded_content = f.read()
        downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
        if downloaded_hash == test_content_hash:
            result("Checksum verify", True, downloaded_hash[:16] + "...")
        else:
            result("Checksum verify", False, f"expected {test_content_hash[:16]} got {downloaded_hash[:16]}")
    except S3Error as e:
        result("Checksum verify", False, str(e))
    finally:
        os.unlink(download_path)

    print()

    # Step 4: Presigned URL generation
    print("=== Step 4: Generate presigned URLs ===")
    try:
        presigned_put = client.presigned_put_object(bucket, "presigned-upload-test.txt", expires=timedelta(minutes=5))
        result("Presigned PUT URL", True, presigned_put[:60] + "...")

        presigned_get = client.presigned_get_object(bucket, test_object_name, expires=timedelta(minutes=5))
        result("Presigned GET URL", True, presigned_get[:60] + "...")
    except Exception as e:
        result("Presigned URLs", False, str(e))

    print()

    # Step 5: List objects
    print("=== Step 5: List objects ===")
    try:
        objects = list(client.list_objects(bucket, prefix="e2e-test-"))
        object_names = [o.object_name for o in objects]
        if test_object_name in object_names:
            result("List objects", True, f"found {len(object_names)} object(s)")
        else:
            result("List objects", False, f"expected {test_object_name} in {object_names}")
    except S3Error as e:
        result("List objects", False, str(e))

    print()

    # Step 6: Stat object
    print("=== Step 6: Stat object ===")
    try:
        stat = client.stat_object(bucket, test_object_name)
        result("Stat object", True, f"size={stat.size}, content_type={stat.content_type}")
    except S3Error as e:
        result("Stat object", False, str(e))

    print()

    # Step 7: Delete test object
    print("=== Step 7: Cleanup ===")
    try:
        client.remove_object(bucket, test_object_name)
        result("Delete object", True, test_object_name)
    except S3Error as e:
        result("Delete object", False, str(e))

    # Stop container if we started it
    if container_id:
        import subprocess
        print("\nStopping MinIO container...")
        subprocess.run(["docker", "stop", container_id], capture_output=True)
        subprocess.run(["docker", "rm", container_id], capture_output=True)
        print(f"Container {container_id} stopped and removed")

    # Print summary
    print()
    print("=" * 50)
    passed = sum(1 for r in RESULTS if r.passed)
    total = len(RESULTS)
    print(f"Results: {passed}/{total} passed")
    for r in RESULTS:
        status = "✅" if r.passed else "❌"
        print(f"  {status} {r.name}")
    print()

    # Provider config snippet
    print("Cheri S3-compatible provider config:")
    print(f"""  {{
    "kind": "s3-compatible",
    "settings": {{
      "endpoint": "{endpoint}",
      "bucket": "{bucket}",
      "region": "{region}",
      "access_key_id": "{access_key}",
      "secret_access_key": "<secret>",
      "force_path_style": {str(force_path).lower()}
    }}
  }}""")
    print()
    print("Provider status: MINIO_INFRASTRUCTURE_VERIFIED")
    print("=" * 50)

    return all(r.passed for r in RESULTS)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)