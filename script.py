import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
GCP_PROJECT_ID = "scraping-challenge-123"
BIG_QUERY_DATASET_NAME = "news_data"
BIG_QUERY_TABLE_NAME = "yogonet_news"


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
 

def scrape_news(webdriver: webdriver):
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
 

def main():
    logger.info("Starting the data pipeline...") 
    try:
        driver = setup_webdriver()
        news_data = scrape_news(webdriver=driver)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()
