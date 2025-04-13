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

## 🛠️ Installation Guide

This guide provides step-by-step instructions to set up and run the Solar Crops Analysis project on a Google Cloud Platform (GCP) Virtual Machine.

---

### ✅ Step 1: Pre-requisites & GCP Setup

#### 🔐 1.1 Create a Service Account

Before creating the VM:

1. Go to **IAM & Admin > Service Accounts** in the GCP Console.
2. Create a new service account and assign the following roles:
  BigQuery Admin
  BigQuery Data Editor
  BigQuery Job User
  BigQuery Read Session User
  Editor
  Storage Admin
  Storage Object Creator
  Storage Object Viewer
3. While creating the VM (in the next step), **attach this service account** to the instance.
---
### 🌐 Step 2: Configure Firewall Rules

Create firewall rules to allow external access to essential services:

| Port | Purpose           |
|------|-------------------|
| 8080 | Apache Airflow UI |
| 3000 | Grafana Dashboards |

Set up these rules under **VPC Network > Firewall** with **Ingress** direction.

---

### 🖥️ Step 3: Create a VM Instance

1. Go to **Compute Engine > VM Instances** and click **Create Instance**.
2. Recommended configuration:
- **Name**: `solar-crops-vm`
- **Machine Type**: `e2-standard-2` or higher
- **Boot Disk**: Ubuntu 20.04 LTS
- **Firewall**: Allow HTTP and HTTPS traffic
- **Service Account**: Attach the one created earlier

---
### 🔑 Step 4: Generate and Configure SSH Keys

#### 4.1 On Local Machine

bash
cd ~/.ssh
ssh-keygen -t rsa -f solar_key -C your_username

This will generate:

solar_key → Private Key

solar_key.pub → Public Key

4.2 Add Public Key to VM Metadata
Go to Compute Engine > Metadata > SSH Keys and paste the contents of solar_key.pub.

4.3 Connect to the VM
Option 1: Direct command
ssh -i ~/.ssh/solar_key your_username@<EXTERNAL_IP>

Option 2: SSH config (recommended)

Create/edit ~/.ssh/config:
Host solar-vm
    HostName <EXTERNAL_IP>
    User your_username
    IdentityFile ~/.ssh/solar_key
Then connect with:
ssh solar-vm
