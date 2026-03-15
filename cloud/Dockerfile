# Use an official lightweight Python image.
FROM python:3.11-slim

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Cloud Run injects the PORT environment variable.
# Our server.py is already set up to read it.
ENV PORT=8080

# Run the web service on container startup
CMD ["python", "server.py"]