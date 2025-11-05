#!/usr/bin/env python3
"""
scrapy.py

Script to crawl "books.toscrape.com" website, extract book metadata
and export results to CSV in data/extracted_data.csv.

Features:
- Navigates through catalog pages (home page and paginated pages)
- Extracts title, price, rating, availability, category, image URL and product URL
- Maintains a list of extracted items and exports to CSV using pandas
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import urljoin
import os

class WebCrawler:
    """Simple crawler to extract book data from books.toscrape.com.

    Attributes:
        target_url (str): Base URL of the website to crawl
        client (requests.Session): Reusable HTTP session with headers
        items (list[dict]): List of dictionaries containing extracted data
    """

    def __init__(self, target_url="https://books.toscrape.com/"):
        self.target_url = target_url
        self.client = requests.Session()
        self.client.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.items = []
        
    def parse_rating(self, class_name):
        """Converts CSS rating class to integer (1-5).

        Args:
            class_name (str): Class name describing the rating (One, Two, ...)

        Returns:
            int: Rating value (0 if not identified)
        """
        ratings = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
        for key, value in ratings.items():
            if key in class_name:
                return value
        return 0
    
    def format_price(self, raw_price):
        """Removes symbols and converts price to float.

        Args:
            raw_price (str): Price text (e.g. '£51.77')

        Returns:
            float: Numeric price
        """
        return float(re.sub(r'[^\d.]', '', raw_price))
    
    def get_section(self, url):
        """Determines category/section from the given page.

        Tries to extract via breadcrumb; if that fails, tries page title;
        otherwise returns 'General'.

        Args:
            url (str): URL of the page to analyze

        Returns:
            str: Section/category name
        """
        try:
            response = self.client.get(url, timeout=10)
            response.raise_for_status()
            doc = BeautifulSoup(response.content, 'html.parser')
            
            nav = doc.find('ul', class_='breadcrumb')
            if nav:
                sections = nav.find_all('li')
                if len(sections) > 1:
                    return sections[-1].get_text(strip=True)
            
            page_title = doc.find('title')
            if page_title and 'Books to Scrape' in page_title.get_text():
                parts = page_title.get_text().split('|')
                if len(parts) > 1:
                    return parts[0].strip()
            
            return "General"
        except Exception as e:
            print(f"Error extracting section from {url}: {e}")
            return "General"
    
    def process_url(self, url):
        """Extracts all products from a page and adds them to self.items.

        Args:
            url (str): URL of the page containing product listings
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()
            doc = BeautifulSoup(response.content, 'html.parser')
            
            current_section = self.get_section(url)
            products = doc.find_all('article', class_='product_pod')
            
            for product in products:
                title_tag = product.find('h3').find('a')
                title = title_tag.get('title', title_tag.get_text(strip=True))
                
                product_url = urljoin(self.target_url, title_tag.get('href'))
                
                price_tag = product.find('p', class_='price_color')
                price = self.format_price(price_tag.get_text()) if price_tag else 0.0
                
                rating_tag = product.find('p', class_='star-rating')
                rating = 0
                if rating_tag:
                    rating_classes = rating_tag.get('class', [])
                    for cls in rating_classes:
                        if cls != 'star-rating':
                            rating = self.parse_rating(cls)
                            break
                
                img_container = product.find('div', class_='image_container').find('img')
                img_url = urljoin(self.target_url, img_container.get('src')) if img_container else ""
                
                stock = "In stock"
                stock_tag = product.find('p', class_='instock')
                if stock_tag:
                    stock = stock_tag.get_text(strip=True)
                elif product.find('p', class_='outofstock'):
                    stock = "Out of stock"
                
                item_data = {
                    'id': len(self.items) + 1,
                    'title': title,
                    'price': price,
                    'rating': rating,
                    'availability': stock,
                    'category': current_section,
                    'image_url': img_url,
                    'book_url': product_url
                }
                
                self.items.append(item_data)
                print(f"Extracted: {title} - Section: {current_section}")
                
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    def crawl(self):
        """Traverses catalog pages until no more products are found."""
        print("Starting crawl...")
        
        current_page = 1
        while True:
            if current_page == 1:
                url = self.target_url
            else:
                url = f"{self.target_url}catalogue/page-{current_page}.html"
            
            print(f"Processing page {current_page}...")
            
            try:
                response = self.client.get(url)
                response.raise_for_status()
                
                doc = BeautifulSoup(response.content, 'html.parser')
                products = doc.find_all('article', class_='product_pod')
                
                if not products:
                    print(f"No items found on page {current_page}. Finishing...")
                    break
                
                self.process_url(url)
                current_page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"Error accessing page {current_page}: {e}")
                break
        
        print(f"Crawl completed! Total items: {len(self.items)}")
    
    def export_data(self, filename="extracted_data.csv"):
        """Exports collected items to data/<filename> in CSV format.

        Args:
            filename (str): Output filename inside data folder
        """
        if not self.items:
            print("No data to export!")
            return
        
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        output_path = os.path.join(data_dir, filename)
        
        df = pd.DataFrame(self.items)
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        print(f"Total items: {len(df)}")

def run():
    """Helper function to run the crawler and export results."""
    crawler = WebCrawler()
    crawler.crawl()
    crawler.export_data()

if __name__ == "__main__":
    run()