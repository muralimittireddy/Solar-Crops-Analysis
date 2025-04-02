import requests
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from google.cloud import storage
import os
from sqlalchemy import create_engine
# import yaml
import aiohttp  # Async HTTP library
import asyncio  # Async programming library

POSTGRES_CONN = "postgresql://app_user:app_password@postgres_app:5432/app_db"
engine = create_engine(POSTGRES_CONN)
# Google Cloud Storage settings
GCS_BUCKET_NAME = "solar-crops-analysis-archival-data-1"  # Replace with your GCS bucket name
# Define a local storage path using the OS module
LOCAL_STORAGE_PATH = os.path.join(os.getcwd(), "temp_storage")

# Ensure the directory exists
os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True) 
# Initialize Google Cloud Storage client
storage_client = storage.Client()

async def main():
    semaphore = asyncio.Semaphore(1)  # Limit the number of concurrent requests
    async with aiohttp.ClientSession() as session:  # Creates a session for all requests
        results = []
        for i in range(1967, 2017+1):  # Process one year at a time
            tasks = [fetch_data_with_semaphore(session, year, semaphore) for year in range(i, i + 1)]
            print(f"Fetching data for year {i}")
            batch_results = await asyncio.gather(*tasks)  # Runs the tasks for one year
            results.extend(batch_results)
            print("Sleeping for a while to respect API rate limits...")
            await asyncio.sleep(60)  # Sleep for 60 seconds to respect API rate limits
    return results

async def fetch_data_with_semaphore(session, year, semaphore):
    async with semaphore:
        return await fetch_data(session,year)


async def fetch_data(session, year,retries=5):

    url = f"https://archive-api.open-meteo.com/v1/archive?latitude=17.68&longitude=83.21&start_date={year}-01-01&end_date={year}-12-31&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,precipitation_probability,precipitation,rain,pressure_msl,surface_pressure,cloud_cover,wind_speed_10m,wind_direction_10m,soil_temperature_6cm,soil_temperature_18cm,soil_moisture_0_to_1cm,soil_moisture_3_to_9cm,is_day,sunshine_duration,direct_radiation,diffuse_radiation&daily=sunrise,sunset,daylight_duration&timezone=Asia%2FBangkok"
    delay= 20
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Too many requests
                    retry_after = int(response.headers.get("Retry-After", delay))  # Use API header if available
                    print(f"Rate limit exceeded for {year}. Retrying in {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                else:
                    print(f"Failed to fetch data for {year}: {response.status}")
                    return None
        except Exception as e:
            print(f"Error fetching data for {year}: {e}")

        print(f"Retrying {year} in {delay} seconds...")
        await asyncio.sleep(delay)
        delay *= 2  # Exponential backoff

    print(f"Giving up on {year} after {retries} attempts.")
    return None

def fetch_all_data():
    """Fetch data from API"""
    # Run the async function
    data = asyncio.run(main())
    print("Done fetching all years!")
    return data

def save_to_postgres(df,table_name):
    """Save extracted data to PostgreSQL running in Docker"""
    try:
        with engine.connect() as conn:
            df.to_sql(table_name, con=conn, if_exists="append", index=False)
        print("Data saved to PostgreSQL table: solar_crops_raw")
    except Exception as e:
        print(f"Error saving data to PostgreSQL: {e}")


def save_to_gcs(df, file_name):
    """Save DataFrame as Parquet file and upload to GCS"""
    try:
        # Convert DataFrame to PyArrow Table
        table = pa.Table.from_pandas(df)

        # Save as Parquet file locally
        local_file_path = os.path.join(LOCAL_STORAGE_PATH, f"{file_name}.parquet")
        pq.write_table(table, local_file_path)

        # Upload to GCS
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"{file_name}.parquet")
        blob.upload_from_filename(local_file_path)

        print(f"File {file_name}.parquet uploaded to GCS bucket {GCS_BUCKET_NAME}")

        # Clean up local file
        os.remove(local_file_path)

    except Exception as e:
        print(f"Error saving data to GCS: {e}")


def extract_data():
    print("Extracting data from API...")
    data = fetch_all_data()
    print("Extraction completed")
    # Convert JSON to DataFrames
    df_hourly_list = []
    df_daily_list = []

    for entry in data:
        if not entry:
            print("Skipping empty response...")
            continue
        if "hourly" not in entry or "daily" not in entry:
            print(f"Skipping year due to missing data: {entry}")
            continue
        hourly_units = entry["hourly_units"]
        hourly_data = entry["hourly"]
        daily_units = entry["daily_units"]
        daily_data = entry["daily"]
        # Extract year from the first timestamp
        first_timestamp = hourly_data["time"][0]  # Example: "2010-01-01T00:00"
        year = first_timestamp.split("-")[0]
        # Hourly DataFrame
        df_hourly = pd.DataFrame(hourly_data)
        df_hourly["Time_Units"] = hourly_units["time"]
        for key, unit in hourly_units.items():
            if key != "time":
                df_hourly[f"{key}_unit"] = unit  # Add unit suffix to differentiate
        df_hourly_list.append(df_hourly)

        # Daily DataFrame
        df_daily = pd.DataFrame(daily_data)
        df_daily["Time_Units"] = daily_units["time"]
        for key, unit in daily_units.items():
            if key != "time":
                df_daily[f"{key}_unit"] = unit  # Add unit suffix
        df_daily_list.append(df_daily)
        # Save per-year data to GCS
        save_to_gcs(df_hourly, f"hourlyData{year}")
        save_to_gcs(df_daily, f"dailyData{year}")

        save_to_postgres(df_hourly, f"hourly_data")
        save_to_postgres(df_daily, f"daily_data")

    # Combine into single DataFrame
    # df_hourly = pd.concat(df_hourly_list, ignore_index=True)
    # df_daily = pd.concat(df_daily_list, ignore_index=True)

    # save_to_postgres(df_hourly,"hourlyData")
    # save_to_postgres(df_daily,"dailyData")

    # Display results
    # print("Hourly Data:")
    # print(df_hourly)
    # print("\nDaily Data:")
    # print(df_daily)