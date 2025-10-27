# Faire to Helm Order Synchronization

Automatically synchronize wholesale orders from Faire to Helm order management system.

## 📋 Overview

This integration automatically pulls new orders from Faire's wholesale platform and creates them in Helm, eliminating manual data entry and reducing errors.

### Features

- ✅ Automatic order synchronization every 15 minutes
- ✅ Transforms Faire order format to Helm format
- ✅ Tracks sync state to prevent duplicates
- ✅ Comprehensive logging and error handling
- ✅ Test mode for safe testing without API credentials
- ✅ Production-ready for Google Cloud Run deployment

### What Gets Synced

- Order header (dates, totals, status)
- Customer/retailer information
- Shipping and billing addresses
- Line items with SKUs, quantities, and prices
- Order notes and metadata

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Faire Brand API token
- Helm API credentials
- Google Cloud account (for production deployment)

### Installation

1. **Clone or download this repository**
```bash
cd ~/OneDrive\ -\ Copper\ Beech\ Trading/faire-helm-sync
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure credentials**

Copy the example environment file and add your credentials:
```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:
```bash
FAIRE_API_TOKEN=faire_your_actual_token
HELM_DOMAIN=yourclient.myhelm.app
HELM_API_TOKEN=your_bearer_token
HELM_MANUAL_CHANNEL_ID=1
```

4. **Test the integration**
```bash
# Test without API credentials (mock mode)
python test_faire_helm.py --mock

# Test with real credentials
python test_faire_helm.py
```

5. **Run the sync**
```bash
# Test mode (uses mock data)
python faire_helm_sync.py --test

# Production mode (syncs real orders)
python faire_helm_sync.py
```

---

## 📖 Detailed Setup Guide

### Getting Faire API Credentials

1. Log into your Faire account at https://faire.com
2. Navigate to **Settings** → **Integrations** → **API**
3. Click **"Generate API Token"** under Brand API
4. Copy the token (starts with `faire_`)
5. Add to your `.env` file as `FAIRE_API_TOKEN`

### Getting Helm API Credentials

1. Log into your Helm account
2. Navigate to **Settings** → **API** (or ask your Helm administrator)
3. Copy your **domain** (e.g., `client.myhelm.app`)
4. Copy your **Bearer Token**
5. Add both to your `.env` file

### Manual Channel ID

The `HELM_MANUAL_CHANNEL_ID` identifies where these orders came from in Helm. This is usually `1` but check your Helm settings under Sales Channels. Ask your Helm administrator if unsure.

---

## 🧪 Testing

### Test Without Credentials (Mock Mode)

Perfect for verifying the code works before you have API access:
```bash
# Test sync with mock data
python faire_helm_sync.py --test

# Test API connections with mock responses
python test_faire_helm.py --mock
```

### Test With Real Credentials

Once you have API credentials configured:
```bash
# Test API connections
python test_faire_helm.py
```

This will:
- ✅ Verify Faire API connection
- ✅ Verify Helm API connection
- ✅ Test data transformation
- ✅ Optionally create a test order in Helm

### Manual Testing

To manually sync orders once:
```bash
python faire_helm_sync.py
```

Check the log file for details:
```bash
cat faire_helm_sync.log
```

---

## 🚀 Production Deployment (Google Cloud Run)

### Prerequisites

- Google Cloud project with billing enabled
- Google Cloud SDK installed (`gcloud` command)
- Docker installed

### Step 1: Setup Google Cloud
```bash
# Set your project ID
export PROJECT_ID=your-gcloud-project-id

# Configure gcloud
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable firestore.googleapis.com
```

### Step 2: Create Firestore Database
```bash
# Create Firestore database (for tracking sync state)
gcloud firestore databases create --location=europe-west2
```

### Step 3: Build and Deploy
```bash
# Build Docker image
docker build -t gcr.io/$PROJECT_ID/faire-helm-sync .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/faire-helm-sync

# Deploy to Cloud Run
gcloud run deploy faire-helm-sync \
  --image gcr.io/$PROJECT_ID/faire-helm-sync \
  --platform managed \
  --region europe-west2 \
  --no-allow-unauthenticated \
  --set-env-vars FAIRE_API_TOKEN=your_faire_token,HELM_DOMAIN=client.myhelm.app,HELM_API_TOKEN=your_helm_token,HELM_MANUAL_CHANNEL_ID=1 \
  --memory 512Mi \
  --timeout 540 \
  --max-instances 1
```

**⚠️ IMPORTANT:** Replace the environment variable values with your actual credentials!

### Step 4: Set Up Automatic Scheduling (Every 15 Minutes)
```bash
# Get the Cloud Run service URL
SERVICE_URL=$(gcloud run services describe faire-helm-sync \
  --region europe-west2 \
  --format 'value(status.url)')

# Create Cloud Scheduler job
gcloud scheduler jobs create http faire-helm-sync-job \
  --location europe-west2 \
  --schedule "*/15 * * * *" \
  --uri "${SERVICE_URL}" \
  --http-method POST \
  --oidc-service-account-email $(gcloud config get-value account) \
  --time-zone "Europe/London"
```

This creates a scheduled job that runs every 15 minutes.

### Step 5: Verify Deployment
```bash
# Check Cloud Run service status
gcloud run services describe faire-helm-sync --region europe-west2

# Check Cloud Scheduler job
gcloud scheduler jobs describe faire-helm-sync-job --location europe-west2

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=faire-helm-sync" --limit 50
```

---

## 📊 Monitoring

### View Logs

**In Google Cloud Console:**
1. Navigate to Cloud Run → faire-helm-sync → Logs
2. Look for:
   - `[SUCCESS]` messages for successful syncs
   - `[ERROR]` messages for failures
   - Order counts and processing details

**Using gcloud:**
```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=faire-helm-sync" \
  --limit 50 \
  --format json

# Follow logs in real-time
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=faire-helm-sync"
```

### Check Scheduler Status
```bash
# List all scheduled jobs
gcloud scheduler jobs list --location europe-west2

# View job details
gcloud scheduler jobs describe faire-helm-sync-job --location europe-west2

# View job execution history
gcloud scheduler jobs describe faire-helm-sync-job --location europe-west2 --format="value(status.lastAttemptTime, status.lastAttemptSuccess)"
```

### Trigger Manual Sync
```bash
# Manually trigger the scheduled job
gcloud scheduler jobs run faire-helm-sync-job --location europe-west2
```

---

## 🔧 Maintenance

### Pause Synchronization
```bash
# Pause the scheduler
gcloud scheduler jobs pause faire-helm-sync-job --location europe-west2
```

### Resume Synchronization
```bash
# Resume the scheduler
gcloud scheduler jobs resume faire-helm-sync-job --location europe-west2
```

### Update Environment Variables
```bash
# Update Cloud Run service with new credentials
gcloud run services update faire-helm-sync \
  --region europe-west2 \
  --set-env-vars FAIRE_API_TOKEN=new_token
```

### Redeploy After Code Changes
```bash
# Rebuild and push
docker build -t gcr.io/$PROJECT_ID/faire-helm-sync .
docker push gcr.io/$PROJECT_ID/faire-helm-sync

# Update Cloud Run service
gcloud run deploy faire-helm-sync \
  --image gcr.io/$PROJECT_ID/faire-helm-sync \
  --region europe-west2
```

---

## 🐛 Troubleshooting

### Orders Not Syncing

**Check 1: Verify Scheduler is Running**
```bash
gcloud scheduler jobs list --location europe-west2
```
Status should be `ENABLED`.

**Check 2: View Recent Logs**
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit 20
```
Look for error messages.

**Check 3: Test APIs Manually**
```bash
# Test Faire API
curl -H "X-FAIRE-ACCESS-TOKEN: your_token" \
  https://www.faire.com/external-api/v2/orders?limit=1

# Test Helm API
curl -H "Authorization: Bearer your_token" \
  https://yourclient.myhelm.app/public-api/orders?page=1
```

### Common Error Messages

**"Missing required environment variables"**
- Solution: Ensure all environment variables are set in Cloud Run

**"[ERROR] Faire API HTTP error: 401"**
- Solution: Faire API token is invalid or expired. Generate a new token.

**"[ERROR] Helm API HTTP error: 401"**
- Solution: Helm Bearer token is invalid. Get a new token from Helm.

**"[ERROR] Faire API HTTP error: 403"**
- Solution: API token doesn't have the required permissions.

**"[ERROR] Failed to create order: HTTP 404"**
- Solution: Check `HELM_DOMAIN` is correct (no https://, no trailing slash)

### Reset Sync State

If you need to re-sync all orders:
```bash
# Delete the Firestore document that tracks last sync
gcloud firestore databases documents delete \
  "faire_sync/last_sync" \
  --database="(default)"
```

Next sync will start from 7 days ago.

---

## 💰 Cost Estimate

Running on Google Cloud Run is very cost-effective:

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| Cloud Run | ~2,880 executions/month (every 15 min) | **FREE** (within free tier) |
| Firestore | ~5,760 operations/month | **FREE** (within free tier) |
| Cloud Scheduler | 1 job | **FREE** (3 jobs free tier) |
| **Total** | | **~$0-2/month** |

Google Cloud provides:
- 2 million Cloud Run requests/month free
- 50K Firestore reads + 20K writes/day free
- 3 Cloud Scheduler jobs free

This integration uses well within these limits.

---

## 📁 Project Structure
```
faire-helm-sync/
├── faire_helm_sync.py      # Main sync script
├── test_faire_helm.py      # Test script for API connections
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── .env                   # Your credentials (not committed to Git)
├── .env.example           # Template for credentials
├── .gitignore            # Git ignore rules
├── README.md             # This file
└── faire_helm_sync.log   # Log file (generated when running)
```

---

## 🔒 Security Best Practices

### Protect Your Credentials

1. **Never commit `.env` to Git** (already in `.gitignore`)
2. **Use environment variables in production** (not hardcoded values)
3. **Rotate API tokens regularly** (every 90 days recommended)
4. **Use least-privilege service accounts** for Cloud Run
5. **Enable audit logging** in Google Cloud Console

### Secure Your Deployment
```bash
# Restrict Cloud Run to specific service account
gcloud iam service-accounts create faire-helm-sync \
  --display-name="Faire Helm Sync Service Account"

# Deploy with specific service account
gcloud run deploy faire-helm-sync \
  --service-account faire-helm-sync@$PROJECT_ID.iam.gserviceaccount.com
```

---

## 🤝 Support

### Getting Help

1. **Check logs first:**
```bash
   cat faire_helm_sync.log
```

2. **Test connections:**
```bash
   python test_faire_helm.py
```

3. **Run in test mode:**
```bash
   python faire_helm_sync.py --test
```

4. **Contact:** Copper Beech Support

### Reporting Issues

When reporting issues, include:
- Error messages from logs
- Output from test script
- Faire and Helm API response codes
- Steps to reproduce the problem

---

## 📝 Change Log

### Version 1.0 (2025-10-26)
- Initial release
- Faire API v2 integration
- Helm API integration
- Firestore sync state tracking
- Cloud Run deployment support
- Comprehensive test suite
- Full documentation

---

## 📄 License

Copyright © 2025 Copper Beech Trading

This software is proprietary and confidential.

---

## 🙏 Acknowledgments

- **Faire API Documentation:** https://faire.github.io/external-api-docs/
- **Helm API Documentation:** Provided by client
- **Google Cloud Documentation:** https://cloud.google.com/run/docs

---

**Last Updated:** 2025-10-26  
**Version:** 1.0  
**Author:** Copper Beech Support