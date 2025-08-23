import requests
import os
import csv
from urllib.parse import urlparse
from datetime import datetime
from utils import (
    get_cache_path,
    download_html,
    extract_domain_links,
    load_existing_links,
    save_new_links
)

LOG_DIR = "logs"

def get_csv_filename(domain):
    now = datetime.now()
    month_str = now.strftime("%Y-%m")
    month_dir = os.path.join(LOG_DIR, month_str)
    os.makedirs(month_dir, exist_ok=True)
    return os.path.join(month_dir, f"{domain}.csv")


def main(url):
    html = download_html(url)
    links = extract_domain_links(html, url)
    parsed = urlparse(url)
    domain = parsed.netloc
    os.makedirs(LOG_DIR, exist_ok=True)
    csv_filename = get_csv_filename(domain)
    existing_links = load_existing_links(csv_filename)
    new_links = [link for link in links if link not in existing_links]
    save_new_links(csv_filename, new_links)
    print(f"Total links found: {len(links)}")
    print(f"New links added: {len(new_links)}")
    print(f"Ignored (already existing): {len(links) - len(new_links)}")

def read_websites_csv(filename):
    websites = []
    if not os.path.exists(filename):
        print(f"Input file {filename} does not exist.")
        return websites
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) < 1:
                continue
            link = row[0].strip()
            city = row[1].strip() if len(row) > 1 else ""
            country = row[2].strip() if len(row) > 2 else ""
            websites.append((link, city, country))
    return websites

if __name__ == "__main__":
    input_csv = "websites.csv"
    websites = read_websites_csv(input_csv)
    if not websites:
        print("No websites to process.")
    for link, city, country in websites:
        print(f"Processing: {link} (City: {city}, Country: {country})")
        main(link)
