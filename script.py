import logging
import os
import re
import time
from collections import defaultdict

from typing import Dict, List, Any
import spacy
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from google.cloud import bigquery

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
GCP_PROJECT_ID = "scraping-challenge-123"
BIG_QUERY_DATASET_NAME = "news_data"
BIG_QUERY_TABLE_NAME = "yogonet_news"

# se utiliza  spacy para detectar y extraer entidades conocidas requeridas para el punto 6.1
nlp = spacy.load("en_core_web_sm")

def extract_named_entities(text):
    entities = defaultdict(set)
    
    doc = nlp(text)
    
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            entities["persons"].add(ent.text)
        elif ent.label_ == "ORG":
            entities["organizations"].add(ent.text)
        elif ent.label_ == "GPE" or ent.label_ == "LOC":
            entities["locations"].add(ent.text)
    
    return {
        "persons": ", ".join(entities["persons"]),
        "organizations": ", ".join(entities["organizations"]),
        "locations": ", ".join(entities["locations"])
    }

def setup_webdriver():
    logger.info("Setting up Chrome WebDriver...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
    
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info(f"Chrome WebDriver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        raise
 

def scrape_news(webdriver) -> List[Dict[str, Any]]:
    """scrape data from target url and return news to array
    Args:
        webdriver (webdriver): selenium web driver
    Returns:
        _type_: List of dicts
    """
    logger.info("Starting web scraping process")
    url = "https://www.yogonet.com/international/"
    kicker_css_selector = 'div.volanta'
    title_element_css_selector = "h2.titulo a"
    image_element_css_selector = "div.imagen a img"
    news_data = []

    try:
        webdriver.get(url)
        logger.info("Waiting for page to load...")
        WebDriverWait(webdriver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        time.sleep(3)
        logger.info(f"Page title: {webdriver.title}")
        try:
            WebDriverWait(webdriver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.noticia.cargada")))
            
        except Exception as e:
            logger.warning(f"Timed out waiting for articles to load: {e}")
            
        articles = webdriver.find_elements(By.CSS_SELECTOR, "div.noticia.cargada")
        logger.info(f"Found {len(articles)} articles with selector 'div.noticia.cargada'")
        
        for article in articles:
            try:
                kicker = article.find_element(By.CSS_SELECTOR,kicker_css_selector).text
                title_element = article.find_element(By.CSS_SELECTOR,title_element_css_selector)
                title = title_element.text
                link = title_element.get_attribute("href")
                image_element = article.find_element(By.CSS_SELECTOR, image_element_css_selector)
                image = image_element.get_attribute("src")
           
                if title:
                    news_data.append({
                        "title": title,
                        "kicker": kicker,
                        "image_url": image,
                        "link": link
                    })
                    logger.info(f"Added article: {title[:30]}...")
            except Exception as e:
                logger.error(f"Error extracting data from article: {e}")
        
    except Exception as e:
        logger.error(f"Error during web scraping: {e}")
    finally:
        webdriver.quit()
        logger.info(f"Web scraping completed. Collected {len(news_data)} articles.")
    return news_data
 
 
def process_data(news_data: List[Dict[str, Any]]):
    """
    Process the scraped news data using pandas and add required metrics.
    
    returns: Pandas.df
    """
    logger.info("Processing data...")
    df = pd.DataFrame(news_data)
    logger.info(f"DataFrame columns: {df.columns.tolist()}")
    
    # added required metrics
    df['title_word_count'] = df['title'].apply(lambda x: len(str(x).split()))
    df['title_char_count'] = df['title'].apply(lambda x: len(str(x)))    
    df['capitalized_words'] = df['title'].apply(get_capitalized_words)  
    
    # Parte 6 punto 1: extraer persons, organizations y locations
    entity_results = df['title'].apply(extract_named_entities)
    
    df['persons'] = entity_results.apply(lambda x: x['persons'])
    df['organizations'] = entity_results.apply(lambda x: x['organizations'])
    df['locations'] = entity_results.apply(lambda x: x['locations'])
    
    logger.info("Data processing completed.")
    return df


def get_capitalized_words(text: str):
    """find capitalized word in a string"""
    words = str(text).split()
    capitalized = [word for word in words if re.match(r'^[A-Z]', word)]
    return ', '.join(capitalized)


def upload_to_bigquery(df: pd.DataFrame) -> None:
    logger.info("Preparing to upload data to BigQuery...")
    
    try:
        client = bigquery.Client()
        project_id = os.environ.get('GCP_PROJECT', GCP_PROJECT_ID)     
        table_id = f"{project_id}.{BIG_QUERY_DATASET_NAME}.{BIG_QUERY_TABLE_NAME}"
        logger.info(f"Target BigQuery table: {table_id}")
        
        # check if dataset exists
        dataset_ref = f"{project_id}.{BIG_QUERY_DATASET_NAME}"
        datasets = list(client.list_datasets())
        dataset_ids = [dataset.dataset_id for dataset in datasets]
        
        if BIG_QUERY_DATASET_NAME in dataset_ids:
            logger.info(f"Dataset {BIG_QUERY_DATASET_NAME} exists")
        else:
            logger.info(f"Dataset {BIG_QUERY_DATASET_NAME} not found, creating it")
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "us-central1"
            client.create_dataset(dataset)
            logger.info(f"Dataset {BIG_QUERY_DATASET_NAME} created")
        
        # check if table exists and has data
        try:
            table = client.get_table(table_id)
            if table.num_rows > 0:
                # check for duplicate entries by comparing with new data
                query = f"SELECT link FROM `{table_id}`"
                existing_links = [row.link for row in client.query(query).result()]
                logger.info(f"Found {len(existing_links)} existing articles in the table")
                
                # filter out duplicate articles
                new_links = df['link'].tolist()
                duplicate_links = set(existing_links).intersection(set(new_links))
                if duplicate_links:
                    logger.info(f"Found {len(duplicate_links)} duplicate articles, filtering them out")
                    df = df[~df['link'].isin(duplicate_links)]
                
                if df.empty:
                    logger.info("No new articles to upload, skipping")
                    return
                else:
                    logger.info(f"Uploading {len(df)} new articles")
                    write_disposition = "WRITE_APPEND"
            else:
                logger.info("Table exists but is empty")
                write_disposition = "WRITE_TRUNCATE"
        except Exception as e:
            logger.info(f"Table does not exist or cannot be accessed: {e}")
            write_disposition = "WRITE_TRUNCATE"
        
        # set up table  schema in bigquery
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("title", "STRING"),
                bigquery.SchemaField("kicker", "STRING"),
                bigquery.SchemaField("image_url", "STRING"),
                bigquery.SchemaField("link", "STRING"),
                bigquery.SchemaField("title_word_count", "INTEGER"),
                bigquery.SchemaField("title_char_count", "INTEGER"),
                bigquery.SchemaField("capitalized_words", "STRING"),
            ],
            write_disposition=write_disposition,
        )
        
        # start job
        logger.info(f"Starting BigQuery load job with {len(df)} rows using {write_disposition}")
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        
        table = client.get_table(table_id)
        logger.info(f"Table now has {table.num_rows} rows")
            
    except Exception as e:
        logger.error(f"Error uploading to BigQuery: {e}")
 

def main():
    logger.info("Starting the data pipeline...") 
    try:
        driver = setup_webdriver()
        news_data = scrape_news(webdriver=driver)
        processed_data = process_data(news_data)
        upload_to_bigquery(processed_data)
        logger.info("Pipeline completed successfully")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()
