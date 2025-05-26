FROM apache/airflow:2.8.1-python3.10

USER root
COPY entrypoint.sh /entrypoint.sh
COPY requirements.txt /requirements.txt
RUN chmod +x /entrypoint.sh

USER airflow
RUN pip install --no-cache-dir -r /requirements.txt
ENTRYPOINT ["/entrypoint.sh"]