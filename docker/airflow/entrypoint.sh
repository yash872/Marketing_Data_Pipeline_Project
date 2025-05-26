#!/bin/bash
echo "Running Airflow DB Upgrade..."
airflow db upgrade

# Create admin user only if not already present
echo "Checking for existing admin user..."
airflow users list | grep -q "$AIRFLOW_ADMIN_USERNAME"
if [ $? -ne 0 ]; then
    echo "Creating admin user..."
    airflow users create --username "$AIRFLOW_ADMIN_USERNAME" \
                         --firstname "$AIRFLOW_ADMIN_FIRSTNAME" \
                         --lastname "$AIRFLOW_ADMIN_LASTNAME" \
                         --role Admin \
                         --email "$AIRFLOW_ADMIN_EMAIL" \
                         --password "$AIRFLOW_ADMIN_PASSWORD"
else
    echo "Admin user already exists."
fi

# Properly invoke the airflow command
exec airflow "$@"
