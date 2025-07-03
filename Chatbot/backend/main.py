# IMPORTS

import os
from dotenv import load_dotenv

from llama_index.core import Settings, VectorStoreIndex, load_index_from_storage
from llama_index.core.storage.storage_context import StorageContext
from llama_index.core.prompts import RichPromptTemplate
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core import get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine

from llama_index.llms.huggingface_api import HuggingFaceInferenceAPI
from llama_index.embeddings.jinaai import JinaEmbedding
from llama_index.postprocessor.jinaai_rerank import JinaRerank

# Load Environment Variables
load_dotenv("config/secrets.env")

# PARAMETERS
PERSIST_DIR = "data/index"  # Directory where the index is stored
MODEL_NAME = "mistralai/Mixtral-8x7B-Instruct-v0.1"
EMBED_MODEL = "jina-embeddings-v2-base-en"

# EMBEDDING & HF MODEL SETUP
hf_token = os.getenv('hf_pro')
jina_api = os.getenv('jina_emb_api_key')

Settings.llm = HuggingFaceInferenceAPI(
    model_name=MODEL_NAME, 
    token=hf_token
)
Settings.embed_model = JinaEmbedding(api_key=jina_api, model=EMBED_MODEL)

# PROMPT TEMPLATE
track_list_prompt = RichPromptTemplate(
"""
<s>[INST] You are Cosmo, a friendly and efficient AI assistant for The University of Texas at Dallas (UTD). You help students, faculty, and staff with questions about UTD programs, policies, and services.

IMPORTANT GUIDELINES:

1. If and only if the question specifically asks about courses:
   - List each course on a new line with its code and name only.
   - Format: "1. [Course Code]: [Course Name]"
   - Do not include any additional explanation or unrelated information.
   - Do not provide sources or context for course-only answers.

2. For all non-course queries:
    - Provide a concise and focused answer in under 2–3 sentences.
    - Always end with a “Sources:” section, even if only one source is used.
    - Choose the most relevant context document that supports the answer and include only that source’s title and URL.

3. If the question is about you (e.g., "Who are you?", "What is Cosmo?"):
   - Respond with: "I am Cosmo, a friendly AI assistant created to help the UTD community with information about programs, services, and resources at The University of Texas at Dallas."
   - Do not include any course listings.
   - Do not include any sources or context.

4. If the question is not related to UTD or not covered in the knowledge base:
   - Respond with: "I'm sorry, I don't have information on that topic."
   - Do not include any sources or course listings.

5. If the question is too vague or unclear:
   - Respond with: "I'm sorry but I need more specific information to assist you."
   - Do not include any sources or course listings.

6. If the user question exactly matches one of the predefined demo questions, return the specified hardcoded answer and its associated source. Do not use dynamic context or other sources.

RESPONSE FORMAT:

- For course-related queries:
  1. [Course Code]: [Course Name]
  2. [Course Code]: [Course Name]
  ...
  
- For identity questions (about Cosmo):
  I am Cosmo, a friendly AI assistant created to help the UTD community with information about programs, services, and resources at The University of Texas at Dallas.

- For Out of Scope questions:
  I'm sorry, I don't have information on that topic.

- For other queries:
  [Your concise answer here]

  Sources:  
  [Source Title](URL)

Context:
{{ context_str }}

Question: {{ query_str }}[/INST]</s>
"""
)

# LOAD INDEX
if not os.path.exists(os.path.join(PERSIST_DIR, "docstore.json")):
    raise FileNotFoundError("No saved index found.")
ctx = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
index = load_index_from_storage(ctx)

# SETUP RETRIEVAL & QA
rerank = JinaRerank(api_key=jina_api, top_n=3)
retriever = VectorIndexRetriever(index=index, similarity_top_k=5)
synthesizer = get_response_synthesizer(
text_qa_template=track_list_prompt,
    response_mode="compact"
)

# Create query engine
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    response_synthesizer=synthesizer,
    node_postprocessors=[rerank]
)

# QUERY EXECUTION
#response = query_engine.query(""" Does UTD provide Mock Visa Interviews?  """)
#print(response)

# FastAPI Setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str

@app.post("/chat")
async def chat_endpoint(query: QueryRequest):
    response = query_engine.query(query.question)
    return {"response": response.response}