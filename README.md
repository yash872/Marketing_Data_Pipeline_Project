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
11. [License](#license)

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
.
├── dags/                       # Airflow DAG definitions
├── scripts/
│   ├── data_generator.py      # Generates synthetic datasets
│   ├── data_validation.py     # Runs data quality checks
│   └── upload_to_minio.py     # Idempotent upload logic
├── dbt/                        # dbt project for transformations
│   ├── models/
│   └── schema.yml
├── docs/                       # Project documentation (Word, PDFs)
├── docker-compose.yml          # Local dev stack (Airflow, MinIO, Postgres)
├── Dockerfile                  # Builds Python & DAG image
├── .env.example                # Sample environment variables
├── README.md                   # This file
└── LICENSE
```

---

## Tech Stack

| Layer               | Technology                                |
|---------------------|-------------------------------------------|
| Orchestration       | Apache Airflow 2.x (Docker Compose)       |
| Generation          | Python 3.8, Faker, pandas, pyarrow        |
| Validation & Upload | Python, MinIO (S3-compatible)             |
| Transformation      | dbt v1.8.7, Snowflake                     |
| Metadata & Logging  | SQLite, python-json-logger, Slack API     |

---

## Prerequisites

- Docker & Docker Compose  
- Python 3.8+ (for script testing)  
- Snowflake account & credentials (for dbt models)

---

## Setup & Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/your-org/marketing-data-pipeline.git
   cd marketing-data-pipeline
   ```
2. **Build and launch services**  
   ```bash
   docker-compose up -d --build
   ```
3. **Initialize Airflow**  
   ```bash
   docker exec -it airflow_scheduler bash
   airflow db init
   airflow users create      --username admin      --firstname Admin      --lastname User      --role Admin      --email admin@example.com
   exit
   ```
---

## Configuration

1. Copy `.env.example` to `.env` and set your values:
   ```ini
   SNOWFLAKE_ACCOUNT=...
   SNOWFLAKE_USER=...
   SNOWFLAKE_PASSWORD=...
   SNOWFLAKE_WAREHOUSE=...
   SNOWFLAKE_DATABASE=...
   SNOWFLAKE_SCHEMA=...

   MINIO_ENDPOINT=minio:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin
   ```
2. Verify MinIO console at: `http://localhost:9001` (minioadmin/minioadmin)

---

## Running the Pipeline

### Trigger via Airflow
```bash
docker exec -it airflow_scheduler bash
airflow dags trigger Marketing_Data_Pipeline
```
- **Airflow UI**: http://localhost:8080  
- **MinIO Console**: http://localhost:9001  

### dbt Transform & Tests
```bash
docker exec -it dbt_runner bash
dbt deps
dbt run --profiles-dir .
dbt test --profiles-dir .
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
