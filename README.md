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

### Note!:
- Below setup is created intentionally for ease of use and demonstration purpose only, not a part of standard practices and will be changed accordingly after some time.
- Snowflake:
   - I have already created and setup Snowflake Trial account with all required user, role, table, stage etc. In case if you want to know I have kept the SQL scripts in repo.
   - dbt will connect with snowflake using profiles.yml placed in root config folder and mapped with airflow container profiles.yml, you can check volumes mapping in docker-compose.yml  

---

## Setup & Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/yash872/Marketing_Data_Pipeline_Project.git
   cd Marketing_Data_Pipeline_Project
   cd docker
   ```
2. **Build and launch services**
- Docker shold be up and running in your machine.
- you can check it with
-  ```bash
   docker ps
   ```
- you should see somthing like this
- ![docker_ps](https://github.com/yash872/Marketing_Data_Pipeline_Project/blob/main/Images/docker_ps.PNG)
- Once the docker is started running you can below command, remeber to run it from docker directory where the docker-compose.yml is available
   ```bash
   docker-compose up -d --build
   ```
- entrypoint.sh is having the logic to create airfow admin user at run time.
- It may take little longer in first time to setup and run Airflow servers.
- when the airflow-webserver is up and rumming you will see below log INFO Listening at http://0.0.0.0:8080
   
---


## Running the Pipeline

- Once the airflow servers are up and running, we are good to go!
- AS we have created end to end pipeline from Generation --> Validation --> Load to Data Lake (minio) --> minio to snowflake staging 
- Try to access:
- **Airflow UI**: http://localhost:8080  
- **MinIO Console**: http://localhost:9001  

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
