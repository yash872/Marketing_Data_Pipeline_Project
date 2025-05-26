from airflow.operators.email import EmailOperator
from logging_config import get_logger
import functools
import time

logger = get_logger(__name__)

def dq_failure_email(context):
    ti = context['task_instance']
    err = context['exception']
    ds = context['execution_date'].strftime("%Y-%m-%d")
    filename = ti.xcom_pull(task_ids=ti.task_id, key='return_value') or 'unknown'
    
    subject = f"[Airflow][{ds}] DQ Failure: {ti.task_id}"
    body = f"""
    <h3>Data Quality Failure</h3>
    <p><strong>Task:</strong> {ti.task_id}</p>
    <p><strong>File:</strong> {filename}</p>
    <p><strong>Error:</strong><br><pre>{err}</pre></p>
    """

    logger.warning(f"📧 Sending DQ failure email for task: {ti.task_id}, file: {filename}, error: {err}")

    EmailOperator(
        task_id="email_on_dq_fail",
        to=["yashbhawsar872@gmail.com"],
        subject=subject,
        html_content=body
    ).execute(context=context)


def notify_failure(context):
    """
    Generic failure callback for Airflow tasks.
    Sends an email summarizing the failed task and links to logs.
    """
    ti = context['task_instance']
    dag_id = ti.dag_id
    task_id = ti.task_id
    try_number = ti.try_number
    max_tries = ti.max_tries or context.get('task').retries
    max_tries+=1
    execution_time = context.get('ts')
    log_url = ti.log_url
    #summary = ti.xcom_pull(key="dbt_test_summary")

    subject = f"[Airflow] Failure in {dag_id}.{task_id} (Attempt {try_number}/{max_tries})"
    body = f"""
    <p><b>DAG:</b> {dag_id}</p>
    <p><b>Task:</b> {task_id}</p>
    <p><b>Execution Time:</b> {execution_time}</p>
    <p><b>Attempt:</b> {try_number} of {max_tries}</p>
    <p>View logs: <a href="{log_url}">{log_url}</a></p>
    """

    logger.warning(f"📧 Sending generic failure email [Airflow] Failure in {dag_id}.{task_id} (Attempt {try_number}/{max_tries})")

    EmailOperator(
        task_id="email_on_generic_failure",
        to=["yashbhawsar872@gmail.com"],
        subject=subject,
        html_content=body
    ).execute(context=context)