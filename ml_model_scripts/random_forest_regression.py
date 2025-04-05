import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from google.cloud import bigquery
from pandas_gbq import to_gbq

def predict_rice_yield():
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
    w.year,
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
    w.year = c.year
    """

    df = pd.read_gbq(query, project_id=project_id)

    # ----------------------------------------
    # 3. Preprocessing
    # ----------------------------------------
    df.dropna(inplace=True)  # Optional: Drop missing rows

    X = df.drop(columns=['year', 'RICE_YIELD_Kg_per_ha'])
    y = df['RICE_YIELD_Kg_per_ha']

    # ----------------------------------------
    # 4. Train/Test Split
    # ----------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # ----------------------------------------
    # 5. Train Model
    # ----------------------------------------
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # ----------------------------------------
    # 6. Predict
    # ----------------------------------------
    y_pred = model.predict(X_test)

    # ----------------------------------------
    # 7. Evaluation
    # ----------------------------------------
    print("RMSE:", root_mean_squared_error(y_test, y_pred, squared=False))
    print("R² Score:", r2_score(y_test, y_pred))

    # ----------------------------------------
    # 8. Prepare result dataframe
    # ----------------------------------------
    df_results = X_test.copy()
    df_results['actual_yield'] = y_test.values
    df_results['predicted_yield'] = y_pred
    df_results.reset_index(inplace=True, drop=True)

    # Add year back for dashboard filters
    df_results = df_results.merge(df[['year']], left_index=True, right_index=True)

    # ----------------------------------------
    # 9. Upload predictions to BigQuery
    # ----------------------------------------
    to_gbq(df_results, f"{dataset}.{prediction_table}", project_id=project_id, if_exists='replace')
    print("Predictions uploaded to BigQuery table.")
