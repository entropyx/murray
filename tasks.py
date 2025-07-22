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
import httpx

logger = logging.getLogger("murray_tasks")

def convert_ndarrays(obj):
    """Converts numpy objects to native Python types recursively"""
    # Convert arrays
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # Convert scalars
    elif isinstance(obj, (np.generic,)):
        return obj.item()
    # Convert dictionaries (also converts keys if they are numpy or tuples)
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
    """Finds numpy objects that were not converted"""
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
    """Ensures that the temporary directory exists"""
    temp_dir = "temp_updates"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def save_temp_data(task_id: str, data: pd.DataFrame, prefix: str = ""):
    """Saves the data in a temporary file"""
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
    """Deletes the temporary files after a successful execution"""
    temp_dir = ensure_temp_dir()
    filename = f"{prefix}_{task_id}.json" if prefix else f"{task_id}.json"
    filepath = os.path.join(temp_dir, filename)
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"[{task_id}] Cleaned up temporary data from {filepath}")
    except Exception as e:
        logger.error(f"[{task_id}] Error cleaning up temporary data: {str(e)}", exc_info=True)
    
@celery_app.task(name="analyze_design_task", track_started=True, bind=True)
def analyze_design_task(
    self,
    file_content: bytes,
    date_column: str,
    location_column: str,
    target_column: str,
    excluded_locations: tuple,
    maximum_treatment_percentage: float,
    significance_level: float,
    deltas_range: tuple,
    periods_range: tuple,
    multicell_config: dict = None,
    global_optimization: bool = False,
    webhook: dict = None
):
    task_id = self.request.id
    
    # Log analysis mode
    analysis_mode = "multicell" if global_optimization and multicell_config else "single-cell"
    logger.info(f"[{task_id}] Starting {analysis_mode} analysis")
    if multicell_config:
        logger.info(f"[{task_id}] Multicell config: {multicell_config}")
    
    # Notify start
    if webhook:
        try:
            httpx.post(webhook["url"], json={
                "status": "started",
                "job_id": task_id,
                "message": f"Design analysis task started ({analysis_mode} mode)",
                "analysis_mode": analysis_mode,
                "multicell_config": multicell_config,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[{task_id}] Error sending start webhook: {str(e)}")

    try:
        df = pd.read_csv(io.BytesIO(file_content))
        logger.info(f"[{task_id}] CSV file read successfully. Shape: {df.shape}")

        save_temp_data(task_id, df, "data_design_input")

        data = cleaned_data(df, col_target=target_column, col_locations=location_column, col_dates=date_column)
        logger.info(f"[{task_id}] Data cleaned successfully")

        logger.info(f"[{task_id}] Starting geo analysis ({analysis_mode} mode)")
        results = run_geo_analysis_streamlit_app(
            data=data,
            excluded_locations=excluded_locations,
            maximum_treatment_percentage=maximum_treatment_percentage,
            significance_level=significance_level,
            deltas_range=deltas_range,
            periods_range=periods_range,
            multicell_config=multicell_config,
            global_optimization=global_optimization
        )
        logger.info(f"[{task_id}] Geo analysis completed ({analysis_mode} mode)")

        serializable_results = convert_ndarrays(results)
        numpy_locations = find_numpy_objects(serializable_results)

        if numpy_locations:
            logger.warning(f"[{task_id}] Numpy objects found in results: {numpy_locations}")
        else:
            logger.info(f"[{task_id}] All numpy objects converted successfully")
            cleanup_temp_data(task_id, "design_input")
            cleanup_temp_data(task_id, "design_results")
        
        # Add metadata about analysis mode to results
        final_results = {
            "analysis_mode": analysis_mode,
            "multicell_config": multicell_config,
            "global_optimization": global_optimization,
            "results": serializable_results
        }

        # Notify success
        if webhook:
            try:
                httpx.post(webhook["url"], json={
                    "status": "completed",
                    "job_id": task_id,
                    "analysis_mode": analysis_mode,
                    "multicell_config": multicell_config,
                    "result": final_results,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"[{task_id}] Error sending success webhook: {str(e)}")

        return final_results

    except Exception as e:
        logger.error(f"[{task_id}] Error in design analysis task: {str(e)}", exc_info=True)
        
        # Notify failure
        if webhook:
            try:
                httpx.post(webhook["url"], json={
                    "status": "failed",
                    "job_id": task_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as webhook_error:
                logger.error(f"[{task_id}] Error sending failure webhook: {str(webhook_error)}")
        
        raise

@celery_app.task(name="analyze_evaluation_task", track_started=True, bind=True)
def analyze_evaluation_task(
    self,
    file_content: bytes,
    date_column: str,
    location_column: str,
    target_column: str,
    treatment_start_date: str,
    treatment_end_date: str,
    treatment_group: list,
    spend: float,
    mmm_option: str,
    webhook: dict = None
):
    task_id = self.request.id
    
    # Notify start
    if webhook:
        try:
            httpx.post(webhook["url"], json={
                "status": "started",
                "job_id": task_id,
                "message": "Evaluation analysis task started",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[{task_id}] Error sending start webhook: {str(e)}")

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

        serializable_results = convert_ndarrays(results)
        numpy_locations = find_numpy_objects(serializable_results)

        if numpy_locations:
            logger.warning(f"[{task_id}] Numpy objects found in results: {numpy_locations}")
        else:
            logger.info(f"[{task_id}] All numpy objects converted successfully")
            cleanup_temp_data(task_id, "evaluation_input")
            cleanup_temp_data(task_id, "evaluation_results")

        # Notify success
        if webhook:
            try:
                httpx.post(webhook["url"], json={
                    "status": "completed",
                    "job_id": task_id,
                    "result": serializable_results,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"[{task_id}] Error sending success webhook: {str(e)}")

        return serializable_results

    except Exception as e:
        logger.error(f"[{task_id}] Error in evaluation analysis task: {str(e)}", exc_info=True)
        
        # Notify failure
        if webhook:
            try:
                httpx.post(webhook["url"], json={
                    "status": "failed",
                    "job_id": task_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as webhook_error:
                logger.error(f"[{task_id}] Error sending failure webhook: {str(webhook_error)}")
        
        raise

class TaskResponse(BaseModel):
    task_id: str
    status: str
    results: Optional[Dict[str, Any]] = None
