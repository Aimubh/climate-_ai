# scripts/evaluate_model.py

import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from src.models.model import load_model  # Assuming load_model is defined in src/models/model.py
from src.config import RESULTS_DIR, MODEL_DIR, PROCESSED_DATA_DIR
import joblib

def load_data(data_path):
    """Load dataset from the given path"""
    try:
        data = pd.read_csv(data_path)
        print(f"Data loaded from {data_path}")
        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

def evaluate_model(model, X_test, y_test):
    """Evaluate the model using mean squared error and R2 score"""
    # Predict the results
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    return mse, r2

def main():
    # Paths to the data and model
    model_path = os.path.join(MODEL_DIR, 'trained_model.pkl')  # Adjust the file name based on your model's format
    data_path = os.path.join(PROCESSED_DATA_DIR, 'processed_test_data.csv')  # Example data file

    # Load data
    data = load_data(data_path)
    
    # Preprocess the data (adjust preprocessing as needed)
    X = data.drop('target', axis=1)  # Assuming 'target' is the column to predict
    y = data['target']

    # Split data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Load the trained model
    try:
        model = load_model(model_path)  # load_model should load your trained model (e.g., using joblib or keras)
        print(f"Model loaded from {model_path}")
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    
    # Evaluate the model
    mse, r2 = evaluate_model(model, X_test, y_test)

    # Print evaluation results
    print(f"Model Evaluation Results:")
    print(f"Mean Squared Error (MSE): {mse}")
    print(f"R2 Score: {r2}")

    # Optionally, save evaluation results to a file
    evaluation_results = {
        'MSE': mse,
        'R2': r2
    }
    results_df = pd.DataFrame([evaluation_results])
    results_df.to_csv(os.path.join(RESULTS_DIR, 'evaluation_results.csv'), index=False)

if __name__ == '__main__':
    main()
