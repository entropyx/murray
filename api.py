from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import RedirectResponse
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel
import numpy as np
import io
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv
import logging
from datetime import datetime
import sys
from celery_app import celery_app
from tasks import analyze_design_task, analyze_evaluation_task
from celery.result import AsyncResult
import requests
import redis
from celery import current_task
import httpx
from tasks import progress_tracker, webhook_manager

load_dotenv()

API_KEY = os.environ.get("MY_API_KEY", "default_key")
api_key_header = APIKeyHeader(name="X-API-Key")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)

def check_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Not authorized")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger("murray_api")

app = FastAPI(
    title="Murray API",
    dependencies=[Depends(check_api_key)],
    description="API for experimental design and evaluation using Murray. Supports both single-cell and multicell analysis modes.",
    version="1.1.0"
)

class TaskResponse(BaseModel):
    task_id: str
    status: str
    results: Optional[Dict[str, Any]] = None

class AnalysisResponse(BaseModel):
    task_id: str
    results: Dict[str, Any]

class ProgressResponse(BaseModel):
    task_id: str
    progress: float
    progress_percentage: int
    status: str  # General status (pending, started, completed, failed, etc.)
    task_status: str  # Specific task stage (Data Loading & Processing, etc.)
    details: str
    updated_at: str
    webhook_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def convert_ndarrays(obj):
    # Convert arrays
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # Convert scalars
    elif isinstance(obj, (np.generic,)):
        return obj.item()
    # Convert dictionaries (also converts keys if they are numpy)
    elif isinstance(obj, dict):
        return {convert_ndarrays(k): convert_ndarrays(v) for k, v in obj.items()}
    # Convert lists
    elif isinstance(obj, list):
        return [convert_ndarrays(i) for i in obj]
    # Convert tuples
    elif isinstance(obj, tuple):
        return tuple(convert_ndarrays(i) for i in obj)
    # Convert sets
    elif isinstance(obj, set):
        return {convert_ndarrays(i) for i in obj}
    else:
        return obj

def find_numpy_objects(obj, path="root"):
    found = []
    if isinstance(obj, np.ndarray):
        found.append(f"{path} (type: {type(obj)})")
    elif isinstance(obj, (np.generic,)):
        found.append(f"{path} (type: {type(obj)})")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            found.extend(find_numpy_objects(v, f"{path}['{k}']"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(find_numpy_objects(v, f"{path}[{i}]"))
    elif isinstance(obj, tuple):
        for i, v in enumerate(obj):
            found.extend(find_numpy_objects(v, f"{path}({i})"))
    return found

def truncate_large_lists(obj, max_len=10):
    if isinstance(obj, list) and len(obj) > max_len:
        return obj[:max_len] + ['...truncated...']
    elif isinstance(obj, dict):
        return {k: truncate_large_lists(v, max_len) for k, v in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(truncate_large_lists(i, max_len) for i in obj)
    else:
        return obj

@app.post("/analyze/design", response_model=TaskResponse)
async def analyze_design(
    file: UploadFile = File(None),
    date_column: str = Form(None),
    location_column: str = Form(None),
    target_column: str = Form(None),
    excluded_locations: str = Form(None),
    maximum_treatment_percentage: float = Form(0.3),
    significance_level: float = Form(0.1),
    deltas_range: str = Form("0.01,0.1,0.01"),
    periods_range: str = Form("5,15,5"),
    enable_multicell: bool = Form(False),
    multicell_sizes: str = Form(""),
    multicell_cells_count: int = Form(3),
    webhook: str = Form(None)
):
    """
    Submit design analysis task
    
    Supports both single-cell and multicell analysis modes:
    
    **Single-cell mode (default):**
    - Finds optimal treatment groups for each size
    - Use when enable_multicell=False
    
    **Multicell mode:**
    - Creates a single experiment with multiple cells of different sizes
    - Use when enable_multicell=True
    - Requires multicell_sizes (comma-separated, e.g., "2,3,4")
    - multicell_cells_count defines total number of cells in experiment
    
    **Example usage:**
    
    Single-cell mode:
    - enable_multicell=False (default)
    - multicell_sizes and multicell_cells_count are ignored
    
    Multicell mode:
    - enable_multicell=True
    - multicell_sizes="2,3,4"  # Allowed cell sizes
    - multicell_cells_count=3  # Total cells in final experiment
    
    **Response format:**
    ```json
    {
        "analysis_mode": "single-cell" | "multicell",
        "multicell_config": {"sizes": [2,3,4], "top_n": 3} | null,
        "global_optimization": false | true,
        "results": { ... }
    }
    ```
    """
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"[{request_id}] Submitting design analysis task")
    
    try:
        contents = await file.read()
        
        # Parse parameters
        deltas_range = tuple(map(float, deltas_range.split(',')))
        periods_range = tuple(map(int, periods_range.split(',')))
        # Handle empty excluded_locations properly
        if excluded_locations and excluded_locations.strip():
            excluded_locations = tuple(map(str, excluded_locations.split(',')))
        else:
            excluded_locations = tuple()
        
        # Process multicell parameters
        multicell_config = None
        if enable_multicell:
            if not multicell_sizes.strip():
                raise HTTPException(status_code=400, detail="multicell_sizes is required when enable_multicell=True")
            
            try:
                sizes_list = list(map(int, multicell_sizes.split(',')))
                if len(sizes_list) == 0:
                    raise ValueError("At least one size must be specified")
                if any(size <= 0 for size in sizes_list):
                    raise ValueError("All sizes must be positive integers")
                if multicell_cells_count <= 0:
                    raise ValueError("multicell_cells_count must be positive")
                
                multicell_config = {
                    "sizes": sizes_list,
                    "top_n": multicell_cells_count
                }
                logger.info(f"[{request_id}] Multicell mode enabled with config: {multicell_config}")
                
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=f"Invalid multicell parameters: {str(ve)}")
        else:
            logger.info(f"[{request_id}] Single-cell mode enabled")
        
        # Prepare webhook dict if URL is provided
        webhook_dict = {"url": webhook} if webhook else None
        
        # Submit task to Celery
        task = analyze_design_task.delay(
            file_content=contents,
            date_column=date_column,
            location_column=location_column,
            target_column=target_column,
            excluded_locations=excluded_locations,
            maximum_treatment_percentage=maximum_treatment_percentage,
            significance_level=significance_level,
            deltas_range=deltas_range,
            periods_range=periods_range,
            multicell_config=multicell_config,
            global_optimization=enable_multicell,
            webhook=webhook_dict
        )
        
        logger.info(f"[{request_id}] Task submitted with ID: {task.id}")

        # Notify PENDING state immediately
        if webhook_dict:
            try:
                httpx.post(webhook_dict["url"], json={
                    "status": "pending",
                    "task_id": task.id,
                    "message": "Task queued for processing",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as ex:
                logger.error(f"[{task.id}] Error sending pending webhook: {str(ex)}")

        return TaskResponse(task_id=task.id, status="PENDING", results={"message": "Task submitted"})
        
    except Exception as e:
        logger.error(f"[{request_id}] Error submitting design analysis task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/evaluation", response_model=TaskResponse)
async def analyze_evaluation(
    file: UploadFile = File(...),
    date_column: str = Form(...),
    location_column: str = Form(...),
    target_column: str = Form(...),
    treatment_start_date: str = Form(...),
    treatment_end_date: str = Form(...),
    treatment_group: str = Form(...),
    spend: float = Form(...),
    mmm_option: str = Form(...),
    webhook: str = Form(None)
):
    """
    Submit evaluation analysis task
    """
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"[{request_id}] Starting evaluation analysis request")
    
    try:
        contents = await file.read()
        treatment_group = list(map(str, treatment_group.split(',')))
        
        # Prepare webhook dict if URL is provided
        webhook_dict = {"url": webhook} if webhook else None
        
        # Submit task to Celery
        task = analyze_evaluation_task.delay(
            file_content=contents,
            date_column=date_column,
            location_column=location_column,
            target_column=target_column,
            treatment_start_date=treatment_start_date,
            treatment_end_date=treatment_end_date,
            treatment_group=treatment_group,
            spend=spend,
            mmm_option=mmm_option,
            webhook=webhook_dict
        )
        
        logger.info(f"[{request_id}] Task submitted with ID: {task.id}")

        # Notify PENDING state immediately
        if webhook_dict:
            try:
                httpx.post(webhook_dict["url"], json={
                    "status": "pending",
                    "task_id": task.id,
                    "message": "Task queued for processing",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as ex:
                logger.error(f"[{task.id}] Error sending pending webhook: {str(ex)}")

        return TaskResponse(task_id=task.id, status="PENDING", results={"message": "Task submitted"})

    except Exception as e:
        logger.error(f"[{request_id}] Error submitting evaluation analysis task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    Get the status and results of a task
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.ready():
        if task_result.successful():
            results = convert_ndarrays(task_result.result)
            # results = truncate_large_lists(results)
            return TaskResponse(
                task_id=task_id,
                status="SUCCESS",
                results=results
            )
        elif task_result.failed():
            return TaskResponse(
                task_id=task_id,
                status="FAILURE",
                results={"error": str(task_result.result)}
            )
        elif task_result.revoked():
            return TaskResponse(
                task_id=task_id,
                status="REVOKED",
                results={
                    "message": "Task was cancelled/revoked",
                    "details": "The task was cancelled by user request or system intervention",
                    "cancelled_at": datetime.now().isoformat(),
                    "final_status": "cancelled"
                }
            )
    elif task_result.state == "RETRY":
        return TaskResponse(
            task_id=task_id,
            status="RETRY",
            results={"message": "Task is being retried"}
        )
    elif task_result.state == "STARTED":
        return TaskResponse(
            task_id=task_id,
            status="STARTED",
            results={"message": "Task is currently running"}
        )
    else:
        return TaskResponse(
            task_id=task_id,
            status="PENDING",
            results={"message": "Task is waiting for execution"}
        )

@app.get("/task/{task_id}/progress", response_model=ProgressResponse)
async def get_task_progress(task_id: str):
    """
    Get detailed progress information for a running task.

    Returns real-time progress including:
    - Progress percentage (0-100)
    - General task status (pending, started, completed, etc.)
    - Specific task stage (Data Loading & Processing, etc.)
    - Detailed progress information
    - Last update timestamp
    - Webhook configuration
    """
    try:
        # Get Celery task status for general status
        task_result = AsyncResult(task_id, app=celery_app)

        # Determine general status from Celery
        if task_result.state == "PENDING":
            general_status = "pending"
        elif task_result.state == "STARTED":
            general_status = "started"
        elif task_result.state == "SUCCESS":
            general_status = "completed"
        elif task_result.state == "FAILURE":
            general_status = "failed"
        elif task_result.state == "REVOKED":
            general_status = "revoked"
        elif task_result.state == "RETRY":
            general_status = "retrying"
        else:
            general_status = "unknown"

        progress_data = progress_tracker.get_progress(task_id)

        if not progress_data:
            # If no progress data but task exists in Celery
            if task_result.state == "PENDING":
                raise HTTPException(
                    status_code=404,
                    detail=f"No progress information found for task {task_id}. Task may not exist or may not have started yet."
                )
            elif task_result.state == "FAILURE":
                # Return failure status even without progress data
                return ProgressResponse(
                    task_id=task_id,
                    progress=0.0,
                    progress_percentage=0,
                    status="failed",
                    task_status="failed",
                    details=f"Task failed: {str(task_result.result) if task_result.result else 'Unknown error'}",
                    updated_at=datetime.now().isoformat(),
                    webhook_url=None
                )
            elif task_result.state == "SUCCESS":
                raise HTTPException(
                    status_code=410,
                    detail=f"Task {task_id} is completed. Progress information is no longer available."
                )
            elif task_result.state == "REVOKED":
                # Return cancellation status for revoked tasks
                return ProgressResponse(
                    task_id=task_id,
                    progress=0.0,
                    progress_percentage=0,
                    status="revoked",
                    task_status="cancelled",
                    details="Task was cancelled by user request or system intervention",
                    updated_at=datetime.now().isoformat(),
                    webhook_url=None
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No progress information found for task {task_id}"
                )

        # If task failed, update details with error information
        if general_status == "failed" and progress_data:
            error_details = f"Task failed: {str(task_result.result) if task_result.result else 'Unknown error'}"
            return ProgressResponse(
                task_id=task_id,
                progress=progress_data.get("progress", 0.0),
                progress_percentage=int(progress_data.get("progress", 0.0) * 100),
                status=general_status,  # General Celery status
                task_status="failed",  # Override with failed status
                details=error_details,  # Show actual error
                updated_at=progress_data.get("updated_at", ""),
                webhook_url=progress_data.get("webhook_url")
            )

        return ProgressResponse(
            task_id=task_id,
            progress=progress_data.get("progress", 0.0),
            progress_percentage=int(progress_data.get("progress", 0.0) * 100),
            status=general_status,  # General Celery status
            task_status=progress_data.get("status", "unknown"),  # Specific task stage
            details=progress_data.get("details", ""),
            updated_at=progress_data.get("updated_at", ""),
            webhook_url=progress_data.get("webhook_url")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while retrieving progress")

@app.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    Cancel a running task

    Attempts to cancel/revoke a Celery task that is currently pending or running.
    Once cancelled, the task cannot be resumed and will show status as 'revoked'.

    Returns:
        Dictionary with cancellation status and details
    """
    try:
        # Check if task exists first
        task_result = AsyncResult(task_id, app=celery_app)

        if task_result.state in ["SUCCESS", "FAILURE"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task {task_id}: Task already completed with status {task_result.state}"
            )

        if task_result.state == "REVOKED":
            return {
                "task_id": task_id,
                "status": "already_cancelled",
                "message": "Task was already cancelled"
            }

        # Revoke the task with terminate=True to kill worker process if running
        celery_app.control.revoke(task_id, terminate=True)

        # Update progress tracker to mark as cancelled
        current_progress_data = progress_tracker.get_progress(task_id)
        current_progress = current_progress_data.get("progress", 0.0) if current_progress_data else 0.0
        webhook_url = current_progress_data.get("webhook_url") if current_progress_data else None

        progress_tracker.update_progress(
            task_id,
            current_progress,
            "cancelled",
            "Task was cancelled by user request"
        )

        # Send webhook notification for task cancellation
        if webhook_url:
            try:
                response = httpx.post(webhook_url, json={
                    "status": "cancelled",
                    "task_id": task_id,
                    "message": "Task was cancelled by user request",
                    "progress": current_progress,
                    "progress_percentage": int(current_progress * 100),
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"[{task_id}] Cancellation webhook sent to {webhook_url}")
            except Exception as e:
                logger.error(f"[{task_id}] Error sending cancellation webhook: {str(e)}")

        logger.info(f"Task {task_id} cancelled successfully")

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancellation requested successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

# @app.post("/task/{task_id}/webhook-progress")
# async def set_progress_webhook(task_id: str, webhook_url: str = Form(...)):
#     """
#     Enable progress webhook notifications for a specific task.
#     
#     Args:
#         task_id: The task identifier
#         webhook_url: URL to receive progress webhook notifications
#         
#     The webhook will receive progress updates when significant progress is made.
#     Progress webhooks are throttled to avoid excessive calls.
#     """
#     try:
#         # Validate that task exists
#         task_result = AsyncResult(task_id, app=celery_app)
#         if task_result.state == "PENDING":
#             # Task might not exist, but we'll allow webhook setup anyway
#             logger.warning(f"Setting webhook for potentially non-existent task {task_id}")
#         
#         # Set webhook URL in progress tracker
#         progress_tracker.set_webhook_url(task_id, webhook_url)
#         
#         logger.info(f"Progress webhook configured for task {task_id}: {webhook_url}")
#         
#         # Send a test webhook to confirm the URL is working
#         test_sent = False
#         try:
#             test_result = webhook_manager.send_webhook_sync(
#                 webhook_url,
#                 {
#                     "status": "webhook_configured",
#                     "task_id": task_id,
#                     "message": "Webhook URL configured successfully. You will receive progress updates for this task.",
#                     "timestamp": datetime.now().isoformat(),
#                     "test": True
#                 }
#             )
#             test_sent = test_result
#             if test_result:
#                 logger.info(f"Test webhook sent successfully to {webhook_url}")
#             else:
#                 logger.warning(f"Test webhook failed to send to {webhook_url}")
#         except Exception as webhook_error:
#             logger.error(f"Failed to send test webhook: {str(webhook_error)}")
#         
#         return {
#             "message": f"Progress webhook configured successfully for task {task_id}",
#             "webhook_url": webhook_url,
#             "task_id": task_id,
#             "test_webhook_sent": test_sent,
#             "note": "A test webhook should have been sent to confirm the URL is reachable"
#         }
#         
#     except Exception as e:
#         logger.error(f"Error setting progress webhook for task {task_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error while setting webhook")

# @app.post("/task/{task_id}/webhook-progress/test")
# async def test_progress_webhook(task_id: str):
#     """
#     Send a test progress webhook immediately for debugging purposes.
#     
#     This endpoint will force send the current progress state via webhook,
#     regardless of throttling rules. Useful for testing webhook connectivity.
#     """
#     try:
#         progress_data = progress_tracker.get_progress(task_id)
#         
#         if not progress_data:
#             raise HTTPException(
#                 status_code=404, 
#                 detail=f"No progress information found for task {task_id}"
#             )
#         
#         webhook_url = progress_data.get("webhook_url")
#         if not webhook_url:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"No webhook URL configured for task {task_id}. Use POST /task/{task_id}/webhook-progress first."
#             )
#         
#         # Force send current progress webhook
#         webhook_sent = webhook_manager.send_progress_webhook_sync(task_id, force=True)
#         
#         if webhook_sent:
#             logger.info(f"Test progress webhook sent successfully for task {task_id}")
#             return {
#                 "message": "Test progress webhook sent successfully",
#                 "task_id": task_id,
#                 "webhook_url": webhook_url,
#                 "progress": progress_data.get("progress", 0.0),
#                 "status": progress_data.get("status", "unknown")
#             }
#         else:
#             return {
#                 "message": "Test webhook failed to send",
#                 "task_id": task_id,
#                 "webhook_url": webhook_url,
#                 "error": "Webhook delivery failed - check URL accessibility and logs"
#             }
#         
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error sending test webhook for task {task_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error while sending test webhook")

@app.get("/")
async def root():
    """
    Redirect to API documentation
    """
    logger.info("Root endpoint accessed, redirecting to docs")
    return RedirectResponse(url="/docs")

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request, call_next):
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"[{request_id}] Status code: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"[{request_id}] Request failed: {str(e)}", exc_info=True)
        raise



