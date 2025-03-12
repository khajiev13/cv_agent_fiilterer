FROM python:3.13.2-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

#RUN install essentials
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential 

# Install Python dependencies with prefer-binary to avoid compilation
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy the rest of the application
COPY . .

# Setup directories
RUN python setup_cv_directory.py

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]