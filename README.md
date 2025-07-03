# 🎓 COSMO – Conversational AI Assistant for UTD

COSMO is a smart, end-to-end conversational assistant designed for The University of Texas at Dallas. It crawls university data, summarizes and embeds relevant documents,
and enables natural language interaction through a React-based UI and an LLM-powered backend.

## 🧠 Key Features

### ✅ UTD Knowledge Ingestion
- Custom **Scrapy spider** crawls public pages from UTD website.
- Summarization using LLMs to clean and format the data.
- Embedding via **Jina Embeddings API**, indexed using **LlamaIndex**.

### ✅ Conversational Backend (FastAPI)
- Query engine built using:
  - HuggingFace LLM (`Mixtral-8x7B-Instruct`)
  - Jina reranker and embedder
  - Prompt engineering for UTD-specific response formats
- Hosted on a REST endpoint (`/chat`) for frontend integration

### ✅ React Frontend
- Chat bubble widget with animated UI
- Avatars and typing indicators for enhanced UX
- Real-time connection to backend
