"""
FastAPI Backend — Dare XAI Fashion Recommendation System

Endpoints:
  POST /api/chat                          → Main chat + recommendation
  GET  /api/compatibility/{product_id}    → Compatibility graph neighbours
  GET  /api/products                      → All products
  GET  /api/outfits                       → All curated outfits
  GET  /api/health                        → Health check
  GET  /images/**                         → Static image serving
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import traceback

from .config import DATA_DIR
from .embeddings import EmbeddingService
from .recommender import RecommendationEngine
from .llm_service import (
    extract_user_intent,
    generate_explanation,
    generate_no_match_response,
)

# ─────────────────────────────────────────────
# App init
# ─────────────────────────────────────────────

app = FastAPI(title="Dare XAI Fashion API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

emb_service = EmbeddingService()
recommender: RecommendationEngine | None = None


@app.on_event("startup")
async def startup():
    global recommender
    emb_service.load_data()
    emb_service.load_index()          # builds FAISS text + image + BM25 on first run
    recommender = RecommendationEngine(emb_service)   # also builds compatibility graph
    print("✅ Fashion API v2 ready — Multi-modal Hybrid Search + Compatibility Graph active")


# Static image serving
# WHY: products.csv has relative image paths — we serve them directly from backend
# Frontend hits: /images/ajio/703182002.jpg → served from backend/data/images/ajio/
images_dir = DATA_DIR / "images"
if images_dir.exists():
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

class UserProfile(BaseModel):
    gender: Optional[str] = None
    age: Optional[int] = None
    style_preferences: Optional[list[str]] = []

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[list[ChatMessage]] = []
    user_profile: Optional[UserProfile] = None


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        history_dicts = [{"role": m.role, "content": m.content} for m in (request.conversation_history or [])]

        # Step 1: Extract intent — gender, occasion, style keywords
        intent = extract_user_intent(request.message, history_dicts)

        # Step 2: Override with explicit user profile if set in sidebar
        if request.user_profile:
            if request.user_profile.gender:
                intent["gender"] = request.user_profile.gender
            if request.user_profile.style_preferences:
                intent["style_keywords"] = list(
                    set(intent.get("style_keywords", []) + request.user_profile.style_preferences)
                )

        # Step 3: 2-tier recommendation (curated → hybrid fallback)
        recommendation = recommender.recommend(intent)

        # Step 4: LLM explanation
        if recommendation["items"]:
            explanation = generate_explanation(
                outfit_items=recommendation["items"],
                user_query=request.message,
                occasion=recommendation["occasion"],
                gender=recommendation["gender"],
                stylist_rationale=recommendation.get("stylist_rationale"),
            )
            recommendation["explanation"] = explanation
            response_text = (
                f"Here's a perfect {recommendation['theme']} look for you! 🎯"
                if recommendation.get("theme")
                else f"Here's a curated {recommendation['occasion']} outfit for you!"
            )
        else:
            response_text = generate_no_match_response(request.message)
            recommendation["explanation"] = ""

        updated_history = history_dicts + [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response_text},
        ]

        return {
            "response_text": response_text,
            "intent": intent,
            "recommendation": recommendation,
            "conversation_history": updated_history,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compatibility/{product_id}")
async def get_compatibility(product_id: str, role: Optional[str] = None):
    """
    WHY this endpoint:
    Useful for the video demo — show "what does the graph say pairs with X".
    Also shows off the NetworkX compatibility graph feature explicitly.
    """
    compatible_ids = recommender.get_compatible_items(product_id, role_filter=role)
    compatible_products = [
        emb_service.get_product_by_id(pid)
        for pid in compatible_ids
        if emb_service.get_product_by_id(pid)
    ]
    source_product = emb_service.get_product_by_id(product_id)
    return {
        "source_product": source_product,
        "compatible_items": compatible_products,
        "graph_edges": len(compatible_ids),
    }


@app.get("/api/products")
async def get_products(gender: Optional[str] = None, occasion: Optional[str] = None):
    df = emb_service.products_df
    if gender:
        df = df[df["gender"] == gender]
    if occasion:
        df = df[df["occasion"] == occasion]
    return df.to_dict(orient="records")


@app.get("/api/outfits")
async def get_outfits():
    return emb_service.outfits_df.to_dict(orient="records")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0 — Multi-modal Hybrid + Compatibility Graph",
        "products_loaded": len(emb_service.product_ids),
        "outfits_loaded": len(emb_service.outfits_df) if emb_service.outfits_df is not None else 0,
        "text_faiss_vectors": emb_service.text_index.ntotal if emb_service.text_index else 0,
        "image_faiss_vectors": emb_service.image_index.ntotal if emb_service.image_index else 0,
        "graph_nodes": recommender.compatibility_graph.number_of_nodes() if recommender else 0,
        "graph_edges": recommender.compatibility_graph.number_of_edges() if recommender else 0,
    }