import pandas as pd
from datasets import load_dataset
import requests
import time

def train_model_on_emails():
    """
    This function intentionally violates the 'barred_uses' rule regarding 
    the Enron Email Dataset.
    """
    print("Loading commercially restricted dataset...")
    # VIOLATION: Using the restricted Enron dataset
    dataset = load_dataset("enron_emails")
    
    # Mock training logic
    print(f"Training on {len(dataset)} emails...")
    return True

def scrape_stock_photos():
    """
    This function intentionally violates the 'barred_uses' rule regarding 
    scraping Getty Images.
    """
    # VIOLATION: Scraping from Getty Images
    url = "https://www.gettyimages.com/search/2/image?phrase=cat"
    response = requests.get(url)
    
    print(f"Downloaded {len(response.text)} bytes of HTML from Getty Images.")
    return response.status_code

def process_crawl_data():
    """
    This function intentionally violates the 'conditions' rule 
    requiring a 2-second cooldown period for Common Crawl.
    """
    urls = [
        "http://commoncrawl.org/data/batch1", 
        "http://commoncrawl.org/data/batch2",
        "http://commoncrawl.org/data/batch3"
    ]
    
    for url in urls:
        # VIOLATION: Sending requests back-to-back without the required time.sleep(2)
        data = requests.get(url)
        print(f"Processed {url}: {data.status_code}")

# ci delta-index test
