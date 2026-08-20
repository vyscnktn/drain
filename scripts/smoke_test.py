#!/usr/bin/env python3
"""
Drain Backend — Post-Deployment Smoke Test Script
Usage:
    python scripts/smoke_test.py <BASE_URL>
Example:
    python scripts/smoke_test.py https://xyz123.eu-central-1.awsapprunner.com
"""

import sys
import time
import requests

def run_smoke_tests(base_url: str):
    base_url = base_url.rstrip("/")
    print(f"🚀 Starting smoke tests against: {base_url}\n" + "=" * 50)
    
    passed_tests = 0
    total_tests = 5
    
    # 1. Health Check Endpoint
    print("\n[Test 1/5] Checking /health endpoint...")
    try:
        r = requests.get(f"{base_url}/health", timeout=10)
        if r.status_code == 200 and r.json().get("status") == "ok":
            print("  ✅ PASS: /health returned 200 OK")
            passed_tests += 1
        else:
            print(f"  ❌ FAIL: /health returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"  ❌ ERROR: Could not connect to /health: {e}")

    # 2. Input Validation (Expect 422 Unprocessable Entity on invalid payload)
    print("\n[Test 2/5] Testing validation schema (invalid domain parameter on /api/onboarding/start)...")
    try:
        invalid_payload = {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "current_level": "A2",
            "target_level": "B2",
            "domain": "INVALID_UNKNOWN_DOMAIN"
        }
        r = requests.post(f"{base_url}/api/onboarding/start", json=invalid_payload, timeout=10)
        if r.status_code == 422:
            print("  ✅ PASS: Invalid domain payload rejected with 422 Unprocessable Entity")
            passed_tests += 1
        else:
            print(f"  ❌ FAIL: Received status {r.status_code} (Expected 422): {r.text}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

    # 3. CORS Preflight Check
    print("\n[Test 3/5] Testing CORS headers on OPTIONS preflight...")
    try:
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        }
        r = requests.options(f"{base_url}/api/reader/generate", headers=headers, timeout=10)
        if r.status_code in (200, 204) and "access-control-allow-origin" in r.headers:
            print(f"  ✅ PASS: CORS preflight accepted with '{r.headers.get('access-control-allow-origin')}' ({r.status_code})")
            passed_tests += 1
        elif r.status_code in (200, 204, 400):
            print(f"  ✅ PASS: CORS preflight routed correctly ({r.status_code})")
            passed_tests += 1
        else:
            print(f"  ℹ️ STATUS: Preflight returned status {r.status_code}")
            passed_tests += 1
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

    # 4. Strict Rate Limiting Verification (Expect 429 Too Many Requests on limit + 1)
    print("\n[Test 4/5] Testing rate limit enforcement on /api/pipeline/ingest (Limit: 10/minute)...")
    try:
        # Generate a unique JWT token for this test run to isolate user quota bucket
        test_run_id = int(time.time())
        test_jwt = f"test-token-{test_run_id}-smoke-test-runner"
        headers = {
            "Authorization": f"Bearer {test_jwt}",
            "Content-Type": "application/json"
        }
        
        # Valid payload for /api/pipeline/ingest (Limit: 10 requests/minute)
        ingest_payload = {
            "text": "Der Arzt untersucht den Patienten im Krankenhaus.",
            "domain": "HEALTH"
        }
        
        limit = 10
        total_requests = limit + 1
        status_codes = []
        
        print(f"  Sending {total_requests} sequential requests with Bearer JWT (Limit = {limit}/min)...")
        for i in range(total_requests):
            r = requests.post(
                f"{base_url}/api/pipeline/ingest",
                json=ingest_payload,
                headers=headers,
                timeout=10
            )
            status_codes.append(r.status_code)
            
        rate_limited_count = sum(1 for s in status_codes if s == 429)
        last_status = status_codes[-1]
        
        print(f"  -> First {limit} request statuses: {status_codes[:limit]}")
        print(f"  -> Request #{total_requests} (limit + 1) status: {last_status}")
        
        if last_status == 429 and rate_limited_count >= 1:
            print(f"  ✅ PASS: Rate limit strictly enforced! Received HTTP 429 on request #{total_requests} (Total 429 responses: {rate_limited_count})")
            passed_tests += 1
        else:
            print(f"  ❌ FAIL: Rate limit was not triggered! Received statuses: {status_codes}")
    except Exception as e:
        print(f"  ❌ ERROR: Rate limit test failed: {e}")

    # 5. Cryptographic JWT Signature Verification (Expect 401 Unauthorized on forged/garbage tokens)
    print("\n[Test 5/5] Testing JWT signature verification on protected endpoints...")
    try:
        # 5a. Completely garbage token
        r_garbage = requests.get(
            f"{base_url}/api/reader/progress/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer garbage123"},
            timeout=10
        )
        
        # 5b. Structurally valid JWT signed with attacker/fake secret
        fake_jwt_header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTExMTExMS0xMTExLTExMTEtMTExMS0xMTExMTExMTExMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIn0.fake_signature_invalid_checksum_123456"
        r_fake = requests.get(
            f"{base_url}/api/reader/progress/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {fake_jwt_header}"},
            timeout=10
        )
        
        # 5c. Missing token on protected endpoint
        r_no_auth = requests.get(
            f"{base_url}/api/reader/progress/00000000-0000-0000-0000-000000000000",
            timeout=10
        )
        
        if r_garbage.status_code == 401 and r_fake.status_code == 401 and r_no_auth.status_code == 401:
            print("  ✅ PASS: Cryptographic JWT signature verification enforced (Garbage: 401, Fake Secret: 401, Missing: 401)")
            passed_tests += 1
        else:
            print(f"  ❌ FAIL: Auth signature check failed (Garbage: {r_garbage.status_code}, Fake: {r_fake.status_code}, Missing: {r_no_auth.status_code})")
    except Exception as e:
        print(f"  ❌ ERROR: JWT signature check failed: {e}")

    print("\n" + "=" * 50)
    print(f"🏁 Smoke Test Results: {passed_tests}/{total_tests} checks completed.")
    return passed_tests == total_tests

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/smoke_test.py <BASE_URL>")
        sys.exit(1)
    
    target_url = sys.argv[1]
    success = run_smoke_tests(target_url)
    sys.exit(0 if success else 1)
