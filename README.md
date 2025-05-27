# Marketing Data Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

An end-to-end, production-grade ELT pipeline for synthetic marketing data—covering generation, validation, storage, transformation, monitoring, and performance benchmarking. Built with Docker for local development and easily portable to cloud.

---

## 📖 Table of Contents

1. [Project Overview](#project-overview)  
2. [Repository Structure](#repository-structure)  
3. [Tech Stack](#tech-stack)  
4. [Prerequisites](#prerequisites)  
5. [Setup & Installation](#setup--installation)  
6. [Configuration](#configuration)  
7. [Running the Pipeline](#running-the-pipeline)  
8. [Design Decisions & Scope](#design-decisions--scope)  
9. [Future Improvements](#future-improvements)  
10. [Contributing](#contributing)  

---

## Project Overview

This repository implements a robust marketing data pipeline that:

- **Generates** synthetic marketing data (contacts, form fills, web events) in CSV, JSON, and Parquet  
- **Validates** data with schema, null/uniqueness, format, and freshness checks, quarantining invalid records  
- **Stores** files in an S3-compatible object store (MinIO locally, AWS S3 in production)  
- **Orchestrates** tasks with Apache Airflow, featuring retries, callbacks, and metrics logging  
- **Transforms** data using dbt incremental models in Snowflake, with built-in tests and documentation  
- **Optimizes** performance via Snowflake clustering and Pandas vectorization  
- **Monitors** pipeline health and data quality with alerts over email and Slack  

---

## Repository Structure

```
├── config/
│   └──  airflow.cfg 
├── dags/
│   └──  Marketing_Data_Pipeline.py              <-- Airflow DAG definitions
├── data/                                        <-- Input data files location (generated)
│   ├── quarantine_data/
│   ├── raw_data/
│   ├── uploaded_data/
│   ├── validated_data/
|   └── metadata.db.py                           <-- metadata.db will generate here            
├── scripts/
│   ├── data_generator.py                        <-- Generates synthetic datasets
│   ├── data_validation.py                       <-- Runs data quality checks
│   ├── email_notification.py                    <-- email service using smtp server (gmail)
│   ├── logging_config.py                        <-- custom logging functions
│   ├── metadata.py                              <-- metadata db operation handling logic
│   ├── upload_to_minio.py                       <-- Idempotent upload to minio
│   └── snowflake_upload.py                      <-- logic to load data from minio to snowflake 
├── dbt/                                         <-- dbt project for transformations
|   ├── log/                      
│   ├── marketing_pipeline/
|   │   ├── models/                              <-- dbt models
|   |   │   ├── marts/
|   |   │   ├── staging/
|   │   ├── tests/                               <-- custome test cases
|   │   └── dbt_project.yml/
│   └── target/
├── docker/                  
|   ├── docker-compose.yml                       <-- Local dev stack (Airflow, MinIO, Postgres)
|   ├── airflow
|   │   ├── Dockerfile                           <-- Builds Python & DAG image
|   │   ├── entrypoint.sh
|   │   └── requirements.txt                     <-- all pyhton installation requirements
├──documents/
|   ├── Marketing_Data_Pipeline_Project.doc      <-- Detailed document of the complete project
├──logs/
|   ├── pipeline.log                             <-- Mounted with Airflow log path
├──images/                                     
├── .env                                         <-- Sample environment variables
├── README.md                                    <-- This file
└── LICENSE
```

---

## Tech Stack

| Layer                | Technology                                          |
|----------------------|-----------------------------------------------------|
| Orchestration        | Apache Airflow 2.x (Docker Compose)                 |
| Scripting & Compute  | Python 3.8, Faker, pandas, pyarrow                  |
| Object Storage       | MinIO (S3-compatible)                               |
| Validation & Upload  | Python, MinIO (S3-compatible)                       |
| Metadata Store       | SQLite (local file metadata.db)                     |
| Data Warehouse       | Snowflake (Standard Edition)                        |
| Transformation       | dbt v1.8.7                                          |
| Logging & Alert      | Airflow callbacks, python-json-logger, Email Alerts |

---

## Prerequisites

- Docker & Docker Compose  
- Python 3.8+ `(for script testing)`
- dbt `(if you want to test locally)`
  
  ```bash
   pip install dbt-snowflake
   ``` 
- Snowflake account & credentials

### Note:
- The configuration below has been provided solely for demonstration and ease of use; it does not represent our standard production practices and will be updated in due course:
- Snowflake:
  - A Snowflake Trial account has been provisioned with the necessary users, roles, tables, and stages. All associated SQL provisioning scripts are available in the repository for your reference.
  - dbt is configured to connect to Snowflake via the profiles.yml file in the project’s root config directory. This file is volume-mounted into the Airflow container—please see the volume mappings in docker-compose.yml for details.
  - URL:  https://uw98118.ap-southeast-1.snowflakecomputing.com/console/login

---

## Setup & Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/yash872/Marketing_Data_Pipeline_Project.git
   cd Marketing_Data_Pipeline_Project
   cd docker
   ```
2. **Build and launch services**
- Docker shold be up and running in your machine you can check it with:
  
  ```bash
   docker ps
   ```
  
- you should see somthing like this
  ![docker_ps](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/docker_ps.PNG)
  
- Once the docker is up and running you can run below command, make sure you run it from docker directory where the `docker-compose.yml` is present
  
   ```bash
   docker-compose up -d --build
   ```
   
- No need to createa airflow Admin user, as we already mentioned those steps in `entrypoint.sh` to create user at run time.
- It may take little longer in first time to setup and run Airflow servers, please be patient..
  
- when the airflow-webserver is up and rumming you will see below log INFO Listening at  http://0.0.0.0:8080
  ![docker_build](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/docker_build.PNG)
   
---

## Running the Pipeline

- Once the airflow servers are up and running, we are good to go!!
- AS we have created end to end pipeline from Generation --> Validation --> Load to Data Lake (minio) --> minio to snowflake staging --> dbt run, test
- Try to access:
- **Airflow UI**: http://localhost:8080  
- **MinIO Console**: http://localhost:9001


- you will see a login screen asking for credential, give username: airflow, password: airflow
   
- you should see Airflow UI main screen with Dags like below
  ![airflow_main](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/airflow_main.PNG)

- Now you can run the pipeline manually or schedule by changing the default args like `start_date`.

---

### dbt Transform & Tests 
- `(only if you want to test locally)`
    ```bash
    cd Marketing_Data_Pipeline_Project
    cd dbt
    
    dbt run --models staging
    dbt run --models marts
    dbt test
    ```
---

## Execution Flow with Screenshots
-  Complete Pipeline End to End
   ![dag_full](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dag_full.PNG)

   **Now lets have a closer look:**
-  This is the starting of the pipeline where we initiate the metadata.db before starting any execution so that we can logging acticity and metadata tracking.
-  Once the metadata.db is created it will trigger the generation task parallel for all dimensions followed by validation task for each if them.
-  after generation dimension tasks, generation fact will be triggerd, where first contact will be create so that it can be used in other 2 Facts as reference.  
   ![dag_gen](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dag_gen.PNG)

-  here we wait until the fact data generated and then we executed the validation task for each data task.
   ![dag_val_fact](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dag_val_fact.PNG)

-  In the next step:
    - we will wait for all data validation task to be completed before proceeding further, thats the purpose of having dq_barrier as `EmptyOperator` and with TRIGGER_RULE AS `ALL_DONE`
    - `branch_on_dq` will choose the path from `proceed_upload` and `notify_dq_failure` based on the XCom values set by data validation result.
    - On ailed Data Validation It will choose `notify_dq_failure` and send an Alert Email with the URL and Error message.
    - On successful Data Validation result it will choose `proceed_upload`  and `notify_dq_failure` will be skipped as showing in image.
    - In the Data Validation process we do check on both file-level & row level, and based on that we create 2 set of data identified as valid-data in validagted-data folder and Invalid-data in quarantine_data data folder.
    - In the Next step we upload our data on data lake (using minio here for local development), using the task `upload_validated_to_minio` and `upload_quarantined_to_minio`.
    - To capture all in metadata.db data as Airflow logs, we have a task `print_metadata_log` which will print the captured intermediate meatadata as airflow logs for that dag run.
    - Once the `upload_validated_to_minio` completed successfully, `load_minio_to_snowflake` will be executed, which will upload the valid data files from minio to snowflake stage, using PUT & COPY INTO commands.
     ![dag_upload](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dag_upload.PNG)

-  After successfull completion of `load_minio_to_snowflake` It will trigger the dbt tasks.
    - `dbt_run_staging` this will run the staging models, and create staging data table from raw table inside snowflake STG Schema, e.g.  MARKETING_DB.RAW.RAW_CONTATCS --->  MARKETING_DB.STG.STG_CONTATCS.
    - After successfull creation of all staging data it will trigger `dbt_run_marts`, to create marts table inside snowlake MART Schema, e.g.  MARKETING_DB.STG.STG_CONTATCS --->  MARKETING_DB.MART.MART_CONTATCS.
    - Once we have both STG and MART data creation completed it will trigger the `dbt_test` to run all the default and custom test defined in `schema.yml`.
    - After completion of the dbt test, we will be get an email notification if there are failed test cases, for better monitoring purpose.
      
     ![dag_dbt](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dag_dbt.PNG)

-  Once the pipeline is completed successfully:
  - you will be able to see the Dag status on as successfull on Airflow home page like below
    
    ![dag_main_run](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dag_main_run.PNG)

  - Inside the Dag running screen, on the left panel you can see all the task in order of completion with Green mark for successfull run.
    
   ![dag_run_bar](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dag_run_bar.PNG)

---

## Logs and Outputs:

-  All the captured Logs are available in logs/pipeline.log
  
-  XCom values passed during data validation for `notify_dq_failure` check:
   ![dag_xcom](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dag_xcom.PNG)

-  logs generated during `dbt_run_staging`:
   ![dbt_log_stg](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dbt_log_stg.PNG)

-  logs generated during `dbt_run_marts`:
   ![dbt_log_mart](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dbt_log_mart.PNG)
   
-  you can check the `dbt_test` run result and Notification alert email sent INFO.
   ![dbt_test_email](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/dbt_test_email.PNG)
   
-  Alert Email received on my mailbox.
   ![email_notification](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/email_notification.PNG)

-  Snowflake Data Screenshots as Output:
    - Snowflake RAW Schema Tables, Stages, and File Formats Pre Created as part of Initial Setup
    ![snowflaek_RAW_schema](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/snowflaek_RAW_schema.PNG)

    - Snowflake sample output for MARKETING_DB.MART.MART_CONTATCS
    ![snowflake_mart_contacts](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/snowflake_mart_contacts.PNG)   

---

## Design Decisions & Scope

- **Docker-First**: Local, zero-cost demos; production uses AWS services  
- **MinIO**: S3-compatible for ease; swap to AWS S3 by updating endpoint/creds  
- **SQLite Metadata**: Simple file store; can migrate to Postgres/RDS  
- **Validation Engine**: Pandas vectorization chosen for simplicity; Spark/Dask option exists  
- **Scope**: Complete ELT with DQ, orchestration, performance benchmarking; focused on production best practices

---

## Future Improvements

- Real-time ingestion (Kafka/Kinesis)  
- Advanced DQ dashboards (Great Expectations)  
- Managed Airflow (AWS MWAA / GCP Composer)  
- Full CI/CD (GitHub Actions)  
- Cloud metadata store (Postgres/Aurora)  

---

## Contributing

1. Fork the repo  
2. Create a feature branch (`git checkout -b feature/XYZ`)  
3. Commit & push your changes  
4. Open a Pull Request  

---

## License

This project is MIT licensed. See [LICENSE](./LICENSE) for details.
