import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from google.cloud import bigquery
from pandas_gbq import to_gbq
import os

def predict_rice_yield():
    print("🔄 Starting rice yield prediction process...")

    # ----------------------------------------
    # 1. Set project and dataset info
    # ----------------------------------------
    # Access environment variables
    project_id = os.getenv("PROJECT_ID")
    dataset = os.getenv("BIGQUERY_DATASET")
    prediction_table = os.getenv("PREDICTION_TABLE")
    daily_data = os.getenv("DAILY_TABLE")
    crop_yearly_data = os.getenv("CROP_DATA_TABLE")

    # ----------------------------------------
    # 2. Load data from BigQuery
    # ----------------------------------------
    query = f"""
    SELECT
      CAST(year AS INT64) AS year,
      CAST(month AS INT64) AS month,
      temperature_2m,
      max_temperature,
      min_temperature,
      relative_humidity_2m,
      precipitation,
      sunshine_duration,
      direct_radiation,
      diffuse_radiation,
      soil_temperature_6cm,
      wind_speed_10m,
      GDD,
      heat_stress,
      soil_moisture_index,
      drought_index,
      total_solar_radiation,
      radiation_efficiency
    FROM
      `{project_id}.{dataset}.{daily_data}` 
    """

    df = pd.read_gbq(query, project_id=project_id)
    print(f"✅ Loaded data: {df.shape[0]} rows")

    query = f"""
    SELECT
      year, 
      RICE_AREA_1000_ha,
      RICE_PRODUCTION_1000_tons,
      RICE_YIELD_Kg_per_ha
    FROM
      `{project_id}.{dataset}.{crop_yearly_data}` 
    """
    crop_data = pd.read_gbq(query, project_id=project_id)
    print(f"✅ Loaded data: {crop_data.shape[0]} rows")

    # Filter data for June to November (Rice growing season)
    season_df = df[df['month'].between(6, 11)]

    # Aggregate data by year and month to create seasonal features (mean, max, std, etc.)
    seasonal_features = season_df.groupby('year').agg(
        avg_temp=('temperature_2m', 'mean'),
        max_temp=('max_temperature', 'max'),
        min_temp=('min_temperature', 'min'),
        total_rainfall=('precipitation', 'sum'),
        avg_radiation=('direct_radiation', 'mean'),
        max_radiation=('direct_radiation', 'max'),
        avg_drought_index=('drought_index', 'mean'),
        total_gdd=('GDD', 'sum'),
        max_gdd=('GDD', 'max'),
        heat_stress_days=('heat_stress', 'sum'),  # Define heat stress based on a threshold, e.g., 35°C
        soil_moisture_index=('soil_moisture_index', 'mean'),
        rainfall_variability=('precipitation', 'std')
    ).reset_index()

    # print(len(seasonal_features))
    # print(seasonal_features)
    # print(crop_data)
    # Now merge with crop data for prediction
    df = pd.merge(seasonal_features, crop_data, on='year')
    # ----------------------------------------
    # 3. Preprocessing
    # ----------------------------------------

    feature_cols = [
      'avg_temp', 'max_temp', 'min_temp', 'total_rainfall',
      'avg_radiation', 'max_radiation', 'avg_drought_index',
      'total_gdd', 'max_gdd', 'heat_stress_days', 'soil_moisture_index',
      'rainfall_variability', 'RICE_AREA_1000_ha', 'RICE_PRODUCTION_1000_tons'
    ]
    X = df[feature_cols]
    y = df['RICE_YIELD_Kg_per_ha']
    year = df['year']
    # print(" after x y year transformation")
    # print(len(X))
    # print(len(y))
    # print(len(year))
    # print(X)
    # print(y)
    # print(year)
    # ----------------------------------------
    # 4. Train/Test Split
    # ----------------------------------------
    
    X_train, X_test, y_train, y_test, year_train, year_test = train_test_split(
        X, y, year, test_size=0.2, random_state=42
    )

    # ----------------------------------------
    # 5. Train Model
    # ----------------------------------------
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    print("✅ Model trained")

    # ----------------------------------------
    # 6. Predict and Evaluate
    # ----------------------------------------
    y_pred = model.predict(X_test)

    # rmse = mean_squared_error(y_test, y_pred, squared=False)
    # r2 = r2_score(y_test, y_pred)
    # print(f"📊 RMSE: {rmse:.2f}, R² Score: {r2:.2f}")

    # ----------------------------------------
    # 7. Prepare result DataFrame
    # ----------------------------------------
    df_results = X_test.copy()
    df_results['actual_yield'] = y_test.values
    df_results['predicted_yield'] = y_pred
    df_results['year'] = year_test.values
    df_results.reset_index(drop=True, inplace=True)

    # ----------------------------------------
    # 8. Upload to BigQuery
    # ----------------------------------------
    to_gbq(
        df_results,
        destination_table=f"{dataset}.{prediction_table}",
        project_id=project_id,
        if_exists="replace"  # change to "append" if needed
    )
    print("🚀 Predictions uploaded to BigQuery.")