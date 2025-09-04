from celery_app import celery_app, redis_client
from Murray.main import run_geo_analysis_streamlit_app
from Murray.post_analysis import run_geo_evaluation
from Murray.auxiliary import cleaned_data
import pandas as pd
import numpy as np
import io
import logging
import json
from datetime import datetime, timezone
from celery import current_task
import os
import shutil
from typing import Optional, Dict, Any
from pydantic import BaseModel
from celery.signals import task_prerun, task_postrun, task_failure
import requests
import httpx
import asyncio
import redis

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
    
    # Initialize progress tracking
    webhook_url = webhook.get("url") if webhook else None
    progress_updater = TaskProgressUpdater(task_id, webhook_url)
    
    # Define analysis stages for progress tracking
    analysis_stages = [
        "Data Loading & Processing",
        "Market Correlation Analysis", 
        "Treatment Group Optimization",
        "Sensitivity Analysis",
        "Results Finalization"
    ]
    progress_updater.set_stages(analysis_stages, 0)
    
    # Log analysis mode
    analysis_mode = "multicell" if global_optimization and multicell_config else "single-cell"
    logger.info(f"[{task_id}] Starting {analysis_mode} analysis")
    if multicell_config:
        logger.info(f"[{task_id}] Multicell config: {multicell_config}")
    
    # Initial progress update
    progress_updater.update_stage_progress(
        0.0, 
        f"Starting {analysis_mode} analysis with {len(analysis_stages)} stages"
    )
    
    # Send traditional webhook for backward compatibility
    if webhook:
        try:
            httpx.post(webhook["url"], json={
                "status": "started",
                "task_id": task_id,
                "message": f"Design analysis task started ({analysis_mode} mode)",
                "analysis_mode": analysis_mode,
                "multicell_config": multicell_config,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[{task_id}] Error sending start webhook: {str(e)}")

    try:
        # Stage 1: Data Loading & Processing
        progress_updater.update_stage_progress(0.2, "Loading CSV data...")
        df = pd.read_csv(io.BytesIO(file_content))
        logger.info(f"[{task_id}] CSV file read successfully. Shape: {df.shape}")

        progress_updater.update_stage_progress(0.5, "Saving temporary data...")
        save_temp_data(task_id, df, "data_design_input")

        progress_updater.update_stage_progress(0.8, "Cleaning and validating data...")
        data = cleaned_data(df, col_target=target_column, col_locations=location_column, col_dates=date_column)
        logger.info(f"[{task_id}] Data cleaned successfully")
        
        progress_updater.update_stage_progress(1.0, f"Data processing completed. Shape: {data.shape}")
        progress_updater.advance_stage("Starting geo analysis pipeline")

        # Stage 2-4: Main Analysis (with custom progress callbacks)
        logger.info(f"[{task_id}] Starting geo analysis ({analysis_mode} mode)")
        
        # Create progress callback objects that mimic Streamlit progress bars
        class ProgressCallback:
            def __init__(self, progress_updater, analysis_stages):
                self.progress_updater = progress_updater
                self.analysis_stages = analysis_stages
            
            def progress(self, value):
                # Map the progress to the current stage range (don't let it go to 100% until final stage)
                current_stage = getattr(self.progress_updater, 'current_stage', 'Treatment Group Optimization')
                
                # Fix: If we're in sensitivity analysis context, ensure stage_idx is 3
                if 'Sensitivity' in current_stage and getattr(self.progress_updater, 'current_stage_index', 0) != 3:
                    self.progress_updater.current_stage_index = 3
                    self.progress_updater.current_stage = "Sensitivity Analysis"
                
                # For BetterGroups (stage 2), cap at 100% within stage (not global 100%)
                stage_progress = min(value, 1.0)
                
                self.progress_updater.update_stage_progress(stage_progress, f"{current_stage}: {int(stage_progress*100)}% complete")
        
        class StatusCallback:
            def __init__(self, progress_updater, analysis_stages):
                self.progress_updater = progress_updater
                self.analysis_stages = analysis_stages
                self.last_message = ""
            
            def text(self, message):
                # Always log the message for debugging
                logger.debug(f"[{task_id}] Status update: {message}")
                
                # Controlled stage detection - only advance forward, never backwards
                logger.debug(f"[{task_id}] Status update: {message}")
                message_lower = message.lower()
                
                current_stage_idx = getattr(self.progress_updater, 'current_stage_index', 0)
                new_stage_idx = current_stage_idx
                
                # Only detect stage advancement, never go backwards
                if any(word in message_lower for word in ['sensitivity', 'mde', 'power']) and current_stage_idx <= 2:
                    new_stage_idx = 3  # Sensitivity Analysis
                
                # Only advance if moving forward
                if new_stage_idx > current_stage_idx:
                    self.progress_updater.current_stage_index = new_stage_idx
                    self.progress_updater.current_stage = self.analysis_stages[new_stage_idx]
                    # Reset stage progress to 0 when advancing to prevent jumps
                    current_progress = 0.0
                else:
                    # Update with current progress and message (always update for timestamp refresh)
                    current_progress = getattr(self.progress_updater, 'stage_progress', 0.0)
                
                # Force update if message changed significantly
                force_update = message != self.last_message
                self.last_message = message
                
                self.progress_updater.update_stage_progress(current_progress, message)
                
                # Progress webhooks disabled - use /task/{id}/progress endpoint instead
        
        # Create callback objects for BetterGroups
        progress_callback = ProgressCallback(progress_updater, analysis_stages)
        status_callback = StatusCallback(progress_updater, analysis_stages)
        
        # Ensure we're in the right stage for group optimization
        progress_updater.current_stage_index = 2
        progress_updater.current_stage = analysis_stages[2]
        
        # Manual stage advancement after group optimization
        def advance_to_sensitivity():
            progress_updater.current_stage_index = 3
            progress_updater.current_stage = analysis_stages[3]
            progress_updater.update_stage_progress(0.0, "Starting sensitivity analysis")
        
        # Pass advancement function to callbacks
        status_callback.advance_to_sensitivity = advance_to_sensitivity
        
        results = run_geo_analysis_streamlit_app(
            data=data,
            excluded_locations=excluded_locations,
            maximum_treatment_percentage=maximum_treatment_percentage,
            significance_level=significance_level,
            deltas_range=deltas_range,
            periods_range=periods_range,
            multicell_config=multicell_config,
            global_optimization=global_optimization,
            progress_bar_1=progress_callback,
            status_text_1=status_callback,
            progress_bar_2=progress_callback,  # Use same callback for sensitivity analysis
            status_text_2=status_callback
        )
        logger.info(f"[{task_id}] Geo analysis completed ({analysis_mode} mode)")
        
        # Move to final stage
        progress_updater.current_stage_index = 4
        progress_updater.current_stage = analysis_stages[4]

        # Stage 5: Results Finalization
        progress_updater.update_stage_progress(0.2, "Converting numpy arrays to JSON-serializable format...")
        serializable_results = convert_ndarrays(results)
        numpy_locations = find_numpy_objects(serializable_results)

        progress_updater.update_stage_progress(0.5, "Validating result serialization...")
        if numpy_locations:
            logger.warning(f"[{task_id}] Numpy objects found in results: {numpy_locations}")
        else:
            logger.info(f"[{task_id}] All numpy objects converted successfully")
            cleanup_temp_data(task_id, "design_input")
            cleanup_temp_data(task_id, "design_results")
        
        progress_updater.update_stage_progress(0.8, "Preparing final results structure...")
        # Add metadata about analysis mode to results
        final_results = {
            "analysis_mode": analysis_mode,
            "multicell_config": multicell_config,
            "global_optimization": global_optimization,
            "results": serializable_results
        }

        progress_updater.update_stage_progress(1.0, "Analysis completed successfully!")
        progress_updater.complete("Design analysis completed with all stages successful")

        # Send traditional webhook for completion
        if webhook:
            try:
                httpx.post(webhook["url"], json={
                    "status": "completed",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "result": final_results
                })
            except Exception as e:
                logger.error(f"[{task_id}] Error sending traditional success webhook: {str(e)}")

        return final_results

    except Exception as e:
        logger.error(f"[{task_id}] Error in design analysis task: {str(e)}", exc_info=True)
        
        # Send traditional failure webhook
        if webhook:
            try:
                httpx.post(webhook["url"], json={
                    "status": "failed",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                })
            except Exception as webhook_error:
                logger.error(f"[{task_id}] Error sending traditional failure webhook: {str(webhook_error)}")
        
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
    
    # Initialize progress tracking
    webhook_url = webhook.get("url") if webhook else None
    progress_updater = TaskProgressUpdater(task_id, webhook_url)
    
    # Define evaluation stages for progress tracking
    evaluation_stages = [
        "Data Loading & Processing",
        "Date Processing & Validation",
        "Geo Evaluation Analysis",
        "Results Finalization"
    ]
    progress_updater.set_stages(evaluation_stages, 0)
    
    # Initial progress update
    progress_updater.update_stage_progress(0.0, "Starting evaluation analysis")
    
    # Send traditional webhook for backward compatibility
    if webhook:
        try:
            httpx.post(webhook["url"], json={
                "status": "started",
                "task_id": task_id,
                "message": "Evaluation analysis task started",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[{task_id}] Error sending start webhook: {str(e)}")

    try:
        # Stage 1: Data Loading & Processing
        progress_updater.update_stage_progress(0.2, "Loading CSV data...")
        df = pd.read_csv(io.BytesIO(file_content))
        logger.info(f"[{task_id}] CSV file read successfully. Shape: {df.shape}")

        progress_updater.update_stage_progress(0.5, "Saving temporary data...")
        save_temp_data(task_id, df, "data_evaluation_input")

        progress_updater.update_stage_progress(0.8, "Cleaning and validating data...")
        df = cleaned_data(df, col_target=target_column, col_locations=location_column, col_dates=date_column)
        logger.info(f"[{task_id}] Data cleaned successfully")
        
        progress_updater.update_stage_progress(1.0, f"Data processing completed. Shape: {df.shape}")
        progress_updater.advance_stage("Processing treatment dates")

        # Stage 2: Date Processing & Validation
        progress_updater.update_stage_progress(0.3, "Converting treatment start date...")
        treatment_start_date = pd.to_datetime(treatment_start_date, dayfirst=True)
        
        progress_updater.update_stage_progress(0.7, "Converting treatment end date...")
        treatment_end_date = pd.to_datetime(treatment_end_date, dayfirst=True)
        
        progress_updater.update_stage_progress(1.0, f"Date processing completed: {treatment_start_date} to {treatment_end_date}")
        progress_updater.advance_stage("Starting geo evaluation analysis")

        # Stage 3: Geo Evaluation Analysis
        logger.info(f"[{task_id}] Starting geo evaluation")
        progress_updater.update_stage_progress(0.1, f"Analyzing treatment group: {treatment_group}")
        
        results = run_geo_evaluation(
            data_input=df,
            start_treatment=treatment_start_date,
            end_treatment=treatment_end_date,
            treatment_group=treatment_group,
            spend=spend,
        )
        logger.info(f"[{task_id}] Geo evaluation completed")
        
        progress_updater.update_stage_progress(1.0, "Geo evaluation analysis completed")
        progress_updater.advance_stage("Finalizing results")

        # Stage 4: Results Finalization
        progress_updater.update_stage_progress(0.3, "Converting numpy arrays to JSON-serializable format...")
        serializable_results = convert_ndarrays(results)
        numpy_locations = find_numpy_objects(serializable_results)

        progress_updater.update_stage_progress(0.6, "Validating result serialization...")
        if numpy_locations:
            logger.warning(f"[{task_id}] Numpy objects found in results: {numpy_locations}")
        else:
            logger.info(f"[{task_id}] All numpy objects converted successfully")
            cleanup_temp_data(task_id, "evaluation_input")
            cleanup_temp_data(task_id, "evaluation_results")

        progress_updater.update_stage_progress(1.0, "Evaluation analysis completed successfully!")
        progress_updater.complete("Evaluation analysis completed with all stages successful")

        # Send traditional webhook for completion
        if webhook:
            try:
                httpx.post(webhook["url"], json={
                    "status": "completed",
                    "task_id": task_id,
                    "result": serializable_results,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"[{task_id}] Error sending traditional success webhook: {str(e)}")

        return serializable_results

    except Exception as e:
        logger.error(f"[{task_id}] Error in evaluation analysis task: {str(e)}", exc_info=True)
        
        # Send traditional failure webhook
        if webhook:
            try:
                httpx.post(webhook["url"], json={
                    "status": "failed",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                })
            except Exception as webhook_error:
                logger.error(f"[{task_id}] Error sending traditional failure webhook: {str(webhook_error)}")
        
        raise

class TaskResponse(BaseModel):
    task_id: str
    status: str
    results: Optional[Dict[str, Any]] = None


# ============================================================================
# PROGRESS TRACKING SYSTEM (previously progress_tracker.py)
# ============================================================================

class ProgressTracker:
    """
    Redis-based progress tracking system for Murray analysis tasks.
    
    Stores and manages real-time progress information including:
    - Progress percentage (0.0 to 1.0)
    - Current operation status
    - Detailed progress information
    - Webhook configuration
    - Timestamps
    """
    
    def __init__(self, redis_client: redis.Redis = None):
        """
        Initialize progress tracker with Redis client.
        
        Args:
            redis_client: Redis client instance. If None, creates a new one from env vars
        """
        if redis_client:
            self.redis = redis_client
        else:
            # Create Redis client from environment variables
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_db = os.getenv("REDIS_DB", "0")
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
            self.redis = redis.Redis.from_url(redis_url)
        self.key_prefix = "murray:progress:"
        self.ttl = 86400  # 24 hours TTL for progress data
        
    def _get_key(self, task_id: str) -> str:
        """Generate Redis key for task progress."""
        return f"{self.key_prefix}{task_id}"
    
    def update_progress(
        self, 
        task_id: str, 
        progress: float, 
        status: str, 
        details: str = "",
        webhook_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update progress information for a task.
        
        Args:
            task_id: Unique task identifier
            progress: Progress value between 0.0 and 1.0
            status: Current operation status description
            details: Additional detailed information
            webhook_url: Optional webhook URL for notifications
            metadata: Additional metadata dictionary
        """
        try:
            # Clamp progress to valid range
            progress = max(0.0, min(1.0, float(progress)))
            
            # Always generate a fresh timestamp
            current_timestamp = datetime.now(timezone.utc).isoformat()
            
            progress_data = {
                "progress": progress,
                "status": status,
                "details": details,
                "updated_at": current_timestamp,
                "webhook_url": webhook_url,
                "last_webhook_sent": 0.0,
                "metadata": metadata or {}
            }
            
            # Try to preserve last_webhook_sent and webhook_url from existing data
            existing_data = self.get_progress(task_id)
            if existing_data:
                progress_data["last_webhook_sent"] = existing_data.get("last_webhook_sent", 0.0)
                if not webhook_url and existing_data.get("webhook_url"):
                    progress_data["webhook_url"] = existing_data["webhook_url"]
            
            key = self._get_key(task_id)
            self.redis.setex(key, self.ttl, json.dumps(progress_data))
            
            logger.debug(f"[{task_id}] Progress updated: {progress:.1%} - {status} at {current_timestamp}")
            
        except Exception as e:
            logger.error(f"[{task_id}] Failed to update progress: {str(e)}")
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current progress information for a task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            Dictionary with progress information or None if not found
        """
        try:
            key = self._get_key(task_id)
            data = self.redis.get(key)
            
            if data:
                return json.loads(data.decode('utf-8'))
            return None
            
        except Exception as e:
            logger.error(f"[{task_id}] Failed to get progress: {str(e)}")
            return None
    
    def should_send_webhook(self, task_id: str, threshold: float = 0.05) -> bool:
        """
        Determine if webhook should be sent based on progress threshold.
        
        Args:
            task_id: Unique task identifier
            threshold: Minimum progress change to trigger webhook
            
        Returns:
            True if webhook should be sent, False otherwise
        """
        try:
            progress_data = self.get_progress(task_id)
            if not progress_data or not progress_data.get("webhook_url"):
                return False
            
            current_progress = progress_data.get("progress", 0.0)
            last_sent = progress_data.get("last_webhook_sent", 0.0)
            
            # Send webhook if progress increased by threshold or reached 100%
            return (current_progress - last_sent >= threshold) or current_progress >= 1.0
            
        except Exception as e:
            logger.error(f"[{task_id}] Failed to check webhook threshold: {str(e)}")
            return False
    
    def mark_webhook_sent(self, task_id: str) -> None:
        """
        Mark that webhook has been sent for current progress level.
        
        Args:
            task_id: Unique task identifier
        """
        try:
            progress_data = self.get_progress(task_id)
            if progress_data:
                progress_data["last_webhook_sent"] = progress_data.get("progress", 0.0)
                key = self._get_key(task_id)
                self.redis.setex(key, self.ttl, json.dumps(progress_data))
                
        except Exception as e:
            logger.error(f"[{task_id}] Failed to mark webhook sent: {str(e)}")
    
    def set_webhook_url(self, task_id: str, webhook_url: str) -> None:
        """
        Set or update webhook URL for a task.
        
        Args:
            task_id: Unique task identifier
            webhook_url: Webhook URL for progress notifications
        """
        try:
            progress_data = self.get_progress(task_id)
            if progress_data:
                progress_data["webhook_url"] = webhook_url
                key = self._get_key(task_id)
                self.redis.setex(key, self.ttl, json.dumps(progress_data))
            else:
                # Create initial progress entry with webhook URL
                self.update_progress(task_id, 0.0, "initialized", webhook_url=webhook_url)
                
        except Exception as e:
            logger.error(f"[{task_id}] Failed to set webhook URL: {str(e)}")
    
    def delete_progress(self, task_id: str) -> None:
        """
        Delete progress information for completed/failed tasks.
        
        Args:
            task_id: Unique task identifier
        """
        try:
            key = self._get_key(task_id)
            self.redis.delete(key)
            logger.debug(f"[{task_id}] Progress data deleted")
            
        except Exception as e:
            logger.error(f"[{task_id}] Failed to delete progress: {str(e)}")
    
    def get_all_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get progress information for all active tasks.
        
        Returns:
            Dictionary mapping task_id to progress information
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis.keys(pattern)
            
            result = {}
            for key in keys:
                task_id = key.decode('utf-8').replace(self.key_prefix, '')
                progress_data = self.get_progress(task_id)
                if progress_data:
                    result[task_id] = progress_data
                    
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all active tasks: {str(e)}")
            return {}


class TaskProgressUpdater:
    """
    Convenience class for updating progress within task execution.
    
    Provides simplified interface for progress updates with automatic
    task_id management and common progress patterns.
    """
    
    def __init__(self, task_id: str, webhook_url: Optional[str] = None):
        """
        Initialize progress updater for specific task.
        
        Args:
            task_id: Unique task identifier
            webhook_url: Optional webhook URL for notifications
        """
        self.task_id = task_id
        self.tracker = ProgressTracker()
        self.current_stage = ""
        self.total_stages = 1
        self.stage_progress = 0.0
        
        if webhook_url:
            self.tracker.set_webhook_url(task_id, webhook_url)
    
    def set_stages(self, stages: list, current_stage_index: int = 0):
        """
        Define analysis stages for automatic progress calculation.
        
        Args:
            stages: List of stage names
            current_stage_index: Index of current stage (0-based)
        """
        self.stages = stages
        self.total_stages = len(stages)
        self.current_stage_index = current_stage_index
        self.current_stage = stages[current_stage_index] if stages else ""
    
    def update_stage_progress(self, progress: float, details: str = ""):
        """
        Update progress within current stage with continuous progression.
        
        Args:
            progress: Progress within current stage (0.0 to 1.0)
            details: Additional progress details
        """
        # Get current overall progress to avoid backwards movement
        current_data = self.tracker.get_progress(self.task_id)
        current_overall = current_data.get("progress", 0.0) if current_data else 0.0
        
        
        if hasattr(self, 'stages') and self.total_stages > 0:
            # Custom stage weights for 5 stages:
            # 0: Data Loading (0-5%)
            # 1: Market Correlation (5-10%) 
            # 2: Treatment Groups (10-30%)
            # 3: Sensitivity Analysis (30-95%)
            # 4: Results Finalization (95-100%)
            stage_weights = [0.05, 0.05, 0.20, 0.65, 0.05]  
            stage_starts = [0.0, 0.05, 0.10, 0.30, 0.95]
            
            if self.current_stage_index < len(stage_weights):
                stage_weight = stage_weights[self.current_stage_index]
                stage_start = stage_starts[self.current_stage_index]
                new_overall_progress = stage_start + (progress * stage_weight)
            else:
                # Fallback for any unexpected stage index
                new_overall_progress = 1.0

            if (self.current_stage_index >= 2 and hasattr(self, 'current_stage') and 
                ('Treatment' in str(getattr(self, 'current_stage', '')) or 'Sensitivity' in str(getattr(self, 'current_stage', ''))) and 
                new_overall_progress < current_overall):
                # Allow the calculated progress for treatment groups or sensitivity analysis
                overall_progress = new_overall_progress
            else:
                # Normal forward-only protection
                overall_progress = max(current_overall, new_overall_progress)
        else:
            overall_progress = max(current_overall, progress)
        
        
        self.stage_progress = progress
        
        # Always update progress (this updates timestamp)
        self.tracker.update_progress(
            self.task_id,
            overall_progress,
            self.current_stage,
            details
        )
        
        # Progress webhooks disabled - use /task/{id}/progress endpoint instead
    
    def advance_stage(self, details: str = ""):
        """
        Move to next analysis stage.
        
        Args:
            details: Details about stage completion
        """
        if hasattr(self, 'stages') and self.current_stage_index < len(self.stages) - 1:
            self.current_stage_index += 1
            self.current_stage = self.stages[self.current_stage_index]
            self.stage_progress = 0.0
            
            # Update progress to start of new stage
            stage_weight = 1.0 / self.total_stages
            overall_progress = self.current_stage_index * stage_weight
            
            self.tracker.update_progress(
                self.task_id,
                overall_progress,
                self.current_stage,
                details
            )
    
    def complete(self, details: str = "Analysis completed successfully"):
        """
        Mark task as completed.
        
        Args:
            details: Completion details
        """
        self.tracker.update_progress(
            self.task_id,
            1.0,
            "completed",
            details
        )


# ============================================================================
# WEBHOOK MANAGEMENT SYSTEM 
# ============================================================================

class WebhookManager:
    """
    Manages webhook notifications for task progress updates.
    
    Features:
    - Asynchronous webhook delivery
    - Throttling to prevent spam
    - Retry logic with exponential backoff
    - Webhook validation and formatting
    """
    
    def __init__(self, default_timeout: float = 30.0):
        """
        Initialize webhook manager.
        
        Args:
            default_timeout: Default timeout for webhook requests in seconds
        """
        self.default_timeout = default_timeout
        self.max_retries = 3
        self.base_retry_delay = 1.0  # seconds
        
    def format_progress_webhook(
        self, 
        task_id: str, 
        progress_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format progress data for webhook delivery.
        
        Args:
            task_id: Task identifier
            progress_data: Progress information from tracker
            
        Returns:
            Formatted webhook payload
        """
        return {
            "status": "progress",
            "task_id": task_id,
            "progress": progress_data.get("progress", 0.0),
            "progress_percentage": int(progress_data.get("progress", 0.0) * 100),
            "current_operation": progress_data.get("status", ""),
            "details": progress_data.get("details", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": progress_data.get("metadata", {})
        }
    
    async def send_webhook_async(
        self, 
        webhook_url: str, 
        payload: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> bool:
        """
        Send webhook notification asynchronously with retry logic.
        
        Args:
            webhook_url: Target webhook URL
            payload: JSON payload to send
            timeout: Request timeout in seconds
            
        Returns:
            True if webhook was sent successfully, False otherwise
        """
        timeout = timeout or self.default_timeout
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Webhook attempt {attempt + 1}/{self.max_retries} to {webhook_url}")
                async with httpx.AsyncClient(timeout=timeout) as client:
                    logger.debug(f"Sending POST request to {webhook_url}")
                    response = await client.post(
                        webhook_url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "Murray-API/1.0"
                        }
                    )
                    
                    logger.debug(f"Received response with status {response.status_code}")
                    if response.status_code < 400:
                        logger.info(f"Webhook sent successfully to {webhook_url} (status: {response.status_code})")
                        return True
                    else:
                        logger.warning(f"Webhook failed with status {response.status_code}: {response.text[:200]}")
                        
            except httpx.TimeoutException as e:
                logger.warning(f"Webhook timeout for {webhook_url} (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
            except httpx.ConnectError as e:
                logger.warning(f"Webhook connection error for {webhook_url} (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
            except ImportError as e:
                logger.error(f"Missing httpx dependency: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Webhook error for {webhook_url}: {str(e)} (attempt {attempt + 1}/{self.max_retries})")
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")
            
            # Exponential backoff for retries
            if attempt < self.max_retries - 1:
                delay = self.base_retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        
        logger.error(f"Failed to send webhook to {webhook_url} after {self.max_retries} attempts")
        return False
    
    def send_webhook_sync(
        self, 
        webhook_url: str, 
        payload: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> bool:
        """
        Send webhook notification synchronously (blocking).
        
        Args:
            webhook_url: Target webhook URL
            payload: JSON payload to send
            timeout: Request timeout in seconds
            
        Returns:
            True if webhook was sent successfully, False otherwise
        """
        try:
            logger.info(f"Attempting to send webhook to {webhook_url}")
            logger.debug(f"Webhook payload: {payload}")
            
            # Run async function in sync context
            result = asyncio.run(self.send_webhook_async(webhook_url, payload, timeout))
            logger.info(f"Webhook send result: {result}")
            return result
        except Exception as e:
            logger.error(f"Sync webhook send failed: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def send_progress_webhook(self, task_id: str, force: bool = False) -> bool:
        """
        Send progress webhook if conditions are met.
        
        Args:
            task_id: Task identifier
            force: Send webhook regardless of throttling rules
            
        Returns:
            True if webhook was sent, False otherwise
        """
        try:
            progress_data = progress_tracker.get_progress(task_id)
            if not progress_data:
                logger.debug(f"No progress data found for task {task_id}")
                return False
            
            webhook_url = progress_data.get("webhook_url")
            if not webhook_url:
                logger.debug(f"No webhook URL configured for task {task_id}")
                return False
            
            # Check if webhook should be sent (respects throttling)
            if not force and not progress_tracker.should_send_webhook(task_id):
                logger.debug(f"Webhook throttled for task {task_id}")
                return False
            
            # Format and send webhook
            payload = self.format_progress_webhook(task_id, progress_data)
            success = await self.send_webhook_async(webhook_url, payload)
            
            if success:
                progress_tracker.mark_webhook_sent(task_id)
                logger.debug(f"Progress webhook sent for task {task_id}: {payload['progress_percentage']}%")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send progress webhook for task {task_id}: {str(e)}")
            return False
    
    def send_progress_webhook_sync(self, task_id: str, force: bool = False) -> bool:
        """
        Send progress webhook synchronously.
        
        Args:
            task_id: Task identifier
            force: Send webhook regardless of throttling rules
            
        Returns:
            True if webhook was sent, False otherwise
        """
        try:
            result = asyncio.run(self.send_progress_webhook(task_id, force))
            if result:
                logger.info(f"Progress webhook sent successfully for task {task_id}")
            return result
        except Exception as e:
            logger.error(f"Sync progress webhook send failed for task {task_id}: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    async def send_completion_webhook(
        self, 
        task_id: str, 
        status: str, 
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Send task completion webhook.
        
        Args:
            task_id: Task identifier
            status: Final task status ("completed", "failed", etc.)
            result: Task result data (for successful completion)
            error: Error message (for failed completion)
            
        Returns:
            True if webhook was sent, False otherwise
        """
        try:
            progress_data = progress_tracker.get_progress(task_id)
            if not progress_data or not progress_data.get("webhook_url"):
                return False
            
            webhook_url = progress_data["webhook_url"]
            
            # Format completion payload
            payload = {
                "status": status,
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "progress": 1.0 if status == "completed" else progress_data.get("progress", 0.0),
                "progress_percentage": 100 if status == "completed" else int(progress_data.get("progress", 0.0) * 100)
            }
            
            if result:
                payload["result"] = result
            if error:
                payload["error"] = error
            
            success = await self.send_webhook_async(webhook_url, payload)
            
            if success:
                logger.info(f"Completion webhook sent for task {task_id} with status: {status}")
                # Clean up progress data after successful completion notification
                if status in ["completed", "failed", "revoked"]:
                    progress_tracker.delete_progress(task_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send completion webhook for task {task_id}: {str(e)}")
            return False
    
    def send_completion_webhook_sync(
        self, 
        task_id: str, 
        status: str, 
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Send task completion webhook synchronously.
        
        Args:
            task_id: Task identifier
            status: Final task status
            result: Task result data
            error: Error message
            
        Returns:
            True if webhook was sent, False otherwise
        """
        try:
            return asyncio.run(self.send_completion_webhook(task_id, status, result, error))
        except Exception as e:
            logger.error(f"Sync completion webhook send failed for task {task_id}: {str(e)}")
            return False


# Global instances for easy access
progress_tracker = ProgressTracker()
webhook_manager = WebhookManager()
