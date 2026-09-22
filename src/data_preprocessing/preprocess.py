import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler

# Open-Meteo daily field -> our column name. The archive (history) and forecast (live) APIs both serve these.
DAILY_FIELDS = {
    'temperature_2m_max': 'tmax', 'temperature_2m_min': 'tmin', 'temperature_2m_mean': 'tmean',
    'relative_humidity_2m_mean': 'rh', 'precipitation_sum': 'rain', 'wind_speed_10m_max': 'wind',
    'wind_direction_10m_dominant': 'wdir', 'surface_pressure_mean': 'pres',
}
# The model's input columns, in order. Training and live scoring both use exactly this list.
FEATURES = ['lat', 'lon', 'doy_sin', 'doy_cos', 'tmax', 'tmin', 'tmean', 'rh', 'rain', 'wind', 'wdir_sin', 'wdir_cos',
            'pres', 'tmax_lag1', 'tmax_lag2', 'tmax_lag3', 'rain_lag1', 'tmax_delta1', 'pres_delta1']


def make_features(df):
    """Build the model's features from one row per city and day.

    Args:
        df (pd.DataFrame): columns city, lat, lon, date (YYYY-MM-DD) and the DAILY_FIELDS columns.

    Returns:
        pd.DataFrame: the same rows, sorted by city and date, with FEATURES filled and
        target = the next day's tmax (NaN on each city's last day). Lags are NaN on the first
        days of each city; HistGradientBoosting handles NaN natively.
    """
    df = df.sort_values(['city', 'date']).copy()
    doy = pd.to_datetime(df['date']).dt.dayofyear
    df['doy_sin'], df['doy_cos'] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    rad = np.radians(df['wdir'].astype(float))
    df['wdir_sin'], df['wdir_cos'] = np.sin(rad), np.cos(rad)
    g = df.groupby('city')
    for k in (1, 2, 3):
        df[f'tmax_lag{k}'] = g['tmax'].shift(k)
    df['rain_lag1'] = g['rain'].shift(1)
    df['tmax_delta1'] = df['tmax'] - df['tmax_lag1']
    df['pres_delta1'] = df['pres'] - g['pres'].shift(1)
    df['target'] = g['tmax'].shift(-1)
    return df
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split

def clean_data(df):
    """
    Perform basic data cleaning tasks such as removing duplicates,
    handling missing values, and ensuring data types are consistent.

    Args:
        df (pd.DataFrame): The raw data to clean.

    Returns:
        pd.DataFrame: The cleaned data.
    """
    # Remove duplicates
    df = df.drop_duplicates()

    # Handle missing values
    df = handle_missing_values(df)

    # Convert date column to datetime (if exists)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Drop rows with invalid or NaT dates
    df = df.dropna(subset=['date'])

    return df

def handle_missing_values(df):
    """
    Handle missing values in the dataset using SimpleImputer.

    Args:
        df (pd.DataFrame): The data to process.

    Returns:
        pd.DataFrame: The data with imputed missing values.
    """
    imputer = SimpleImputer(strategy='mean')  # Using mean imputation
    for column in df.columns:
        if df[column].dtype in ['float64', 'int64']:  # Only impute numerical columns
            df[column] = imputer.fit_transform(df[[column]])

    return df

def transform_features(df):
    """
    Perform feature engineering, such as creating new features
    or transforming existing ones.

    Args:
        df (pd.DataFrame): The data to process.

    Returns:
        pd.DataFrame: The data with transformed features.
    """
    # Example: Adding a new feature based on existing columns
    if 'temperature' in df.columns and 'precipitation' in df.columns:
        df['temp_precipitation_ratio'] = df['temperature'] / (df['precipitation'] + 1)  # Avoid division by zero

    return df

def scale_data(df, scaling_method='standard'):
    """
    Scale the numerical features of the dataset using the chosen scaling method.

    Args:
        df (pd.DataFrame): The data to scale.
        scaling_method (str): The scaling method ('standard' or 'minmax').

    Returns:
        pd.DataFrame: The scaled data.
    """
    scaler = None

    # Select the scaling method
    if scaling_method == 'standard':
        scaler = StandardScaler()
    elif scaling_method == 'minmax':
        scaler = MinMaxScaler()

    # Apply scaling only to numerical columns
    numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
    df[numerical_cols] = scaler.fit_transform(df[numerical_cols])

    return df

def split_data(df, test_size=0.2, random_state=42):
    """
    Split the dataset into training and testing sets.

    Args:
        df (pd.DataFrame): The data to split.
        test_size (float): The proportion of data to include in the test set.
        random_state (int): Random state for reproducibility.

    Returns:
        tuple: (X_train, X_test, y_train, y_test)
    """
    # Assuming the target variable is 'target', change it if necessary
    if 'target' not in df.columns:
        raise ValueError("'target' column not found in the dataframe.")

    X = df.drop('target', axis=1)
    y = df['target']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    return X_train, X_test, y_train, y_test
