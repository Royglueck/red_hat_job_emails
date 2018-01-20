This script uses Scrapy to crawl Red Hat's jobs site for any new jobs and then sends them to a nominated email address. It runs as a serverless function in AWS every hour.

### Deploying
1. Add your email address and password to `scraper.py` and `main.tf`.
2. Add your AWS access and secret keys to `main.tf`.
2. Run `deploy.sh` to deploy it to AWS Lambda!
