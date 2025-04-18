import json
import os
from datetime import datetime
import logging
from filelock import FileLock
import shutil

# Configuración de rutas y constantes
METRICS_DIR = "/app/data/metrics"
METRICS_FILE = os.path.join(METRICS_DIR, "app_metrics.json")
BACKUP_FILE = os.path.join(METRICS_DIR, "app_metrics.backup.json")
LOCK_FILE = os.path.join(METRICS_DIR, "metrics.lock")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB límite

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Asegurar que el directorio existe
os.makedirs(METRICS_DIR, exist_ok=True)

def check_file_size():
    """Verifica el tamaño del archivo y hace rotación si es necesario"""
    if os.path.exists(METRICS_FILE):
        size = os.path.getsize(METRICS_FILE)
        if size > MAX_FILE_SIZE:
            # Hacer backup del archivo actual
            shutil.copy2(METRICS_FILE, BACKUP_FILE)
            # Reiniciar contadores manteniendo solo el último mes
            metrics = load_metrics()
            # Resetear contadores pero mantener últimas estadísticas
            metrics = {
                "experimental_design": {"runs": 0, "last_run": metrics["experimental_design"]["last_run"]},
                "experimental_evaluation": {"runs": 0, "last_run": metrics["experimental_evaluation"]["last_run"]},
                "total_runs": 0,
                "history": []  # Mantener el historial
            }
            save_metrics(metrics)
            logger.info("Metrics file rotated due to size limit")

def load_metrics():
    """Carga las métricas del archivo con manejo de errores y backup"""
    try:
        with FileLock(LOCK_FILE):
            if os.path.exists(METRICS_FILE):
                try:
                    with open(METRICS_FILE, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    logger.error("Corrupted metrics file, loading backup")
                    if os.path.exists(BACKUP_FILE):
                        with open(BACKUP_FILE, 'r') as f:
                            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading metrics: {e}")
    
    return {
        "experimental_design": {"runs": 0, "last_run": None},
        "experimental_evaluation": {"runs": 0, "last_run": None},
        "total_runs": 0,
        "history": []  # Inicializar historial vacío
    }

def save_metrics(metrics):
    """Guarda las métricas con manejo de errores y backup"""
    try:
        with FileLock(LOCK_FILE):
            # Crear backup antes de escribir
            if os.path.exists(METRICS_FILE):
                shutil.copy2(METRICS_FILE, BACKUP_FILE)
            
            with open(METRICS_FILE, 'w') as f:
                json.dump(metrics, f)
            
            check_file_size()
    except Exception as e:
        logger.error(f"Error saving metrics: {e}")

def update_metrics(section):
    """Actualiza las métricas para una sección específica"""
    try:
        metrics = load_metrics()
        current_time = datetime.now()
        
        # Log para depuración
        logger.info(f"Updating metrics for section: {section}")
        logger.info(f"Current metrics: {metrics}")
        
        # Actualizar contadores
        metrics[section]["runs"] += 1
        metrics[section]["last_run"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        metrics["total_runs"] += 1
        
        # Agregar nuevo registro al historial
        new_record = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "section": section,
            "date": current_time.strftime("%Y-%m-%d"),
            "day_of_week": current_time.strftime("%A"),
            "hour": current_time.hour
        }
        
        # Asegurar que existe la lista de historial
        if "history" not in metrics:
            metrics["history"] = []
            logger.info("Initializing history list")
            
        metrics["history"].append(new_record)
        logger.info(f"Added new record: {new_record}")
        
        save_metrics(metrics)
        logger.info("Metrics saved successfully")
        return metrics
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")
        return None    
def get_daily_stats():
    """Obtiene estadísticas de uso por día"""
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
    """Obtiene estadísticas de uso por día de la semana"""
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
    """Obtiene estadísticas de uso por hora del día"""
    metrics = load_metrics()
    if "history" not in metrics:
        return {}
        
    hourly_stats = {hour: 0 for hour in range(24)}
    
    for record in metrics["history"]:
        hourly_stats[record["hour"]] += 1
        
    return hourly_stats