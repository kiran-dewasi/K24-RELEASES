#!/usr/bin/env python3
"""
K24 Smoke Test - WhatsApp Pipeline End-to-End Test

Tests the complete flow: WhatsApp → Cloud → Desktop → Tally
Inserts a test message into the queue and verifies the desktop poller processes it.

Usage:
    python tests/smoke_test.py --tenant-id <tenant_id> [--env staging] [--timeout-seconds 120]

Requirements:
    - SUPABASE_URL environment variable
    - SUPABASE_SERVICE_KEY environment variable
    - Desktop poller running and configured for the same database
"""

import argparse
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase library not installed. Run: pip install supabase")
    sys.exit(1)


class SmokeTestRunner:
    """Runs end-to-end smoke test for WhatsApp message processing"""
    
    def __init__(self, tenant_id: str, timeout_seconds: int = 120):
        self.tenant_id = tenant_id
        self.timeout_seconds = timeout_seconds
        self.job_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.transitions: list = []
        
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ ERROR: Missing Supabase credentials")
            print("   Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
            sys.exit(1)
        
        try:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            print(f"✓ Connected to Supabase: {supabase_url}")
        except Exception as e:
            print(f"❌ ERROR: Failed to connect to Supabase: {e}")
            sys.exit(1)
    
    def insert_test_job(self) -> str:
        """
        Insert a test message into the whatsapp_message_queue table
        
        Returns:
            str: The job ID (UUID)
        """
        test_payload = {
            "id": str(uuid.uuid4()),
            "tenant_id": self.tenant_id,
            "user_id": "00000000-0000-0000-0000-000000000001",
            "customer_phone": "917333906200",
            "message_type": "text",
            "message_text": "[SMOKE TEST] hello from smoke_test.py",
            "media_url": None,
            "raw_payload": {},
            "status": "pending",
            "processed_at": None,
            "error_message": None,
            "processing_started_at": None
        }
        
        try:
            result = self.supabase.table("whatsapp_message_queue").insert(test_payload).execute()
            
            if not result.data or len(result.data) == 0:
                raise Exception("Insert returned no data")
            
            job_id = result.data[0]["id"]
            print(f"✓ Inserted test job: {job_id}")
            print(f"  Tenant ID: {self.tenant_id}")
            print(f"  Message: {test_payload['message_content'][:60]}...")
            return job_id
            
        except Exception as e:
            print(f"❌ ERROR: Failed to insert test job: {e}")
            sys.exit(1)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Query the current status of a job
        
        Returns:
            dict: Job record or None if not found
        """
        try:
            result = self.supabase.table("whatsapp_message_queue").select("*").eq("id", job_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to query job status: {e}")
            return None
    
    def record_transition(self, status: str, timestamp: datetime):
        """Record a status transition"""
        elapsed = (timestamp - self.start_time).total_seconds()
        self.transitions.append({
            "status": status,
            "timestamp": timestamp,
            "elapsed_seconds": elapsed
        })
        print(f"  [{elapsed:.1f}s] Status → {status}")
    
    def poll_for_completion(self, job_id: str) -> tuple[bool, str, Optional[str]]:
        """
        Poll the job until it reaches 'processed' or 'failed' status
        
        Returns:
            tuple: (success: bool, final_status: str, error_message: Optional[str])
        """
        self.start_time = datetime.now()
        last_status = "pending"
        poll_count = 0
        
        print(f"\n🔄 Polling for status changes (timeout: {self.timeout_seconds}s)...")
        
        while True:
            poll_count += 1
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            # Check timeout
            if elapsed > self.timeout_seconds:
                print(f"\n❌ TIMEOUT: Job did not complete within {self.timeout_seconds} seconds")
                print(f"   Last known status: {last_status}")
                print(f"   Polls executed: {poll_count}")
                return False, last_status, f"Timeout after {elapsed:.1f}s"
            
            # Get current status
            job = self.get_job_status(job_id)
            if not job:
                print(f"⚠️  Warning: Job {job_id} not found in database")
                time.sleep(2)
                continue
            
            current_status = job.get("status", "unknown")
            
            # Record transition if status changed
            if current_status != last_status:
                self.record_transition(current_status, datetime.now())
                last_status = current_status
            
            # Check for terminal states
            if current_status == "processed":
                print(f"\n✅ Job completed successfully!")
                return True, current_status, None
            
            elif current_status == "failed":
                error_message = job.get("error_message", "No error message provided")
                print(f"\n❌ Job failed with error: {error_message}")
                return False, current_status, error_message
            
            # Continue polling
            time.sleep(2)  # Poll every 2 seconds
    
    def run(self) -> int:
        """
        Execute the full smoke test
        
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        print("\n" + "="*70)
        print("K24 SMOKE TEST - WhatsApp Pipeline E2E Verification")
        print("="*70)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Tenant ID: {self.tenant_id}")
        print(f"Timeout: {self.timeout_seconds}s")
        print("="*70 + "\n")
        
        # Step 1: Insert test job
        print("📤 Step 1: Inserting test job into queue...")
        job_id = self.insert_test_job()
        self.job_id = job_id
        
        # Step 2: Poll for completion
        print("\n📥 Step 2: Waiting for desktop poller to process...")
        success, final_status, error_message = self.poll_for_completion(job_id)
        
        # Step 3: Print results
        print("\n" + "="*70)
        print("SMOKE TEST RESULTS")
        print("="*70)
        print(f"Job ID: {job_id}")
        print(f"Tenant ID: {self.tenant_id}")
        print(f"Final Status: {final_status}")
        
        if self.transitions:
            print(f"\nStatus Transitions:")
            for t in self.transitions:
                timestamp_str = t['timestamp'].strftime('%H:%M:%S')
                print(f"  [{t['elapsed_seconds']:.1f}s] {timestamp_str} → {t['status']}")
        
        total_time = (datetime.now() - self.start_time).total_seconds()
        print(f"\nTotal Time: {total_time:.1f}s")
        
        if success:
            print("\n" + "🎉 " * 15)
            print("SMOKE TEST PASS ✅")
            print("🎉 " * 15 + "\n")
            return 0
        else:
            print("\n" + "❌ " * 15)
            print(f"SMOKE TEST FAIL: {error_message or final_status}")
            print("❌ " * 15 + "\n")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="K24 Smoke Test - E2E WhatsApp Pipeline Verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run smoke test for a specific tenant
    python tests/smoke_test.py --tenant-id K24-abc123

    # With custom timeout
    python tests/smoke_test.py --tenant-id K24-abc123 --timeout-seconds 180

Environment Variables Required:
    SUPABASE_URL            - Your Supabase project URL
    SUPABASE_SERVICE_KEY    - Supabase service role key (server-side)
        """
    )
    
    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant ID to test (e.g., K24-abc123)"
    )
    
    parser.add_argument(
        "--env",
        default="staging",
        help="Environment to test against (default: staging). Currently informational only."
    )
    
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Maximum time to wait for job completion (default: 120)"
    )
    
    args = parser.parse_args()
    
    # Run the smoke test
    runner = SmokeTestRunner(
        tenant_id=args.tenant_id,
        timeout_seconds=args.timeout_seconds
    )
    
    exit_code = runner.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
