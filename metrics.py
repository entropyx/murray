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
                "total_runs": 0
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
        "total_runs": 0
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
        metrics[section]["runs"] += 1
        metrics[section]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metrics["total_runs"] += 1
        save_metrics(metrics)
        return metrics
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")
        return None 