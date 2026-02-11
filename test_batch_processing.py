# WhatsApp Bill Batch Processing - Test Suite
# ==============================================
# Verifies the batch processing endpoint works correctly

import asyncio
import base64
import httpx
from pathlib import Path

# Test configuration
BACKEND_URL = "http://localhost:8000"
BAILEYS_SECRET = "k24_baileys_secret"

async def test_batch_endpoint():
    """Test the batch processing endpoint with sample images"""
    
    # Find test images in the project root
    test_images = list(Path(".").glob("test_invoice_*.jpg"))
    
    if not test_images:
        print("❌ No test images found (test_invoice_*.jpg)")
        print("   Creating dummy test to verify endpoint exists...")
        
        # Just verify endpoint responds
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{BACKEND_URL}/api/baileys/health",
                    timeout=10
                )
                print(f"✅ Health endpoint: {response.status_code}")
                print(f"   Response: {response.json()}")
            except Exception as e:
                print(f"❌ Health check failed: {e}")
        return
    
    print(f"📸 Found {len(test_images)} test images")
    
    # Prepare batch payload
    images_data = []
    for img_path in test_images[:3]:  # Use max 3 for quick test
        img_bytes = img_path.read_bytes()
        images_data.append({
            "buffer": base64.b64encode(img_bytes).decode(),
            "mimetype": "image/jpeg",
            "filepath": str(img_path)
        })
    
    payload = {
        "sender_phone": "7339906200",  # Test phone (hardcoded override in backend)
        "images": images_data,
        "batch_id": "test_batch_001"
    }
    
    print(f"\n🚀 Sending batch of {len(images_data)} images...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/baileys/process-batch",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Baileys-Secret": BAILEYS_SECRET
                },
                timeout=180  # 3 min timeout
            )
            
            print(f"\n📦 Response Status: {response.status_code}")
            
            result = response.json()
            
            if result.get("status") == "success":
                stats = result.get("stats", {})
                print(f"\n✅ BATCH COMPLETE!")
                print(f"   Total: {stats.get('total')}")
                print(f"   Success: {stats.get('success')}")
                print(f"   Failed: {stats.get('failed')}")
                print(f"   Total Items: {stats.get('total_items')}")
                print(f"   Total Amount: ₹{stats.get('total_amount'):,.2f}")
                print(f"   Time: {stats.get('elapsed_seconds')}s")
                
                print("\n📋 Vouchers:")
                for v in result.get("vouchers", []):
                    print(f"   - {v.get('party_name')} | ₹{v.get('total_amount')} | {v.get('items_count')} items")
            else:
                print(f"\n❌ BATCH FAILED: {result.get('error')}")
                
        except httpx.TimeoutException:
            print("❌ Request timed out (batch may still be processing)")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("BATCH PROCESSING TEST")
    print("=" * 60)
    asyncio.run(test_batch_endpoint())
