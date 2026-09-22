# src/config.py

import os

# Set paths for directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, 'processed')
EXTERNAL_DATA_DIR = os.path.join(DATA_DIR, 'external')
MODEL_DIR = os.path.join(BASE_DIR, 'outputs', 'model')
RESULTS_DIR = os.path.join(BASE_DIR, 'outputs', 'results')
LOGS_DIR = os.path.join(BASE_DIR, 'outputs', 'logs')
for _d in (RAW_DATA_DIR, PROCESSED_DATA_DIR, EXTERNAL_DATA_DIR, MODEL_DIR, RESULTS_DIR, LOGS_DIR):
    os.makedirs(_d, exist_ok=True)

# Hyperparameters for model training
HYPERPARAMETERS = {
    'learning_rate': 0.001,
    'batch_size': 32,
    'epochs': 100,
    'dropout_rate': 0.3,
    'optimizer': 'adam'
}

# Paths for configuration files
CONFIG_FILE_PATH = os.path.join(BASE_DIR, 'config.json')
LOG_FILE_PATH = os.path.join(LOGS_DIR, 'training.log')

# Model configurations
MODEL_CONFIG = {
    'input_dim': 64,  # Example input dimensions
    'hidden_layers': [128, 64],  # Example hidden layer architecture
    'output_dim': 1,  # For regression, or number of classes for classification
    'activation': 'relu'
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',  # Logging level (DEBUG, INFO, WARNING, ERROR)
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
}

# The cities the project reads, trains on and forecasts (name -> latitude, longitude)
CITIES = {
    'New Delhi': (28.61, 77.21), 'Jaipur': (26.91, 75.79), 'Lucknow': (26.85, 80.95),
    'Ahmedabad': (23.02, 72.57), 'Bhopal': (23.26, 77.41), 'Kolkata': (22.57, 88.36),
    'Nagpur': (21.15, 79.09), 'Mumbai': (19.08, 72.88), 'Pune': (18.52, 73.86),
    'Hyderabad': (17.39, 78.49), 'Chennai': (13.08, 80.27), 'Bengaluru': (12.97, 77.59),
}

# Other configurations
RANDOM_SEED = 42  # For reproducibility
TRAINING_SET_SIZE = 0.8  # 80% of data for training, 20% for validation

# API or external data sources (if applicable)
API_KEYS = {
    'weather_api': 'your-weather-api-key',
    'data_source_2': 'your-api-key-here'
}

# Whether to use GPU or CPU for training (set to True/False)
USE_GPU = True

# Add any additional project-specific configuration below
