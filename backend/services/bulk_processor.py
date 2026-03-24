"""
Bulk Bill Processor for K24
============================
Processes 10-15 bills in parallel using asyncio with rate limiting.
"""

import asyncio
from typing import List, Dict
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)


class BulkBillProcessor:
    """
    Process multiple bills in parallel using asyncio
    """
    
    def __init__(self, max_concurrent: int = 10):
        """
        Initialize bulk processor.
        
        Args:
            max_concurrent: Max bills to process simultaneously. 
                           Set to 10 for fast batch processing of 10-15 bills.
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single_bill(
        self,
        image_path: str,
        user_id: str,
        api_key: str,
        auto_post_enabled: bool = False
    ) -> Dict:
        """
        Process one bill with confidence-based auto-execution.
        
        Args:
            image_path: Path to the bill image
            user_id: User/tenant ID
            api_key: Google API key for Gemini
            auto_post_enabled: If True, auto-post to Tally when confidence >= 95%
        """
        async with self.semaphore:  # Limit concurrency
            try:
                logger.info(f"Processing: {Path(image_path).name}")
                
                # Run blocking Gemini call in thread pool
                loop = asyncio.get_event_loop()
                from agent_gemini import extract_bill_data
                
                bill_data = await loop.run_in_executor(
                    None,  # Use default thread pool
                    extract_bill_data,
                    image_path,
                    api_key
                )
                
                # Check for extraction errors
                if bill_data.get('error'):
                    logger.warning(f"Extraction error for {image_path}: {bill_data['error']}")
                    return {
                        "status": "error",
                        "image": image_path,
                        "error": bill_data['error']
                    }
                
                # ============ AUTO-EXECUTION LOGIC ============
                from services.auto_executor import process_with_auto_execution
                from services.confidence_scorer import calculate_overall_confidence
                
                confidence = calculate_overall_confidence(bill_data)
                
                # Process with auto-execution decision
                execution_result = await process_with_auto_execution(
                    bill_data=bill_data,
                    user_id=user_id,
                    tenant_id=user_id,
                    auto_post_enabled=auto_post_enabled
                )
                
                logger.info(f"Completed: {Path(image_path).name} (Confidence: {confidence:.0%}, Action: {execution_result['action']})")
                
                return {
                    "status": "success",
                    "image": image_path,
                    "action": execution_result.get('action'),
                    "voucher": execution_result.get('voucher'),
                    "items_count": len(bill_data.get('items', [])),
                    "confidence": confidence,
                    "confidence_level": execution_result.get('confidence_level'),
                    "party_name": bill_data.get('party_name'),
                    "total_amount": bill_data.get('total_amount'),
                    "message": execution_result.get('message'),
                    "question": execution_result.get('question'),  # If clarification needed
                    "tally_result": execution_result.get('tally_result')  # If auto-posted
                }
                
            except Exception as e:
                logger.error(f"Failed: {Path(image_path).name} - {str(e)}")
                return {
                    "status": "error",
                    "image": image_path,
                    "error": str(e)
                }
    
    async def process_batch(
        self,
        image_paths: List[str],
        user_id: str,
        api_key: str,
        auto_post_enabled: bool = False
    ) -> Dict:
        """
        Process multiple bills in parallel with auto-execution logic.
        
        Args:
            image_paths: List of paths to bill images
            user_id: User/tenant ID
            api_key: Google API key
            auto_post_enabled: If True, auto-post to Tally when confidence >= 95%
        """
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info(f"BULK PROCESSING: {len(image_paths)} bills")
        logger.info(f"Concurrency: {self.max_concurrent}")
        logger.info(f"Auto-post enabled: {auto_post_enabled}")
        logger.info("=" * 60)
        
        # Create tasks for all bills
        tasks = [
            self.process_single_bill(path, user_id, api_key, auto_post_enabled)
            for path in image_paths
        ]
        
        # Process with rate limit awareness - add delay between batches
        results = []
        batch_size = self.max_concurrent
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append({
                        "status": "error",
                        "error": str(result)
                    })
                else:
                    results.append(result)
            
            # Small delay between batches to avoid rate limits
            if i + batch_size < len(tasks):
                await asyncio.sleep(1.0)
        
        elapsed = time.time() - start_time
        
        # Compile summary with auto-execution stats
        success_count = sum(1 for r in results if r.get('status') == 'success')
        error_count = len(results) - success_count
        
        # Count by action type
        auto_posted = sum(1 for r in results if r.get('action') == 'auto_posted')
        auto_created = sum(1 for r in results if r.get('action') == 'auto_created')
        needs_review = sum(1 for r in results if r.get('action') == 'needs_review')
        needs_clarification = sum(1 for r in results if r.get('action') == 'needs_clarification')
        
        summary = {
            "total_bills": len(image_paths),
            "success": success_count,
            "errors": error_count,
            "elapsed_seconds": round(elapsed, 2),
            "avg_per_bill": round(elapsed / len(image_paths), 2) if image_paths else 0,
            # Auto-execution breakdown
            "auto_posted": auto_posted,
            "auto_created": auto_created,
            "needs_review": needs_review,
            "needs_clarification": needs_clarification,
            "results": results
        }
        
        logger.info("=" * 60)
        logger.info(f"COMPLETED: {success_count}/{len(image_paths)} bills in {elapsed:.1f}s")
        logger.info(f"  âœ… Auto-posted: {auto_posted} | Auto-created: {auto_created}")
        logger.info(f"  âš ï¸ Needs review: {needs_review} | â“ Needs clarification: {needs_clarification}")
        logger.info("=" * 60)
        
        return summary


# Convenience function for synchronous callers
def process_bills_sync(
    image_paths: List[str],
    user_id: str,
    api_key: str,
    max_concurrent: int = 5
) -> Dict:
    """
    Synchronous wrapper for bulk processing.
    Use this from non-async code.
    """
    processor = BulkBillProcessor(max_concurrent=max_concurrent)
    return asyncio.run(processor.process_batch(image_paths, user_id, api_key))


# Singleton for reuse
bulk_processor = BulkBillProcessor(max_concurrent=10)

