# Use the official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# Set the working directory in the container
WORKDIR /app

# Copy the application code to the working directory
COPY . /app/

# Create the instance folder (for SQLite database)
RUN mkdir -p /app/instance

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app will run on
EXPOSE 5000

# Start the app using Gunicorn
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000"]
