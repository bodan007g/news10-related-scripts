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
CACHE_DIR = "cache"

def get_cache_path(url):
    parsed = urlparse(url)
    filename = parsed.netloc.replace('.', '_') + ".html"
    return os.path.join(CACHE_DIR, filename)

def is_cache_fresh(cache_path, threshold_minutes=5):
    if not os.path.exists(cache_path):
        return False
    mtime = os.path.getmtime(cache_path)
    age = (datetime.now() - datetime.fromtimestamp(mtime)).total_seconds() / 60.0
    return age < threshold_minutes

def get_csv_filename(domain):
    now = datetime.now()
    month_str = now.strftime("%Y-%m")
    month_dir = os.path.join(LOG_DIR, month_str)
    os.makedirs(month_dir, exist_ok=True)
    return os.path.join(month_dir, f"{domain}.csv")


def download_html(url, cache_threshold_minutes=5):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = get_cache_path(url)
    if is_cache_fresh(cache_path, cache_threshold_minutes):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()
    response = requests.get(url)
    response.raise_for_status()
    html = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html

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
    return len(links), len(new_links), len(links) - len(new_links)

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
    import time
    input_csv = "websites.csv"
    websites = read_websites_csv(input_csv)
    if not websites:
        print("No websites to process.")
    start_time = time.time()
    # Collect new links per domain for summary log
    new_links_summary = {}
    for link, city, country in websites:
        parsed = urlparse(link)
        domain = parsed.netloc
        total, added, _ = main(link)
        print(f"{domain} | found: {total} | new: {added}")
        if added > 0:
            new_links_summary[domain] = added
    elapsed = time.time() - start_time
    print(f"Total time taken: {elapsed:.2f} seconds")

    # Always write a summary log line, even if no new links found
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    if new_links_summary:
        summary_parts = [f"{domain}: {count}" for domain, count in new_links_summary.items()]
        summary_line = f"{time_str} " + " ".join(summary_parts) + "\n"
    else:
        summary_line = f"{time_str} none found\n"
    month_str = now.strftime("%Y-%m")
    month_dir = os.path.join(LOG_DIR, month_str)
    os.makedirs(month_dir, exist_ok=True)
    summary_log_path = os.path.join(month_dir, "summary.log")
    with open(summary_log_path, "a", encoding="utf-8") as f:
        f.write(summary_line)
