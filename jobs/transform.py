import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, date_format, mean, sum as _sum, stddev, when, min as _min, max as _max, lit
)
from pyspark.sql.types import DateType
from pyspark.sql.functions import to_timestamp

# Initialize Spark session
try:
    spark = SparkSession.builder \
        .appName("WeatherDataTransformation") \
    .config("spark.hadoop.fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem") \
    .config("spark.hadoop.fs.AbstractFileSystem.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS") \
    .config("spark.hadoop.google.cloud.auth.service.account.enable", "true") \
        .config("spark.jars", "/opt/bitnami/spark/jars/postgresql-42.2.23.jar,/opt/bitnami/spark/jars/spark-3.5-bigquery-0.36.5.jar,/opt/bitnami/spark/jars/gcs-connector-hadoop3-latest.jar") \
        .getOrCreate()
except Exception as e:
    logging.error(f"Error initializing Spark session: {e}")
    exit(1)

# Configure Spark to use GCS for BigQuery
spark.conf.set("spark.hadoop.fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem")
spark.conf.set("spark.hadoop.fs.gs.auth.service.account.enable", "true")
spark.conf.set("fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem")
spark.conf.set("fs.AbstractFileSystem.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS")



# PostgreSQL Connection
postgres_url = "jdbc:postgresql://postgres_app/app_db"
properties = {
    "user": "app_user",
    "password": "app_password",
    "driver": "org.postgresql.Driver"
}

# Load Data
try:
    hourly_weather = spark.read.jdbc(postgres_url, '"hourly_data"', properties=properties)
    daily_weather = spark.read.jdbc(postgres_url, '"daily_data"', properties=properties)
except Exception as e:
    logging.error(f"Error loading data from PostgreSQL: {e}")
    spark.stop()
    exit(1)

# Convert time column to Date
hourly_weather = hourly_weather.withColumn("time", to_timestamp(col("time"), "yyyy-MM-dd'T'HH:mm")) \
                               .withColumn("date", col("time").cast(DateType()))

# Aggregate Hourly Data to Daily
daily_agg = hourly_weather.groupBy("date").agg(
    mean("temperature_2m").alias("temperature_2m"),
    _max("temperature_2m").alias("max_temperature"),
    _min("temperature_2m").alias("min_temperature"),
    mean("relative_humidity_2m").alias("relative_humidity_2m"),
    _sum("precipitation").alias("precipitation"),
    _sum("sunshine_duration").alias("sunshine_duration"),
    _sum("direct_radiation").alias("direct_radiation"),
    _sum("diffuse_radiation").alias("diffuse_radiation"),
    mean("soil_temperature_6cm").alias("soil_temperature_6cm"),
    mean("wind_speed_10m").alias("wind_speed_10m")
)

# Normalize Units
daily_agg = daily_agg.withColumn("direct_radiation", col("direct_radiation") * 0.0864) \
                     .withColumn("diffuse_radiation", col("diffuse_radiation") * 0.0864) \
                     .withColumn("precipitation", col("precipitation") / 10)

# Derived Features
daily_agg = daily_agg.withColumn("GDD", ((col("max_temperature") + col("min_temperature")) / 2 - 10)) \
                     .withColumn("GDD", when(col("GDD") < 0, 0).otherwise(col("GDD")))

daily_agg = daily_agg.withColumn("heat_stress", when(col("temperature_2m") > 35, 1).otherwise(0))

# Compute Min/Max values for indices
soil_temp_min = daily_agg.agg(_min("soil_temperature_6cm")).collect()[0][0]
soil_temp_max = daily_agg.agg(_max("soil_temperature_6cm")).collect()[0][0]
precip_min = daily_agg.agg(_min("precipitation")).collect()[0][0]
precip_max = daily_agg.agg(_max("precipitation")).collect()[0][0]

# Avoid division by zero
soil_temp_range = soil_temp_max - soil_temp_min if soil_temp_max != soil_temp_min else 1
precip_range = precip_max - precip_min if precip_max != precip_min else 1

# Apply Indices
daily_agg = daily_agg.withColumn("soil_moisture_index", (col("soil_temperature_6cm") - lit(soil_temp_min)) / lit(soil_temp_range)) \
                     .withColumn("drought_index", (col("precipitation") - lit(precip_min)) / lit(precip_range))

# Total Solar Radiation
daily_agg = daily_agg.withColumn("total_solar_radiation", col("direct_radiation") + col("diffuse_radiation"))

# Radiation Efficiency (Handle division by zero)
daily_agg = daily_agg.withColumn("radiation_efficiency",
    when(col("sunshine_duration") > 0, col("total_solar_radiation") / col("sunshine_duration"))
    .otherwise(lit(0))
)

# Extract Month and Year
daily_agg = daily_agg.withColumn("month", date_format(col("date"), "M")) \
                     .withColumn("year", date_format(col("date"), "yyyy"))

# Monthly Aggregation
monthly_agg = daily_agg.groupBy("year", "month").agg(
    _sum("GDD").alias("GDD"),
    _sum("precipitation").alias("precipitation"),
    _sum("sunshine_duration").alias("sunshine_duration"),
    _sum("direct_radiation").alias("direct_radiation")
)

# Seasonal Aggregation (June–November)
seasonal_agg = daily_agg.filter((col("month") >= 6) & (col("month") <= 11)).groupBy("year").agg(
    _sum("GDD").alias("GDD"),
    _sum("precipitation").alias("precipitation"),
    _sum("sunshine_duration").alias("sunshine_duration"),
    _sum("direct_radiation").alias("direct_radiation"),
    _sum("diffuse_radiation").alias("diffuse_radiation")
)

# Compute Rainfall Variability Index
precip_mean = seasonal_agg.agg(mean("precipitation")).collect()[0][0]
precip_std = seasonal_agg.agg(stddev("precipitation")).collect()[0][0]
seasonal_agg = seasonal_agg.withColumn("rainfall_variability",
    when(lit(precip_mean) > 0, lit(precip_std) / lit(precip_mean))
    .otherwise(lit(0))
)

# Seasonal Drought Index
seasonal_precip_min = seasonal_agg.agg(_min("precipitation")).collect()[0][0]
seasonal_precip_max = seasonal_agg.agg(_max("precipitation")).collect()[0][0]
seasonal_precip_range = seasonal_precip_max - seasonal_precip_min if seasonal_precip_max != seasonal_precip_min else 1

seasonal_agg = seasonal_agg.withColumn("drought_index", (col("precipitation") - lit(seasonal_precip_min)) / lit(seasonal_precip_range))

# Save to BigQuery
for df, table in [(daily_agg, "Daily_WeatherData"), (monthly_agg, "Monthly_WeatherData"), (seasonal_agg, "Seasonal_WeatherData")]:
    df.write.format("bigquery") \
        .option("table", f"solarcropsanalysis-454507.weatherData_SolarCropsAnalysis_1.{table}") \
        .option("temporaryGcsBucket", "solar-crops-analysis-archival-data-1") \
        .mode("overwrite") \
        .save()

# Stop Spark session
spark.stop()