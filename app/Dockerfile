# Use the official Python image as the base image
FROM python:3

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install required packages
RUN pip install Flask gunicorn

# Expose port 8000 (adjust this if you want to use a different port)
EXPOSE 8000

# Command to run the Gunicorn server with 4 worker processes
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8000", "-w", "4"]
