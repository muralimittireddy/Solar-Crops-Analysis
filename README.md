# Solar-Crops-Analysis
**Solar-Crops-Analysis** is an end-to-end Data Engineering and Machine Learning pipeline that leverages weather data to explore the impact of solar energy on agriculture. The project demonstrates complete lifecycle implementation — from data ingestion, transformation, and modeling to dashboarding — all containerized and deployed on a Google Cloud Platform Virtual Machine.

## 🛠️ End-to-End Pipeline Overview

- 🔄 Fetch weather data from Open-Meteo API
- ☁️ Store raw data in **Google Cloud Storage (Parquet)** and **PostgreSQL**
- 🔧 Transform data using **Apache Spark**
- 🚀 Load transformed data into **BigQuery**
- 🧠 Train a **Random Forest Machine Learning model** using data from BigQuery
- 📈 Build **Grafana dashboards** for visual insights
- 🧩 Orchestrate tasks using **Apache Airflow**
- 📦 Containerized using **Docker**
- 🌐 Fully deployed and executed in a **GCP Virtual Machine**

## Project Architecture

Here’s an overview of the project architecture:

![Project Architecture](images/architecture.png)
