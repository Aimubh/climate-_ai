# scripts/generate_predictions.py

import os
import sys
import pandas as pd
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

def generate_predictions(model, X_data):
    """Generate predictions from the model"""
    try:
        predictions = model.predict(X_data)
        print(f"Predictions generated.")
        return predictions
    except Exception as e:
        print(f"Error generating predictions: {e}")
        sys.exit(1)

def save_predictions(predictions, output_path):
    """Save the predictions to a CSV file"""
    try:
        predictions_df = pd.DataFrame(predictions, columns=['Predictions'])
        predictions_df.to_csv(output_path, index=False)
        print(f"Predictions saved to {output_path}")
    except Exception as e:
        print(f"Error saving predictions: {e}")
        sys.exit(1)

def main():
    # Paths to the data and model
    model_path = os.path.join(MODEL_DIR, 'trained_model.pkl')  # Adjust the file name based on your model's format
    data_path = os.path.join(PROCESSED_DATA_DIR, 'processed_test_data.csv')  # Example data file
    output_path = os.path.join(RESULTS_DIR, 'predictions.csv')  # Path to save the predictions

    # Load the data
    data = load_data(data_path)
    
    # Preprocess the data (adjust preprocessing as needed)
    X = data.drop('target', axis=1)  # Assuming 'target' is the column to predict
    
    # Load the trained model
    try:
        model = load_model(model_path)  # load_model should load your trained model (e.g., using joblib or keras)
        print(f"Model loaded from {model_path}")
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    
    # Generate predictions
    predictions = generate_predictions(model, X)
    
    # Save the predictions
    save_predictions(predictions, output_path)

if __name__ == '__main__':
    main()
