import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from google.cloud import bigquery
from pandas_gbq import to_gbq

def predict_rice_yield():
    print("🔄 Starting rice yield prediction process...")

    # ----------------------------------------
    # 1. Set project and dataset info
    # ----------------------------------------
    project_id = "solarcropsanalysis-454507"
    dataset = "weatherData_SolarCropsAnalysis_1"
    prediction_table = "rice_yield_predictions"

    # ----------------------------------------
    # 2. Load data from BigQuery
    # ----------------------------------------
    query = f"""
    SELECT
      CAST(w.year AS INT64) AS year,
      w.avg_temp,
      w.total_rainfall,
      w.avg_humidity,
      w.total_gdd,
      w.avg_drought_index,
      c.RICE_AREA_1000_ha,
      c.RICE_PRODUCTION_1000_tons,
      c.RICE_YIELD_Kg_per_ha
    FROM
      `{project_id}.{dataset}.yearly_data` w
    JOIN
      `{project_id}.{dataset}.crop_data` c
    ON
      CAST(w.year AS INT64) = CAST(c.year AS INT64)
    """

    df = pd.read_gbq(query, project_id=project_id)
    print(f"✅ Loaded data: {df.shape[0]} rows")

    # ----------------------------------------
    # 3. Preprocessing
    # ----------------------------------------
    df.dropna(inplace=True)
    print(f"📉 After dropping NA: {df.shape[0]} rows")

    feature_cols = [
        'avg_temp', 'total_rainfall', 'avg_humidity',
        'total_gdd', 'avg_drought_index',
        'RICE_AREA_1000_ha', 'RICE_PRODUCTION_1000_tons'
    ]

    X = df[feature_cols]
    y = df['RICE_YIELD_Kg_per_ha']

    year = df['year']
    # ----------------------------------------
    # 4. Train/Test Split
    # ----------------------------------------
    X_train, X_test, y_train, y_test= train_test_split(
        X, y,  test_size=0.2, random_state=42
    )
    year_train, year_test = train_test_split(year, test_size=0.2, random_state=42)
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
