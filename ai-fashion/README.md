# 🎨 AI Fashion Outfit Recommendation System

An intelligent, conversational fashion assistant that recommends complete outfit combinations using **multi-modal hybrid search**, **CLIP image embeddings**, **compatibility graphs**, and **LLM-powered explanations**.

---

## 🏗️ Architecture

```
User Chat Input (React Frontend)
         │
         ▼
   FastAPI Backend (/api/chat)
         │
    ┌────┴────────────────────┐
    │                         │
    ▼                         ▼
 Intent Parser           User Profile
 (Groq LLM)              Override
    │
    ▼
┌─────────────────────────────────────────────┐
│         RECOMMENDATION ENGINE               │
│                                             │
│  Tier 1: Curated Outfit Matching            │
│  25 expert outfits → score by gender +      │
│  occasion + style keyword overlap           │
│                         │                   │
│  Tier 2: Multi-Modal Hybrid Search          │
│  ┌──────────────────────────────────────┐   │
│  │  Text FAISS   + Image FAISS  + BM25  │   │
│  │  (45%)          (CLIP 35%)   (20%)   │   │
│  │                                      │   │
│  │  + Compatibility Graph (NetworkX)    │   │
│  │    25 outfits → co-occurrence edges  │   │
│  │    "Navy blazer pairs with chinos"   │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         │
         ▼
  Explanation Generator (Groq LLM)
         │
         ▼
   React Chat UI
   (Product cards + score breakdown + source badge)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Text Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 384-dim semantic text embeddings |
| Image Embeddings | `CLIP ViT-B-32` (open_clip) | Cross-modal: text query → image space search |
| Keyword Search | `BM25Okapi` (rank-bm25) | Exact brand/product name matching |
| Vector Search | `FAISS IndexFlatIP` (×2) | Cosine similarity over text + image indexes |
| Compatibility Graph | `NetworkX` | Expert outfit co-occurrence knowledge |
| LLM | `Groq — Llama 3.3 70B` | Intent extraction + explanation generation |
| Backend | `FastAPI` | Async, type-safe |
| Frontend | `React 18 + Vite + Tailwind` | Chat UI with product grid |

---

## 📁 Project Structure

```
ai-fashion/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── embeddings.py
│   │   ├── llm_service.py
│   │   ├── recommender.py
│   │   └── main.py
│   ├── data/
│   │   ├── products.csv
│   │   ├── outfits.csv
│   │   └── images/         # (ajio/ myntra/ nykaa/) — gitignored
│   ├── faiss_index/        # Auto-generated — gitignored
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── ProductCard.jsx
│   │   │   ├── OutfitRecommendation.jsx
│   │   │   └── UserProfilePanel.jsx
│   │   └── services/
│   │       └── api.js
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── .gitignore
└── README.md
```

---

## 🚀 Setup & Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API key → [console.groq.com](https://console.groq.com) (free)

### 1. Dataset setup

```
backend/data/
├── products.csv
├── outfits.csv
└── images/
    ├── ajio/
    ├── myntra/
    └── nykaa/
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Add your key: GROQ_API_KEY=gsk_...

uvicorn app.main:app --reload --port 8000
```

**First run:** Downloads `all-MiniLM-L6-v2` (~90MB) + `CLIP ViT-B-32` (~350MB),
then builds text FAISS + image FAISS + BM25 + compatibility graph.
Subsequent runs load everything instantly from `faiss_index/`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## 💡 Key Design Decisions

### Why 2-tier recommendation?
- **Tier 1 (Curated):** 25 stylist outfits = fashion-guaranteed combos. Match by gender + occasion.
- **Tier 2 (Hybrid):** Fallback for edge cases. Assembles outfit piece-by-piece using 3-signal hybrid search.

### Why Hybrid Search (text + CLIP + BM25)?
Each signal catches what the others miss:
- **Text FAISS (45%):** "smart casual trousers for summer" → finds chinos semantically
- **CLIP Image (35%):** Cross-modal search — encodes user's text query into CLIP text space, searches CLIP image index. Visual compatibility (color, silhouette) that text alone misses.
- **BM25 (20%):** "Peter England white shirt" → exact brand match that semantic search might downrank

### Why NetworkX compatibility graph?
25 expert outfits = 25 co-occurrence relationships between products. Graph lets us ask: *"Given a navy blazer, what bottomwear did expert stylists pair it with?"* Zero ML training required — pure expert knowledge encoded as graph edges.

### Why FAISS over Qdrant/Chroma?
68 products = FAISS in-memory is instant. No infra needed. Saves to disk between restarts. Qdrant/Chroma would add value at 10,000+ products.

### Hybrid score fusion formula
```
final_score = 0.45 × text_cosine + 0.35 × clip_cosine + 0.20 × bm25_normalised
```
BM25 is min-max normalised before combining (BM25 is unbounded; cosine is 0–1).

---

## 🎯 Example Queries

- "I need an outfit for a business meeting"
- "Suggest a smart casual look for a dinner date"
- "I'm attending a wedding — women, 25 years old"
- "22-year-old male, casual summer outfit"
- "Something stylish for a beach vacation"
- "Festive ethnic look for women"

---

## 🔮 Future Improvements

1. **Pairwise compatibility model** — Train classifier on curated outfit pairs: "does item A go with item B?"
2. **Outfit Similarity Network** — Siamese network to score visual similarity between complete outfits
3. **FashionCLIP** — Fashion-domain fine-tuned CLIP for better visual understanding
4. **User preference learning** — Track liked outfits to personalise recommendations over time
5. **Scale to full catalog** — Qdrant/Weaviate for million-product catalogs

---

## 📊 Advanced Features Implemented

| Bonus Feature | Implementation |
|---|---|
| Multi-modal Retrieval | ✅ CLIP image embeddings + sentence-transformer text |
| Hybrid Search | ✅ Text FAISS + Image FAISS + BM25, weighted fusion |
| RAG Pipeline | ✅ Retrieve outfits/products → Groq LLM generates explanation |
| Fashion Graph-Based Recommendations | ✅ NetworkX compatibility graph from 25 curated outfits |