from celery_app import celery_app, redis_client
from Murray.main import run_geo_analysis_streamlit_app
from Murray.post_analysis import run_geo_evaluation
from Murray.auxiliary import cleaned_data
import pandas as pd
import numpy as np
import io
import logging
import json
from datetime import datetime
from celery import current_task
import os
import shutil
from typing import Optional, Dict, Any
from pydantic import BaseModel
from celery.signals import task_prerun, task_postrun, task_failure
import requests

logger = logging.getLogger("murray_tasks")

def convert_ndarrays(obj):
    """Convierte objetos numpy a tipos nativos de Python de manera recursiva"""
    # Convert arrays
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # Convert scalars
    elif isinstance(obj, (np.generic,)):
        return obj.item()
    # Convert dictionaries (también convierte keys si son numpy o tuplas)
    elif isinstance(obj, dict):
        return {
            str(k) if isinstance(k, (tuple, np.ndarray, np.generic)) else convert_ndarrays(k): 
            convert_ndarrays(v) 
            for k, v in obj.items()
        }
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
    """Encuentra objetos numpy que no fueron convertidos"""
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

def ensure_temp_dir():
    """Asegura que existe el directorio temporal"""
    temp_dir = "temp_updates"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def save_temp_data(task_id: str, data: pd.DataFrame, prefix: str = ""):
    """Guarda los datos en un archivo temporal"""
    temp_dir = ensure_temp_dir()
    filename = f"{prefix}_{task_id}.csv" if prefix else f"{task_id}.csv"
    filepath = os.path.join(temp_dir, filename)
    
    try:
        with open(filepath, 'w') as f:
            data.to_csv(f, index=False)
        logger.info(f"[{task_id}] Saved temporary data to {filepath}")
    except Exception as e:
        logger.error(f"[{task_id}] Error saving temporary data: {str(e)}", exc_info=True)

def cleanup_temp_data(task_id: str, prefix: str = ""):
    """Elimina los archivos temporales después de una ejecución exitosa"""
    temp_dir = ensure_temp_dir()
    filename = f"{prefix}_{task_id}.json" if prefix else f"{task_id}.json"
    filepath = os.path.join(temp_dir, filename)
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"[{task_id}] Cleaned up temporary data from {filepath}")
    except Exception as e:
        logger.error(f"[{task_id}] Error cleaning up temporary data: {str(e)}", exc_info=True)

@celery_app.task(name="analyze_design_task", track_started=True)
def analyze_design_task(
    file_content: bytes,
    date_column: str,
    location_column: str,
    target_column: str,
    excluded_locations: tuple,
    maximum_treatment_percentage: float,
    significance_level: float,
    deltas_range: tuple,
    periods_range: tuple,
    webhook_url: str = None
):
    task_id = current_task.request.id
    logger.info(f"[{task_id}] Starting design analysis task")
    
    try:
        # Read the CSV file
        df = pd.read_csv(io.BytesIO(file_content))
        logger.info(f"[{task_id}] CSV file read successfully. Shape: {df.shape}")
        
        save_temp_data(task_id, df, "data_design_input")
        
        # Clean data
        data = cleaned_data(df, col_target=target_column, col_locations=location_column, col_dates=date_column)
        logger.info(f"[{task_id}] Data cleaned successfully")
        
        # Run analysis
        logger.info(f"[{task_id}] Starting geo analysis")
        results = run_geo_analysis_streamlit_app(
            data=data,
            excluded_locations=excluded_locations,
            maximum_treatment_percentage=maximum_treatment_percentage,
            significance_level=significance_level,
            deltas_range=deltas_range,
            periods_range=periods_range
        )
        logger.info(f"[{task_id}] Geo analysis completed")
        
        # Converted results to native Python types
        serializable_results = convert_ndarrays(results)
        
        # Verify if there are numpy objects that were not converted
        numpy_locations = find_numpy_objects(serializable_results)
        if numpy_locations:
            logger.warning(f"[{task_id}] Numpy objects found in results: {numpy_locations}")
        else:
            logger.info(f"[{task_id}] All numpy objects converted successfully")
            # Clean up temp files only if everything went well
            cleanup_temp_data(task_id, "design_input")
            cleanup_temp_data(task_id, "design_results")
        
        return serializable_results
        
    except Exception as e:
        logger.error(f"[{task_id}] Error in design analysis task: {str(e)}", exc_info=True)
        raise

@celery_app.task(name="analyze_evaluation_task", track_started=True)
def analyze_evaluation_task(
    file_content: bytes,
    date_column: str,
    location_column: str,
    target_column: str,
    treatment_start_date: str,
    treatment_end_date: str,
    treatment_group: list,
    spend: float,
    mmm_option: str,
    webhook_url: str = None
):
    task_id = current_task.request.id
    logger.info(f"[{task_id}] Starting evaluation analysis task")
    
    # Agregar el registro del webhook URL
    if webhook_url:
        redis_client.set(f"webhook:{task_id}", webhook_url)
    
    try:
        df = pd.read_csv(io.BytesIO(file_content))
        logger.info(f"[{task_id}] CSV file read successfully. Shape: {df.shape}")
        
        save_temp_data(task_id, df, "data_evaluation_input")
        
        
        df = cleaned_data(df, col_target=target_column, col_locations=location_column, col_dates=date_column)
        logger.info(f"[{task_id}] Data cleaned successfully")
        
        
        treatment_start_date = pd.to_datetime(treatment_start_date, dayfirst=True)
        treatment_end_date = pd.to_datetime(treatment_end_date, dayfirst=True)
        
        logger.info(f"[{task_id}] Starting geo evaluation")
        results = run_geo_evaluation(
            data_input=df,
            start_treatment=treatment_start_date,
            end_treatment=treatment_end_date,
            treatment_group=treatment_group,
            spend=spend,
        )
        logger.info(f"[{task_id}] Geo evaluation completed")
        
        # Converted results to native Python types
        serializable_results = convert_ndarrays(results)
        
        
        numpy_locations = find_numpy_objects(serializable_results)
        if numpy_locations:
            logger.warning(f"[{task_id}] Numpy objects found in results: {numpy_locations}")
        else:
            logger.info(f"[{task_id}] All numpy objects converted successfully")
            # Clean up temp files only if everything went well
            cleanup_temp_data(task_id, "evaluation_input")
            cleanup_temp_data(task_id, "evaluation_results")
        
        return serializable_results
        
    except Exception as e:
        logger.error(f"[{task_id}] Error in evaluation analysis task: {str(e)}", exc_info=True)
        raise 

class TaskResponse(BaseModel):
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    results: Optional[Dict[str, Any]] = None  

def notify_webhook(task_id, status, results=None, error=None):
    webhook_url = redis_client.get(f"webhook:{task_id}")
    if webhook_url:
        try:
            payload = {
                "task_id": task_id,
                "status": status,
                "results": results,
                "error": error,
            }
            requests.post(webhook_url.decode(), json=payload, timeout=5)
        except Exception as ex:
            logger.error(f"[{task_id}] Error sending webhook: {ex}")

@task_prerun.connect
def task_started_handler(sender=None, task_id=None, **kwargs):
    notify_webhook(task_id, "STARTED")

@task_postrun.connect
def task_completed_handler(sender=None, task_id=None, retval=None, state=None, **kwargs):
    if state == "SUCCESS":
        notify_webhook(task_id, "SUCCESS", results=retval)
    elif state == "FAILURE":
        notify_webhook(task_id, "FAILURE", error=str(retval))

@task_failure.connect
def task_failed_handler(sender=None, task_id=None, exception=None, **kwargs):
    notify_webhook(task_id, "FAILURE", error=str(exception))