FROM apache/airflow:2.10.5
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         openjdk-17-jre-headless \
  && apt-get install -y procps \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/bitnami/spark/jars && \
    curl -o /opt/bitnami/spark/jars/postgresql-42.2.23.jar https://jdbc.postgresql.org/download/postgresql-42.2.23.jar && \
    curl -o /opt/bitnami/spark/jars/spark-3.5-bigquery-0.36.5.jar \
https://repo1.maven.org/maven2/com/google/cloud/spark/spark-bigquery-with-dependencies_2.12/0.36.5/spark-bigquery-with-dependencies_2.12-0.36.5.jar && \
curl -o /opt/bitnami/spark/jars/gcs-connector-hadoop3-latest.jar \
    https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-hadoop3-latest.jar

USER airflow
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
RUN pip install --upgrade pip

RUN pip uninstall -y apache-airflow apache-airflow-providers-openlineage && \
pip cache purge

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" apache-airflow-providers-apache-spark==2.1.3

# Copy requirements.txt to the working directory
COPY ../requirements.txt /opt/airflow/requirements.txt

RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt