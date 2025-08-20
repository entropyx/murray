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
    file: UploadFile = File(...),
    date_column: str = Form(...),
    location_column: str = Form(...),
    target_column: str = Form(...),
    excluded_locations: str = Form(...),
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
        excluded_locations = tuple(map(str, excluded_locations.split(',')))
        
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
                results={"message": "Task was revoked"}
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



