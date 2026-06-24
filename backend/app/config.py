import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FAISS_DIR = BASE_DIR / "faiss_index"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = "llama-3.3-70b-versatile"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# CLIP — for image embeddings (multi-modal retrieval)
# WHY ViT-B-32: lightweight, fast on CPU, 512-dim vectors, well-pretrained on fashion images
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "openai"

# Hybrid search weights — must sum to 1.0
# WHY these values:
#   text(0.45): most reliable signal for understanding occasion/style intent
#   image(0.35): catches visual compatibility that text misses (color, silhouette)
#   bm25(0.20): exact keyword match for brand names, product titles
HYBRID_WEIGHT_TEXT = 0.45
HYBRID_WEIGHT_IMAGE = 0.35
HYBRID_WEIGHT_BM25 = 0.20

# Category → outfit role mapping
CATEGORY_ROLES = {
    "topwear": [
        "formal-shirts", "casual-shirts", "party-shirts", "tshirts",
        "polo-tshirts", "linen-shirts", "sweatshirts", "sweaters",
        "tops", "activewear",
    ],
    "full_outfit": [
        "party-dresses", "casual-dresses", "maxi-dresses", "co-ord-sets",
        "kurta-sets", "sherwanis", "salwar-suits", "sharara-sets", "wedding-sarees",
    ],
    "bottomwear": [
        "trousers", "jeans", "chinos", "shorts",
        "track-pants", "leggings", "skirts",
    ],
    "footwear": [
        "heels", "boots", "sneakers", "running-shoes",
        "formal-shoes", "loafers", "sandals", "flats", "ethnic-footwear",
    ],
    "layer": [
        "suits", "blazers", "denim-jackets", "long-coats", "nehru-jackets",
    ],
    "accessory": [
        "necklaces", "clutches", "handbags", "earrings",
        "watches", "sunglasses", "caps",
    ],
}

ROLE_LABELS = {
    "topwear": "👕 Topwear",
    "full_outfit": "👗 Outfit",
    "bottomwear": "👖 Bottomwear",
    "footwear": "👟 Footwear",
    "layer": "🧥 Layer",
    "accessory": "💍 Accessory",
}