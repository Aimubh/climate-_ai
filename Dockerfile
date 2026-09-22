# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port the app runs on (default for Flask is 5000)
EXPOSE 5000

# Command to run the application (adjust if you have a different start command)
CMD ["python", "-m", "scripts.train_model"]
