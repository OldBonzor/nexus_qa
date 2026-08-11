# Use official Microsoft Playwright image with Python 3.10 pre-installed
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy project dependency definition
COPY requirements.txt .

# Install Python dependencies without caching to keep image lightweight
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Default command to run tests with Allure results export
CMD ["pytest", "--alluredir=allure-results"]