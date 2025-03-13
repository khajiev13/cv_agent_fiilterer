FROM python:3.13.2-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .


# Install Python dependencies with prefer-binary to avoid compilation
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt


# Pre-download NLTK data with error handling
RUN python -m nltk.downloader -d /usr/local/share/nltk_data punkt punkt_tab wordnet stopwords averaged_perceptron_tagger averaged_perceptron_tagger_eng || \
    python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger_eng')"


# Copy the rest of the application
COPY . .

# Setup directories
RUN python setup_cv_directory.py

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]