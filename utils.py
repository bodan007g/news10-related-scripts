import os
import re
import requests
import csv
from urllib.parse import urlparse, urljoin
from datetime import datetime

CACHE_DIR = "cache"

def get_cache_path(url):
    parsed = urlparse(url)
    filename = parsed.netloc.replace('.', '_') + ".html"
    return os.path.join(CACHE_DIR, filename)

def download_html(url):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = get_cache_path(url)
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()
    response = requests.get(url)
    response.raise_for_status()
    html = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html

def extract_domain_links(html, base_url):
    parsed_base = urlparse(base_url)
    domain = parsed_base.netloc
    links = set()
    for match in re.findall(r'<a [^>]*href=["\"](.*?)["\"]', html, re.IGNORECASE):
        full_url = urljoin(base_url, match)
        parsed_link = urlparse(full_url)
        if parsed_link.netloc == domain:
            path = parsed_link.path
            if parsed_link.query:
                path += '?' + parsed_link.query
            if parsed_link.fragment:
                path += '#' + parsed_link.fragment
            links.add(path)
    return sorted(links)

def load_existing_links(csv_path):
    existing = set()
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    existing.add(row[1])
    return existing

def save_new_links(csv_path, new_links):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m%d: %H:%M")
    try:
        with open(csv_path, "a", encoding="utf-8", newline='') as f:
            writer = csv.writer(f)
            for link in new_links:
                writer.writerow([timestamp, link])
    except Exception as e:
        print(f"Error writing to log file {csv_path}: {e}")

# Helper function to get HTML content for a given link
def get_html_content(link):
    """
    Downloads and returns the HTML content for the given link.
    Raises requests.RequestException if the request fails.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    response = requests.get(link, headers=headers)
    response.raise_for_status()
    return response.text