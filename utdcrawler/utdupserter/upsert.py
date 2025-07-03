import scrapy
from scrapy.crawler import CrawlerProcess
from pymongo import MongoClient
from bs4 import BeautifulSoup
import tldextract
import requests
import re
import time
import sys
import copy

# === CONFIG ===
SOURCE_MONGO_URI = ""
TARGET_MONGO_URI = ""
SOURCE_DB = "utd_crawler"
SOURCE_COLLECTION = "pages"
TARGET_DB = "utd_cleaned"
TARGET_COLLECTION = "cleaned_pages"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# === SCRAPY SPIDER ===
class UtdSpiderUpsert(scrapy.Spider):
    name = "utd_upsert"

    def __init__(self, url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not url:
            raise ValueError("A URL must be provided")
        self.start_urls = [url]
        self.visited_links = set()
        self.client = MongoClient(SOURCE_MONGO_URI)
        self.collection = self.client[SOURCE_DB][SOURCE_COLLECTION]

    def parse(self, response):
        self.visited_links.add(response.url)
        self.logger.info(f"Crawling: {response.url}")

        item = {
            "url": response.url,
            "title": response.xpath("//title/text()").get(default="No Title"),
            "text": " ".join(response.xpath("//body//text()").getall()).strip(),
            "metadata": {},
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }

        for meta in response.xpath("//meta[@name]"):
            name = meta.xpath("@name").get()
            content = meta.xpath("@content").get()
            item["metadata"][name] = content

        # Insert or update the raw HTML/text
        self.collection.replace_one({"url": response.url}, item, upsert=True)
        self.logger.info(f"[STORED] Raw data for {response.url}")

        # Post-process immediately
        process_cleaning_pipeline(item)

# === CLEANING & SUMMARIZATION ===

def clean_html_bs4(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "noscript", "footer", "nav", "aside"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip())

def filter_garbage_lines(text):
    lines = text.split("\n")
    return "\n".join(
        line for line in lines
        if len(line.split()) >= 3 and not re.search(r"(function|\{|\}|\.js|#|var\s)", line)
    )

def chunk_text(text, max_chars=4000):
    lines, chunks, current, total = text.split("\n"), [], [], 0
    for line in lines:
        if total + len(line) > max_chars:
            chunks.append("\n".join(current))
            current, total = [], 0
        current.append(line)
        total += len(line)
    if current:
        chunks.append("\n".join(current))
    return chunks

def ask_ollama(chunk):
    prompt = (
        "The following is the visible text extracted from a university website.\n"
        "Ignore all technical details, styles, buttons, accessibility tags, modals, code, and navigation menus.\n"
        "Extract and summarize only meaningful, human-readable content intended for students, faculty, staff, or visitors.\n"
        "Focus on conveying relevant information about admissions, academic programs, scholarships, events, student resources, campus safety, emergency contacts, university acheivements, professor biographies and any infomation relevant to the university and the users of the university's websites.\n"
        "Include names of people, their titles or roles, phone numbers, and emails **only if clearly part of the informational content**, and **integrate them naturally into the summary**.\n"
        "Include particulars like dates and times for events and other items **only if clearly part of the informational content**, and **integrate them naturally into the summary**.\n"
        "Do not mention modal behavior, layout structure, or CSS properties. Do not start the output with phrases like 'Summary:', 'Here’s a summary', or similar. Return only the clean, useful summary text.\n\n"
        "Do not make up or assume any information. Do not include any information that is not present in the text.\n"
        "Give the factual information only. Do not include any opinions or assumptions.\n"
        f"{chunk}"
    )
    r = requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
    if r.status_code == 200:
        return r.json().get("response", "")
    return f"[Error {r.status_code}] {r.text}"

def extract_summary(text):
    cleaned = clean_html_bs4(text)
    filtered = filter_garbage_lines(cleaned)
    chunks = chunk_text(filtered)
    summaries = []
    for i, chunk in enumerate(chunks):
        print(f"[OLLLAMA] Sending chunk {i+1}/{len(chunks)}...")
        summaries.append(ask_ollama(chunk))
    return "\n\n".join(summaries)

def process_cleaning_pipeline(doc):
    raw_text = doc.get("text", "")
    if not raw_text.strip():
        print("[SKIP] Empty text")
        return

    summary = extract_summary(raw_text)

    cleaned_doc = copy.deepcopy(doc)
    cleaned_doc["cleaned_content"] = summary
    cleaned_doc.pop("text", None)

    target = MongoClient(TARGET_MONGO_URI)[TARGET_DB][TARGET_COLLECTION]
    target.replace_one({"url": doc["url"]}, cleaned_doc, upsert=True)
    print(f"[CLEANED] Summary stored for {doc['url']}")

# === ENTRY POINT ===

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scrape_and_summarize_single.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    process = CrawlerProcess(settings={"LOG_LEVEL": "ERROR"})
    process.crawl(UtdSpiderUpsert, url=url)
    process.start()
    print(f"[INFO] Finished processing {url}")