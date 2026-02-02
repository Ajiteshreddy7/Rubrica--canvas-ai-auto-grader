"""
Submission Queue Management

FIFO queue for processing student submissions across all assignments.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import threading

QUEUE_FILE = Path(__file__).parent / "queue.json"
_lock = threading.Lock()


def _load_queue() -> Dict[str, Any]:
    """Load queue from disk."""
    if not QUEUE_FILE.exists():
        return {
            "pending": [],
            "processing": None,
            "completed": [],
            "failed": []
        }
    
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_queue(queue_data: Dict[str, Any]):
    """Save queue to disk."""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, indent=2)


def add_to_queue(
    assignment_id: str,
    assignment_title: str,
    student_login: str,
    submission_data: Dict[str, Any]
) -> str:
    """
    Add a submission to the queue.
    
    Args:
        assignment_id: Canvas assignment ID
        assignment_title: Assignment name
        student_login: Student login ID
        submission_data: Full submission dict from Canvas
    
    Returns:
        Queue item ID (composite key)
    """
    with _lock:
        queue = _load_queue()
        
        # Create queue item
        item_id = f"{assignment_id}_{student_login}"
        
        # Check if already in queue
        existing_ids = {item["id"] for item in queue["pending"]}
        if item_id in existing_ids:
            return item_id  # Already queued
        
        # Check if currently processing
        if queue["processing"] and queue["processing"]["id"] == item_id:
            return item_id  # Currently being processed
        
        # Check if completed
        completed_ids = {item["id"] for item in queue["completed"]}
        if item_id in completed_ids:
            return item_id  # Already completed
        
        item = {
            "id": item_id,
            "assignment_id": assignment_id,
            "assignment_title": assignment_title,
            "student_login": student_login,
            "submission_type": submission_data.get("type", "unknown"),
            "submission_url": submission_data.get("url", ""),
            "submission_id": submission_data.get("id", ""),
            "queued_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        queue["pending"].append(item)
        _save_queue(queue)
        
        return item_id


def get_next() -> Optional[Dict[str, Any]]:
    """
    Get next submission from queue (FIFO).
    
    Marks it as 'processing' and removes from pending.
    Returns None if queue is empty or something is already processing.
    """
    with _lock:
        queue = _load_queue()
        
        # Check if something is already being processed
        if queue["processing"] is not None:
            return None
        
        # Check if queue is empty
        if not queue["pending"]:
            return None
        
        # Get first item (FIFO)
        item = queue["pending"].pop(0)
        item["status"] = "processing"
        item["started_at"] = datetime.now().isoformat()
        
        queue["processing"] = item
        _save_queue(queue)
        
        return item


def mark_completed(item_id: str, score: float, grading_file: str):
    """
    Mark a submission as completed successfully.
    
    Moves from processing to completed list.
    """
    with _lock:
        queue = _load_queue()
        
        if queue["processing"] and queue["processing"]["id"] == item_id:
            item = queue["processing"]
            item["status"] = "completed"
            item["score"] = score
            item["grading_file"] = grading_file
            item["completed_at"] = datetime.now().isoformat()
            
            queue["completed"].append(item)
            queue["processing"] = None
            
            _save_queue(queue)


def mark_failed(item_id: str, error: str):
    """
    Mark a submission as failed.
    
    Moves from processing to failed list.
    Preserves retry_count for tracking retry attempts.
    """
    with _lock:
        queue = _load_queue()
        
        if queue["processing"] and queue["processing"]["id"] == item_id:
            item = queue["processing"]
            item["status"] = "failed"
            item["error"] = error
            item["failed_at"] = datetime.now().isoformat()
            # Preserve retry count
            item["retry_count"] = item.get("retry_count", 0)
            
            queue["failed"].append(item)
            queue["processing"] = None
            
            _save_queue(queue)


def retry_failed(item_id: str) -> bool:
    """
    Move a failed submission back to pending queue.
    
    Increments retry_count and preserves error history.
    Returns True if successful, False if not found.
    """
    with _lock:
        queue = _load_queue()
        
        # Find in failed list
        for i, item in enumerate(queue["failed"]):
            if item["id"] == item_id:
                # Remove from failed
                failed_item = queue["failed"].pop(i)
                
                # Increment retry count
                failed_item["retry_count"] = failed_item.get("retry_count", 0) + 1
                
                # Preserve error history
                if "error" in failed_item:
                    failed_item["last_error"] = failed_item.pop("error")
                if "failed_at" in failed_item:
                    failed_item["last_failed_at"] = failed_item.pop("failed_at")
                
                # Reset and add to pending
                failed_item["status"] = "pending"
                failed_item["retried_at"] = datetime.now().isoformat()
                
                queue["pending"].append(failed_item)
                _save_queue(queue)
                
                return True
        
        return False


def get_retryable_failed(max_retries: int = 1) -> List[Dict[str, Any]]:
    """
    Get failed submissions that are eligible for retry.
    
    WinError 5 (access denied) failures are ALWAYS retryable (don't count toward max_retries)
    since they're just Windows file locks that don't need human intervention.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 1)
    
    Returns:
        List of failed items eligible for retry
    """
    with _lock:
        queue = _load_queue()
        retryable = []
        
        for item in queue["failed"]:
            error = item.get("error", item.get("last_error", ""))
            
            # WinError 5 (access denied) - always retry, don't count toward max
            if "WinError 5" in error or "Access is denied" in error:
                retryable.append(item)
            # Other errors - respect max_retries
            elif item.get("retry_count", 0) < max_retries:
                retryable.append(item)
        
        return retryable


def retry_all_eligible(max_retries: int = 1) -> int:
    """
    Move all eligible failed submissions back to pending queue.
    
    WinError 5 (access denied) failures are ALWAYS retried (don't count toward max_retries).
    Deduplicates by student to avoid retrying same student multiple times.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 1)
    
    Returns:
        Number of items moved to pending
    """
    with _lock:
        queue = _load_queue()
        
        retried_count = 0
        new_failed = []
        seen_students = set()  # Track to avoid duplicates
        
        for item in queue["failed"]:
            retry_count = item.get("retry_count", 0)
            error = item.get("error", item.get("last_error", ""))
            student_key = f"{item['assignment_id']}_{item['student_login']}"
            
            # Skip duplicates for same student in same assignment
            if student_key in seen_students:
                continue
            
            is_file_lock = "WinError 5" in error or "Access is denied" in error
            
            # WinError 5 - always retry, don't increment retry_count
            if is_file_lock or retry_count < max_retries:
                seen_students.add(student_key)
                
                # Only increment retry_count for non-file-lock errors
                if not is_file_lock:
                    item["retry_count"] = retry_count + 1
                
                # Preserve error history
                if "error" in item:
                    item["last_error"] = item.pop("error")
                if "failed_at" in item:
                    item["last_failed_at"] = item.pop("failed_at")
                
                # Reset and add to pending
                item["status"] = "pending"
                item["retried_at"] = datetime.now().isoformat()
                
                queue["pending"].append(item)
                retried_count += 1
            else:
                # Keep in failed (max retries reached for non-file-lock errors)
                new_failed.append(item)
        
        queue["failed"] = new_failed
        _save_queue(queue)
        
        return retried_count


def get_status() -> Dict[str, Any]:
    """
    Get overall queue status.
    
    Returns dict with:
    - pending_count: Number waiting to be processed
    - processing: Currently processing item (or None)
    - completed_count: Number successfully completed
    - failed_count: Number failed
    - pending_items: List of pending items
    - failed_items: List of failed items
    """
    with _lock:
        queue = _load_queue()
        
        return {
            "pending_count": len(queue["pending"]),
            "processing": queue["processing"],
            "completed_count": len(queue["completed"]),
            "failed_count": len(queue["failed"]),
            "pending_items": queue["pending"],
            "failed_items": queue["failed"]
        }


def clear_completed(keep_last_n: int = 100):
    """
    Clear completed items to keep queue file small.
    
    Keeps only the last N completed items.
    """
    with _lock:
        queue = _load_queue()
        
        if len(queue["completed"]) > keep_last_n:
            queue["completed"] = queue["completed"][-keep_last_n:]
            _save_queue(queue)


def remove_from_queue(item_id: str) -> bool:
    """
    Remove an item from pending queue (if not yet processing).
    
    Returns True if removed, False if not found or already processing.
    """
    with _lock:
        queue = _load_queue()
        
        # Check if processing
        if queue["processing"] and queue["processing"]["id"] == item_id:
            return False  # Can't remove while processing
        
        # Find in pending
        for i, item in enumerate(queue["pending"]):
            if item["id"] == item_id:
                queue["pending"].pop(i)
                _save_queue(queue)
                return True
        
        return False
