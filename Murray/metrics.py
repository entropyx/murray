import json
from datetime import datetime

def load_metrics():
    try:
        with open('usage_counter.txt', 'r') as f:
            return json.load(f)
    except:
        return {
            "experimental_evaluation": {"runs": 0, "last_run": None},
            "experimental_design": {"runs": 0, "last_run": None}
        }

def update_metrics(page):
    metrics = load_metrics()
    metrics[page]["runs"] += 1
    metrics[page]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open('usage_counter.txt', 'w') as f:
        json.dump(metrics, f)
    
    return metrics 