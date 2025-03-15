# Yogonet News Scraper

## Description

This project is a web scraper designed to extract news articles from [Yogonet International](https://www.yogonet.com/international/) - a gaming industry news website. The scraper collects article titles, kickers (subtitles), image URLs, and links, then processes this data and stores it in Google BigQuery for analysis.

## Architecture

The system uses:
- **Selenium** with Chrome WebDriver for web scraping
- **Pandas** for data processing
- **Google BigQuery** for data storage
- **Docker** for containerization
- **Google Cloud Run** for serverless execution



## Prerequisites

- Google Cloud Platform account with billing enabled
- gcloud CLI installed and configured
- Docker installed
- Python 3.9+ (for local development)

## Project Structure

```
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
├── script.py               # Main Python script
└── deploy-artifact.sh      # Deployment script
```

## Setup and Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/felipefritz/scrapter-test.git
cd scrapter-test
```

### 2. Configure Google Cloud Project

Make sure you have a Google Cloud project created and have set up appropriate permissions:

```bash
gcloud auth login
gcloud config set project {project_id} ( you need to create a project)
```

Enable required APIs:
```bash
gcloud services enable artifactregistry.googleapis.com run.googleapis.com bigquery.googleapis.com
```

### 3. Update Project ID
In `deploy.sh`, update the project ID to match your GCP project:
In `deploy.sh`, update the REGION to match your GCP REGION:

In `script.py`, update the project ID to match your GCP project:


### 4. Install Dependencies (for local testing)

```bash
pip install -r requirements.txt
```

### 5. Build and Deploy

Make the deployment script executable:
```bash
chmod +x deploy-artifact.sh
```

Run the deployment script:
```bash
./deploy-artifact.sh
```

The script will:
1. Create a Docker repository in Artifact Registry
2. Build the Docker image
3. Push the image to the repository
4. Create/update a Cloud Run job
5. Execute the job

### 6. View Results

After the job completes, you can check the data in BigQuery:

```bash
gcloud bq query --use_legacy_sql=false "SELECT * FROM {project_id}.news_data.yogonet_news LIMIT 10"
```

Or use the Google Cloud Console to view the data in BigQuery.

## Scheduled Execution

To run the scraper on a schedule, you can set up a Cloud Scheduler job:

```bash
gcloud scheduler jobs create http yogonet-scraper-daily \
  --schedule="0 8 * * *" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/YOUR_PROJECT_ID/jobs/scraping-job:run" \
  --http-method=POST \
  --oauth-service-account-email=YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

This sets up a daily job that runs at 8:00 AM.

## Local Testing

To test the script locally:

```bash
python script.py
```

Note: For local testing, you'll need to have Chrome and the appropriate version of ChromeDriver installed. You may also need to authenticate with Google Cloud for BigQuery access:

```bash
gcloud auth application-default login
```


1. Download the matching ChromeDriver from https://chromedriver.chromium.org/downloads

2. Alternatively, let the script handle driver management with webdriver-manager

### BigQuery Permissions

If you encounter BigQuery access issues, verify:

1. You have the necessary IAM permissions on the project
2. Your service account has bigquery.dataEditor and bigquery.jobUser roles
