from pymongo import MongoClient
from bs4 import BeautifulSoup
import requests
import re
import copy
from tqdm import tqdm

# MongoDB Config
SOURCE_MONGO_URI = ""
SOURCE_DB = "utd_crawler"
SOURCE_COLLECTION = "pages"
TARGET_MONGO_URI = ""
TARGET_DB = "utd_cleaned"
TARGET_COLLECTION = "cleaned_pages"

# Ollama Config
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

# === HTML CLEANING HELPERS ===

def clean_html_bs4(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for tag in soup.find_all(['nav', 'footer', 'aside']):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

def filter_garbage_lines(text):
    lines = text.split("\n")
    filtered = []
    for line in lines:
        if re.search(r"(var |function|\.com|\.edu|#|\.js|\{|\}|;)", line):
            continue
        if len(line.split()) < 3:
            continue
        if line.lower().startswith(("click", "press", "hover", "menu", "var", "document")):
            continue
        filtered.append(line.strip())
    return "\n".join(filtered)

def chunk_text(text, max_chars=4000):
    lines = text.split("\n")
    chunks, current, total = [], [], 0
    for line in lines:
        if total + len(line) > max_chars:
            chunks.append("\n".join(current))
            current, total = [], 0
        current.append(line)
        total += len(line)
    if current:
        chunks.append("\n".join(current))
    return chunks

# === LLM CALL ===

def ask_ollama(chunk, model=MODEL):
    prompt = (
        "The following is the visible text extracted from a university website.\n"
        "Ignore all technical details, styles, buttons, accessibility tags, modals, code, and navigation menus.\n"
        "Extract and summarize only meaningful, human-readable content intended for students, faculty, staff, or visitors.\n"
        "Focus on conveying relevant information about admissions, academic programs, scholarships, events, student resources, campus safety, emergency contacts, and university achievements.\n"
        "Include names of people, their titles or roles, phone numbers, and emails **only if clearly part of the informational content**, and **integrate them naturally into the summary**.\n"
        "Include particulars like dates and times for events and other items **only if clearly part of the informational content**, and **integrate them naturally into the summary**.\n"
        "Do not mention modal behavior, layout structure, or CSS properties. Do not start the output with phrases like 'Summary:', 'Here’s a summary', or similar. Return only the clean, useful summary text.\n\n"
        f"{chunk}"
    )

    response = requests.post(OLLAMA_URL, json={
        "model": model,
        "prompt": prompt,
        "stream": False
    })

    if response.status_code == 200:
        return response.json().get("response", "")
    return f"[Error {response.status_code}]: {response.text}"

def extract_meaningful_content(raw_html):
    cleaned = clean_html_bs4(raw_html)
    filtered = filter_garbage_lines(cleaned)
    chunks = chunk_text(filtered)
    summaries = []

    for i, chunk in enumerate(chunks):
        print(f"→ Sending chunk {i+1}/{len(chunks)} to Ollama...")
        response = ask_ollama(chunk)
        summaries.append(response)

    return "\n\n".join(summaries)

# === MAIN PIPELINE ===

def main():
    source_client = MongoClient(SOURCE_MONGO_URI)
    source = source_client[SOURCE_DB][SOURCE_COLLECTION]
    target_client = MongoClient(TARGET_MONGO_URI)
    target = target_client[TARGET_DB][TARGET_COLLECTION]

    docs = list(source.find({}))
    for doc in tqdm(docs, desc="Processing pages"):
        raw_html = doc.get("text", "")
        if not raw_html.strip():
            continue

        cleaned_content = extract_meaningful_content(raw_html)

        new_doc = copy.deepcopy(doc)
        new_doc["cleaned_content"] = cleaned_content
        new_doc.pop("text", None)  # Remove raw HTML

        target.insert_one(new_doc)

if __name__ == "__main__":
    main()
