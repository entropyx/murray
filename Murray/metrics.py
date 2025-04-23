import json
import os
from datetime import datetime
import logging
from filelock import FileLock


METRICS_DIR = "traffic_metrics"
METRICS_FILE = os.path.join(METRICS_DIR, "app_metrics.json")
LOCK_FILE = os.path.join(METRICS_DIR, "metrics.lock")

# Configurate logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure the directory exists
os.makedirs(METRICS_DIR, exist_ok=True)

def load_metrics():
    """Load metrics from the file"""
    try:
        with FileLock(LOCK_FILE):
            if os.path.exists(METRICS_FILE):
                with open(METRICS_FILE, 'r') as f:
                    return json.load(f)
    except Exception as e:
        logger.error(f"Error loading metrics: {e}")
    
    return {"history": []}  

def save_metrics(metrics):
    """Save metrics"""
    try:
        with FileLock(LOCK_FILE):
            with open(METRICS_FILE, 'w') as f:
                json.dump(metrics, f, indent=2) 
    except Exception as e:
        logger.error(f"Error saving metrics: {e}")

def update_metrics(section):
    """Update metrics for a specific section"""
    try:
        metrics = load_metrics()
        current_time = datetime.now()
        
        # Create new record
        new_record = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "section": section,
            "date": current_time.strftime("%Y-%m-%d"),
            "day_of_week": current_time.strftime("%A"),
            "hour": current_time.hour
        }
        
        
        metrics["history"].append(new_record)
        
        save_metrics(metrics)
        logger.info(f"New record added: {new_record}")
        return metrics
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")
        return None

def get_daily_stats():
    """Get daily usage statistics"""
    metrics = load_metrics()
    if "history" not in metrics:
        return {}
        
    daily_stats = {}
    for record in metrics["history"]:
        date = record["date"]
        if date not in daily_stats:
            daily_stats[date] = {
                "total": 0,
                "experimental_design": 0,
                "experimental_evaluation": 0
            }
        daily_stats[date]["total"] += 1
        daily_stats[date][record["section"]] += 1
        
    return daily_stats

def get_weekly_stats():
    """Get weekly usage statistics"""
    metrics = load_metrics()
    if "history" not in metrics:
        return {}
        
    weekly_stats = {
        "Monday": 0, "Tuesday": 0, "Wednesday": 0,
        "Thursday": 0, "Friday": 0, "Saturday": 0, "Sunday": 0
    }
    
    for record in metrics["history"]:
        weekly_stats[record["day_of_week"]] += 1
        
    return weekly_stats

def get_hourly_stats():
    """Get hourly usage statistics"""
    metrics = load_metrics()
    if "history" not in metrics:
        return {}
        
    hourly_stats = {hour: 0 for hour in range(24)}
    
    for record in metrics["history"]:
        hourly_stats[record["hour"]] += 1
        
    return hourly_stats