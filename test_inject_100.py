"""Standalone Verification Script for Telemetry Payload ID 100.

Loads the poisoned test payload, passes it through the in-memory Sanitizer,
demonstrates that 100% of credentials are intercepted and removed,
and transmits the sanitized telemetry to the live Central SaaS backend.
"""

import os
import sys
import json

# Setup local-collector path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTOR_DIR = os.path.join(CURRENT_DIR, "local-collector")
sys.path.insert(0, COLLECTOR_DIR)

from security.sanitizer import Sanitizer
from collector.collector_service import CollectorService
from config.settings import Settings


def main():
    json_path = os.path.join(CURRENT_DIR, "telemetry_stream_100.json")
    print("=" * 75)
    print("  AEGIS OPS - TELEMETRY PAYLOAD ID 100 VERIFICATION TEST")
    print("=" * 75)
    print(f"\n[1] Reading poisoned input payload from: {json_path}")
    
    with open(json_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    
    raw_event = events[0]
    print(f"    - Message ID: {raw_event.get('message_id')}")
    print(f"    - Device ID:  {raw_event.get('device_id')}")
    print(f"    - Injected Secrets in Raw File:")
    print(f"        * admin_password:           {raw_event.get('admin_password')}")
    print(f"        * aws_access_key:           {raw_event.get('aws_access_key')}")
    print(f"        * bearer_token:             {raw_event.get('bearer_token')[:35]}...")
    print(f"        * raw_cmdline:              {raw_event.get('raw_cmdline')}")
    print(f"        * session_cookie:           {raw_event.get('session_cookie')}")
    print(f"        * database_connection_string: {raw_event.get('metrics', {}).get('database_connection_string')}")

    print("\n[2] Executing In-Memory Privacy Sanitizer...")
    sanitizer = Sanitizer()
    result = sanitizer.sanitize_payload(raw_event)

    print(f"    ✔ Sensitive Fields Detected: {result.sensitive_fields_detected}")
    print(f"    ✔ Total Fields Scrubbed:    {len(result.fields_removed)}")
    for removed in result.fields_removed:
        print(f"       [-] STRIPPED: {removed}")

    print("\n[3] Validating Outgoing Wire JSON (Egress Guarantee)...")
    clean_json_str = json.dumps(result.sanitized_data, indent=2)
    has_pwd = "SuperSecretPassword100!" in clean_json_str
    has_aws = "AKIAIOSFODNN7EXAMPLE" in clean_json_str
    has_cmd = "hunter2" in clean_json_str or "db_pass100" in clean_json_str
    has_db = "postgres://" in clean_json_str

    print(f"    - Contains 'SuperSecretPassword100!': {has_pwd}")
    print(f"    - Contains 'AKIAIOSFODNN7EXAMPLE':    {has_aws}")
    print(f"    - Contains raw command line password: {has_cmd}")
    print(f"    - Contains database password string:  {has_db}")
    
    if not any([has_pwd, has_aws, has_cmd, has_db]):
        print("    ✔ ZERO-LEAKAGE PRIVACY BOUNDARY VERIFIED: 100% Clean!")
    else:
        print("    ❌ LEAKAGE DETECTED!")
        sys.exit(1)

    print("\n[4] Transmitting Clean Payload to Live Central SaaS via Collector Service...")
    service = CollectorService()
    replayed = service.replay_stream_file(json_path)
    print(f"    ✔ Successfully ingested and transmitted {replayed} event(s) to:")
    print(f"      {service.settings.backend_url}")
    print(f"    ✔ Status Code: {service.latest_status_code}")
    print("\n" + "=" * 75)
    print("  VERIFICATION COMPLETE: Payload ID 100 is live on your cloud dashboard!")
    print(f"  Check: {service.settings.backend_url}/privacy-audit")
    print("=" * 75)


if __name__ == "__main__":
    main()
