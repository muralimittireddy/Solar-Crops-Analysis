# Use the official Bitnami Spark image as the base
FROM bitnami/spark:latest

USER root

RUN install_packages curl

RUN apt-get update && apt-get install -y procps

# Set environment variables for Spark
ENV SPARK_HOME=/opt/bitnami/spark
ENV PATH=$SPARK_HOME/bin:$PATH

# Download and add the PostgreSQL JDBC driver
RUN curl  https://jdbc.postgresql.org/download/postgresql-42.2.23.jar -o /opt/bitnami/spark/jars/postgresql-42.2.23.jar && \
    curl https://repo1.maven.org/maven2/com/google/cloud/spark/spark-bigquery-with-dependencies_2.12/0.36.5/spark-bigquery-with-dependencies_2.12-0.36.5.jar -o /opt/bitnami/spark/jars/spark-3.5-bigquery-0.36.5.jar  && \
curl -o /opt/bitnami/spark/jars/gcs-connector-hadoop3-latest.jar \
    https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-hadoop3-latest.jar

# Update permissions
RUN chmod 644 $SPARK_HOME/jars/*.jar
# Set up the classpath environment variable
ENV SPARK_CONF_DIR=$SPARK_HOME/conf
ENV SPARK_CLASSPATH=$SPARK_HOME/jars/*

# Create config directory and spark-defaults.conf file
RUN mkdir -p $SPARK_CONF_DIR && touch $SPARK_CONF_DIR/spark-defaults.conf

# Add configurations to spark-defaults.conf
RUN echo "spark.jars $SPARK_HOME/jars/gcs-connector-hadoop3-latest.jar,$SPARK_HOME/jars/spark-bigquery-with-dependencies_2.12-0.36.5.jar" >> $SPARK_CONF_DIR/spark-defaults.conf && \
    echo "spark.hadoop.google.cloud.auth.service.account.enable true" >> $SPARK_CONF_DIR/spark-defaults.conf


# Start Spark shell by default (change to another command if needed)
CMD [ "spark-shell" ]