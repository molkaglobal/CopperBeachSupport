# 🧩 Faire to Helm Sync Setup Guide

This document provides step-by-step instructions for setting up the **Faire to Helm Sync** project, including dependencies, Docker configuration, and environment variables.

---

## 📝 File #3: `requirements.txt`

**Purpose:**  
Lists all Python dependencies required for the project.

**Create a new file in VS Code:**  
`requirements.txt`

**Content:**
```txt
# ============================================================================
# FAIRE TO HELM SYNC - PYTHON DEPENDENCIES
# ============================================================================
#
# Install all dependencies with:
#   pip install -r requirements.txt
#
# For production deployment (Cloud Run):
#   These will be automatically installed via Dockerfile
#
# ============================================================================

# HTTP Requests Library
# Used for making API calls to Faire and Helm
requests==2.31.0

# Google Cloud Firestore
# Used for tracking last sync time between runs
google-cloud-firestore==2.14.0

# Python Environment Variables (for local development only)
# Loads .env file for testing
python-dotenv==1.0.0
```
✅ **Save the file.**

---

## 📝 File #4: `Dockerfile`

**Purpose:**  
Defines how to build a Docker container for Google Cloud Run deployment.

**Create a new file in VS Code:**  
`Dockerfile`

**Content:**
```dockerfile
# ============================================================================
# DOCKERFILE FOR FAIRE TO HELM SYNC
# ============================================================================
#
# This Dockerfile creates a container image for deploying the sync service
# to Google Cloud Run.
#
# Build command:
#   docker build -t gcr.io/PROJECT_ID/faire-helm-sync .
#
# Push to Google Container Registry:
#   docker push gcr.io/PROJECT_ID/faire-helm-sync
#
# ============================================================================

# Use official Python 3.11 slim image as base
# Slim version is smaller and more secure than full Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements file first (for Docker layer caching)
# This allows Docker to cache the pip install step if requirements don't change
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces image size by not caching pip packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application file
COPY faire_helm_sync.py .

# Set environment variables for Python
# PYTHONUNBUFFERED ensures logs are immediately flushed to stdout
ENV PYTHONUNBUFFERED=1

# Expose port (Cloud Run will set this automatically, but good practice to document)
EXPOSE 8080

# Run the sync script when container starts
CMD ["python", "faire_helm_sync.py"]
```
✅ **Save the file.**

---

## 📝 File #5: `.env.example`

**Purpose:**  
Template for your environment variables file (`.env`).  
The real `.env` file will include actual credentials and must **never** be committed to Git.

**Create a new file in VS Code:**  
`.env.example`

**Content:**
```bash
# ============================================================================
# FAIRE TO HELM SYNC - ENVIRONMENT VARIABLES TEMPLATE
# ============================================================================
#
# INSTRUCTIONS:
# 1. Copy this file to .env
# 2. Replace all placeholder values with your actual credentials
# 3. Never commit the .env file to Git (already in .gitignore)
#
# ============================================================================

# ----------------------------------------------------------------------------
# FAIRE API CREDENTIALS
# ----------------------------------------------------------------------------
# Get your Faire API token from:
# https://faire.com → Settings → Integrations → API
# Token format: faire_xxxxxxxxxxxxxxxxxx

FAIRE_API_TOKEN=faire_your_actual_token_here

# ----------------------------------------------------------------------------
# HELM API CREDENTIALS
# ----------------------------------------------------------------------------
# Your Helm domain (without https://)
# Example: ocelotchocolate.myhelm.app

HELM_DOMAIN=yourclient.myhelm.app

# Your Helm API Bearer Token
# Get from Helm → Settings → API

HELM_API_TOKEN=your_actual_bearer_token_here

# The manual channel ID for Faire orders in Helm
# Usually this is "1" but check with your Helm setup
# This tells Helm which sales channel these orders came from

HELM_MANUAL_CHANNEL_ID=1

# ----------------------------------------------------------------------------
# OPTIONAL: GOOGLE CLOUD PROJECT (for Firestore)
# ----------------------------------------------------------------------------
# Only needed if you have multiple Google Cloud projects
# The project ID where your Firestore database is located

# GOOGLE_CLOUD_PROJECT=your-project-id

# ----------------------------------------------------------------------------
# NOTES
# ----------------------------------------------------------------------------
# - The .env file is ignored by Git (see .gitignore)
# - Never share your .env file or commit it to version control
# - When deploying to Cloud Run, use environment variables instead
# - Test your credentials with: python test_faire_helm.py
# ============================================================================
```
✅ **Save the file.**

---

## ✅ Final Project File List

| File | Description |
|------|--------------|
| `faire_helm_sync.py` | Main sync script |
| `test_faire_helm.py` | Test script |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container configuration |
| `.env.example` | Template for credentials |

---

## 🎯 Next Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Your `.env` File
```bash
# Copy the template
cp .env.example .env

# Then edit .env with your real credentials
```

### 3. Test in Mock Mode (No Credentials Needed)
```bash
python faire_helm_sync.py --test
python test_faire_helm.py --mock
```

### 4. Once You Have Real Credentials
```bash
# Test connections
python test_faire_helm.py

# Run actual sync
python faire_helm_sync.py
```

---

## 📤 Commit to Git

```bash
cd ~/OneDrive\ -\ Copper\ Beech\ Trading/faire-helm-sync

# Add all files (except .env which is in .gitignore)
git add .

# Commit
git commit -m "Add all Faire to Helm sync files with full documentation"

# Push
git push
```

---

✅ **All setup files created successfully!**  
You’re now ready to deploy the Faire-to-Helm Sync project.
