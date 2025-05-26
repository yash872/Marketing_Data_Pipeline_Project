from airflow.operators.email import EmailOperator
from logging_config import get_logger
import functools
import time
import re
import subprocess
from email_notification import notify_failure

logger_json = get_logger(__name__, use_json=True)
logger = get_logger(__name__)


def capture_metrics(task_name: str):
    """
    Decorator to capture operational metrics for a task:
      - records_in, records_out
      - start_time, end_time, duration_sec
    Logs a single JSON entry with these fields under 'task_metrics'.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Record start
            start_ts = time.time()
            
            # Execute task
            result = func(*args, **kwargs)
            
            # Record end
            end_ts = time.time()
            duration = end_ts - start_ts
            
            # Extract record counts
            try:
                rows_in, rows_out = result
            except Exception:
                # Fall back: count on kwargs or use length
                rows_in = kwargs.get('records_in', None)
                # If result is iterable, attempt len()
                try:
                    rows_out = len(result)
                except Exception:
                    rows_out = None

            # Prepare metrics payload
            metrics = {
                'task': task_name,
                'records_in': rows_in,
                'records_out': rows_out,
                'start_time': start_ts,
                'end_time': end_ts,
                'duration_sec': round(duration, 3),
            }

            # Emit JSON log
            logger_json.info('task_metrics', extra=metrics)

            return result
        return wrapper
    return decorator


# Utility to run generic dbt commands and stream output to Airflow logs
def run_dbt(cmd: str, **context):
    logger.info(f"Running dbt command: {cmd}")
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        
        text=True
    )
    
    
    for line in process.stdout:
        logger.info(line.strip())
    process.stdout.close()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"dbt command failed with exit code {return_code}")

# Wrapper for tests: catch failures, send notification, but do not fail the task
def run_dbt_test(cmd: str, **kwargs):
    logger.info(f"Running dbt tests: {cmd}")
    try:
        run_dbt(cmd)
        logger.info("dbt tests passed successfully.")
    except RuntimeError as e:
        logger.error(f"dbt tests failed: {e}")
        # send a notification using your existing failure handler
        context = kwargs
        # notify_failure expects **context
        notify_failure(context)
        # swallow exception so task succeeds