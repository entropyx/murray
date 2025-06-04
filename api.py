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
    description="API for experimental design and evaluation using Murray",
    version="1.0.0"
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
    deltas_range: str = Form(...),
    periods_range: str = Form(...),
    webhook_url: str = Form(None)
):
    """
    Submit design analysis task
    """
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"[{request_id}] Submitting design analysis task")
    
    try:
        contents = await file.read()
        
        # Parse parameters
        deltas_range = tuple(map(float, deltas_range.split(',')))
        periods_range = tuple(map(int, periods_range.split(',')))
        excluded_locations = tuple(map(str, excluded_locations.split(',')))
        
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
            webhook_url=webhook_url
        )
        
        logger.info(f"[{request_id}] Task submitted with ID: {task.id}")
        if webhook_url:
            redis_client.set(f"webhook:{task.id}", webhook_url, ex=60*60*24)
            # Notifica PENDING
            try:
                requests.post(webhook_url, json={
                    "task_id": task.id,
                    "status": "PENDING",
                    "results": None,
                    "error": None
                }, timeout=5)
            except Exception as ex:
                logger.error(f"[{task.id}] Error sending webhook: {ex}")
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
    webhook_url: str = Form(None)
):
    """
    Submit evaluation analysis task
    """
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"[{request_id}] Starting evaluation analysis request")
    
    try:
        contents = await file.read()
        treatment_group = list(map(str, treatment_group.split(',')))
        
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
            webhook_url=webhook_url
        )
        
        logger.info(f"[{request_id}] Task submitted with ID: {task.id}")
        if webhook_url:
            redis_client.set(f"webhook:{task.id}", webhook_url, ex=60*60*24)
            # Notifica PENDING inmediatamente
            try:
                requests.post(webhook_url, json={
                    "task_id": task.id,
                    "status": "PENDING",
                    "results": None,
                    "error": None
                }, timeout=5)
            except Exception as ex:
                logger.error(f"[{task.id}] Error sending webhook: {ex}")
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



