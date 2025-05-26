from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys

sys.path.append('/opt/airflow')
sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts"))



from data_generation_new import (
    generate_dimension_if_needed, generate_contacts_if_needed,
    generate_form_fills_if_needed, generate_website_activity_if_needed,
)

from data_validation import (
    validate_contacts_if_needed, validate_form_fills_if_needed, validate_website_activity_if_needed,
    validate_campaigns_if_needed, validate_forms_if_needed, validate_pages_if_needed
)

from upload_to_minio import upload_all_validated_files, upload_all_quarantined_files
from metadata import init_metadata_db, print_metadata
from email_notification import dq_failure_email, notify_failure
from logging_config import get_logger
from snowflake_upload import load_to_snowflake
from utils import run_dbt, run_dbt_test


logger = get_logger("Marketing_Data_Pipeline")
 
def wrap_task(fn, label):
        def _wrapped(**kwargs):
            logger.info(f"▶️ Starting task: {label}")
            fn(**kwargs)
            logger.info(f"✅ Completed task: {label}")
        return _wrapped


default_args = {
    "owner": "Yash",
    "email": ["yashbhawsar872@gmail.com"],  # for testing purpose
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": notify_failure,  # generic failure notifier

}


with DAG(
    dag_id='Marketing_Data_Pipeline',
    default_args=default_args,
    start_date=datetime(2025, 5, 25),
    schedule_interval='@daily',
    catchup=False,
    tags=['marketing', 'mock-data', 'validation', 'minio'],
    description='Generates, validates, and uploads marketing data to MinIO.'
) as dag:

    ds = "{{ ds }}"

    # Initialize metadata DB
    init_metadata_task = PythonOperator(
        task_id='init_metadata_db',
        python_callable=wrap_task(init_metadata_db, "Init Metadata DB")
    )

    # Generate and Validate all dimensions in parallel
    with TaskGroup('generate_and_validate_dims') as generate_and_validate_dims:

        # Dimension generation task
        generate_campaigns_task = PythonOperator(
            task_id='campaigns',
            python_callable=wrap_task(generate_dimension_if_needed,'Generate Campaigns'),
            op_kwargs={'name': 'campaigns', 'ds': ds}
        )
        generate_forms_task = PythonOperator(
            task_id='forms',
            python_callable=wrap_task(generate_dimension_if_needed,'Generate Forms'),
            op_kwargs={'name': 'forms', 'ds': ds}
        )
        generate_pages_task = PythonOperator(
            task_id='pages',
            python_callable=wrap_task(generate_dimension_if_needed,'Generate Pages'),
            op_kwargs={'name': 'pages', 'ds': ds}
        )

        # Dimension validation tasks
        validate_campaigns_task = PythonOperator(
            task_id='validate_campaigns',
            python_callable=wrap_task(validate_campaigns_if_needed, "Validate Campaigns"),
            op_kwargs={'ds': '{{ ds }}'},
            on_failure_callback=dq_failure_email
        )

        validate_forms_task = PythonOperator(
            task_id='validate_forms',
            python_callable=wrap_task(validate_forms_if_needed, "Validate Forms"),
            op_kwargs={'ds': '{{ ds }}'},
            on_failure_callback=dq_failure_email
        )

        validate_pages_task = PythonOperator(
            task_id='validate_pages',
            python_callable=wrap_task(validate_pages_if_needed, "Validate Pages"),
            op_kwargs={'ds': '{{ ds }}'},
            on_failure_callback=dq_failure_email
        )

    # Generate Facts 
    with TaskGroup('generate_facts') as generate_facts:
        generate_contacts_task = PythonOperator(
            task_id='contacts',
            python_callable=wrap_task(generate_contacts_if_needed,'Generate Contacts'),
            op_kwargs={'ds': ds}
        )

        generate_form_fills_task = PythonOperator(
            task_id='form_fills',
            python_callable=wrap_task(generate_form_fills_if_needed,'Generate Form Fills'),
            op_kwargs={'ds': ds}
        )

        generate_website_activity_task = PythonOperator(
            task_id='website_activity',
            python_callable=wrap_task(generate_website_activity_if_needed,'Generate Website Activity'),
            op_kwargs={'ds': ds}
        )

        

    # Validate Facts
    with TaskGroup('validate_facts') as validate_facts:
        validate_contacts_task = PythonOperator(
            task_id='validate_contacts',
            python_callable=wrap_task(validate_contacts_if_needed, "Validate Contacts"),
            op_kwargs={'ds': '{{ ds }}'},
            on_failure_callback=dq_failure_email
        )

        validate_form_fills_task = PythonOperator(
        task_id='validate_form_fills',
        python_callable=wrap_task(validate_form_fills_if_needed, "Validate Form Fills"),
        op_kwargs={'ds': '{{ ds }}'},
        on_failure_callback=dq_failure_email
        )

        validate_website_activity_task = PythonOperator(
            task_id='validate_website_activity',
            python_callable=wrap_task(validate_website_activity_if_needed, "Validate Website Activity"),
            op_kwargs={'ds': '{{ ds }}'},
            on_failure_callback=dq_failure_email
        )

    # Barrier waits for all validators (success or fail)
    dq_barrier = EmptyOperator(
        task_id="dq_barrier",
        trigger_rule=TriggerRule.ALL_DONE
    )

    # Branching operator: chooses failure alert vs upload
    def choose_path(**context):
        ti = context['ti']
        # Pull the 'new_dq_failures' flag from each validation task
        flags = [
            ti.xcom_pull(task_ids="validate_contacts",     key="new_dq_failures"),
            ti.xcom_pull(task_ids="validate_form_fills",   key="new_dq_failures"),
            ti.xcom_pull(task_ids="validate_website_activity", key="new_dq_failures"),
        ]
        # If any task has new failures → alert, else proceed to upload
        return "notify_dq_failure" if any(flags) else "proceed_upload"

    branch_on_dq = BranchPythonOperator(
        task_id="branch_on_dq",
        python_callable=choose_path,
        provide_context=True,
        trigger_rule=TriggerRule.ALL_DONE  # run after dq_barrier, regardless of success
    )

    # Dummy node for the “all good” path
    proceed_upload = EmptyOperator(
        task_id="proceed_upload",
        trigger_rule=TriggerRule.NONE_FAILED  # equivalent to ALL_SUCCESS for the branch
    )

    # Task to upload all valid files
    upload_validated_task = PythonOperator(
        task_id="upload_validated_to_minio",
        python_callable=wrap_task(upload_all_validated_files, "Upload Validated to MinIO"),
        retries=3,
        retry_delay=timedelta(minutes=2)
    )

    # Task to upload all quarantined files
    upload_quarantined_task = PythonOperator(
        task_id="upload_quarantined_to_minio",
        python_callable=wrap_task(upload_all_quarantined_files, "Upload Quarantined to MinIO"),
        retries=3,
        retry_delay=timedelta(minutes=2)
    )

    # New notify task for DQ failures
    notify_dq_failure = PythonOperator(
        task_id="notify_dq_failure",
        python_callable=dq_failure_email,     # your existing callback
        provide_context=True
    )


    # Uploading Valid Minio Data to Snowflake RAW Schema
    load_to_snowflake_task = PythonOperator(
        task_id="load_minio_to_snowflake",
        python_callable=wrap_task(load_to_snowflake, "Upload valid-data to Snowflake RAW"),
        trigger_rule=TriggerRule.ALL_SUCCESS,
        op_kwargs={'ds': '{{ ds }}'}
    )

    # --- dbt Runs --- 
    with TaskGroup('dbt_run') as dbt_run:
        #Run staging models
        dbt_run_staging_task = PythonOperator(
            task_id='dbt_run_staging',
            python_callable=wrap_task(run_dbt, "Run staging models"),
            trigger_rule=TriggerRule.ALL_SUCCESS,
            op_kwargs={
                'cmd': (
                'cd /opt/dbt/marketing_pipeline && '
                'dbt run --models staging '
                "--vars '{\"batch_date\": \"{{ ds }}\"}'"
                ),
            },
        )


        # Run mart models
        dbt_run_marts_task = PythonOperator(
            task_id='dbt_run_marts',
            python_callable=wrap_task(run_dbt, "Run mart models"),
            trigger_rule=TriggerRule.ALL_SUCCESS,
            op_kwargs={
                'cmd': (
                'cd /opt/dbt/marketing_pipeline && '
                'dbt run --models marts '
                "--vars '{\"batch_date\": \"{{ ds }}\"}'"
                ),
            },
        )
        
        # Run all tests
        dbt_test_task = PythonOperator(
            task_id='dbt_test',
            python_callable=wrap_task(run_dbt_test, "Run all dbt tests"),
            trigger_rule=TriggerRule.ALL_SUCCESS,
            retries= 0,
            op_kwargs={
                'cmd': (
                'cd /opt/dbt/marketing_pipeline && '
                'dbt test '
                ),
            },
        )



    # Final metadata logging (runs on both paths)
    print_metadata_task = PythonOperator(
        task_id='print_metadata_log',
        python_callable=wrap_task(print_metadata, "Print Metadata Logs"),
        trigger_rule="all_done",
        op_kwargs={'ds': '{{ ds }}'}
    )


    
    
    # ——————————— Define Task Dependencies ———————————

    # init_metadata --> Generation --> Validation --> Upload_to_minio --> minio_to_Snowflake --> dbt_run
    
    init_metadata_task >> [ generate_campaigns_task, generate_forms_task, generate_pages_task ]

    # Dim validation after generation 
    generate_campaigns_task >> validate_campaigns_task
    generate_forms_task     >> validate_forms_task
    generate_pages_task     >> validate_pages_task

    # generate contacts after dim validation
    [ validate_campaigns_task, validate_forms_task, validate_pages_task ] >> generate_contacts_task
    
    # generate form_fill & website_activity after generating contact data
    generate_contacts_task >> [generate_form_fills_task,generate_website_activity_task]

    # Fact Data Validation
    [generate_form_fills_task,generate_website_activity_task] >> validate_contacts_task
    generate_form_fills_task >> validate_form_fills_task
    generate_website_activity_task >> validate_website_activity_task   

    # Wait untill all validation completed (Success or Fail)
    validate_facts >> dq_barrier

    # Branch based on DQ outcomes
    dq_barrier >> branch_on_dq
    branch_on_dq >> [proceed_upload, notify_dq_failure]

    # Upload only on success
    proceed_upload >> [upload_validated_task, upload_quarantined_task]

    # On DQ Failure
    branch_on_dq >> notify_dq_failure
    
    # Now converge both paths into print_metadata_task:
    [ upload_validated_task, upload_quarantined_task, notify_dq_failure ] >> print_metadata_task

    # Load Valid data to snowflake followed by dbt run & test
    upload_validated_task >> load_to_snowflake_task >> dbt_run_staging_task >> dbt_run_marts_task >> dbt_test_task

    
    
    




