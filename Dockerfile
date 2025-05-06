# Use the official Python image
FROM python:3.11-slim

# Set environment variables to avoid Python writing .pyc files
# and ensure output is sent directly to the terminal (useful for debugging)
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the local code to the working directory in the container
COPY . /app/

# Install dependencies from the requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your Flask app will run on
EXPOSE 5000

# Run the app using Gunicorn (recommended for production)
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000"]
