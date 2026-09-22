# scripts/train_model.py

import os
import sys
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingRegressor  # small on disk, fast, handles missing lags natively
from sklearn.metrics import mean_squared_error
from src.models.model import save_model  # Assuming save_model is defined in src/models/model.py
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

def train_model(X_train, y_train):
    """Train the model using the provided data"""
    try:
        model = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, random_state=42)
        model.fit(X_train, y_train)
        print("Model training completed.")
        return model
    except Exception as e:
        print(f"Error training the model: {e}")
        sys.exit(1)

def evaluate_model(model, X_test, y_test):
    """Evaluate the trained model using mean squared error"""
    try:
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        print(f"Model evaluation - MSE: {mse}")
        return mse
    except Exception as e:
        print(f"Error evaluating the model: {e}")
        sys.exit(1)

def main():
    # Paths to the data and model directories
    data_path = os.path.join(PROCESSED_DATA_DIR, 'processed_training_data.csv')  # Example data file
    model_path = os.path.join(MODEL_DIR, 'trained_model.pkl')  # Adjust file name as needed

    # Load data
    data = load_data(data_path)
    
    # Preprocess the data (adjust preprocessing as needed)
    X = data.drop('target', axis=1)  # Assuming 'target' is the column to predict
    y = data['target']

    # Split data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train the model
    model = train_model(X_train, y_train)

    # Evaluate the model
    mse = evaluate_model(model, X_test, y_test)
    
    # Save the trained model
    try:
        save_model(model, model_path)  # save_model should save the trained model (e.g., using joblib or pickle)
        print(f"Model saved to {model_path}")
    except Exception as e:
        print(f"Error saving the model: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
