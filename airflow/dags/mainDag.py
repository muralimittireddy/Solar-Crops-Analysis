from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime, timedelta
from extract import extract_data


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 3, 15),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='solar_energy_crops_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False
)


start = PythonOperator(
    task_id="start",
    python_callable=lambda: print("Jobs started"),
    dag=dag
)


extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    dag=dag
)

# Define the Spark job task
submit_spark_job = SparkSubmitOperator(
    task_id="submit_spark_job",
    application="jobs/transform.py",  # Path to your Spark script
    conn_id="spark_mm",  # Spark connection ID
    conf={"spark.master": "spark://spark-master:7077",
         "spark.hadoop.google.cloud.auth.service.account.enable": "true",
        "spark.hadoop.fs.gs.impl": "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem",
        "spark.hadoop.fs.AbstractFileSystem.gs.impl": "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS",
        },
    jars="/opt/bitnami/spark/jars/postgresql-42.2.23.jar,/opt/bitnami/spark/jars/spark-3.5-bigquery-0.36.5.jar,/opt/bitnami/spark/jars/gcs-connector-hadoop3-latest.jar",
    dag=dag
)

end = PythonOperator(
    task_id="end",
    python_callable=lambda: print("Jobs ended"),
    dag=dag
)

start >> extract_task >> submit_spark_job >> end