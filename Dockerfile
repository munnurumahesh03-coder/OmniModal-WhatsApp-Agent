# 1. Use the official Microsoft Playwright image (Contains all Linux browser dependencies)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy requirements first (Leverages Docker cache to build faster)
COPY requirements.txt .

# 4. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code into the container
COPY . .

# 6. Set environment variables for Python logging
ENV PYTHONUNBUFFERED=1

# 7. Command to run the continuous AI Agent
CMD ["python", "main.py"]
