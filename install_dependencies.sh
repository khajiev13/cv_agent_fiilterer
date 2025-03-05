#!/bin/bash

echo "Installing required dependencies for Resume Agent..."

pip install --upgrade pip
pip install -r requirements.txt

echo "Setting up necessary directories..."
python setup_cv_directory.py

echo "Installation complete!"
