"""
EmbeddingService — Multi-modal Hybrid Search

3 search signals combined:
  1. Text Embeddings (sentence-transformers)
     → Understands semantic intent: "smart casual" matches "chinos" even without exact words
  2. Image Embeddings (CLIP ViT-B-32)
     → Visual compatibility: encodes color, silhouette, style from product photos
     → Query text is ALSO encoded by CLIP text encoder → cross-modal search
  3. BM25 (keyword)
     → Catches exact brand names, product titles that semantic search might score lower

WHY hybrid instead of just FAISS:
  Each signal catches different things. A query like "Peter England white shirt" needs BM25
  for the brand name, FAISS text for "formal office", CLIP for the visual white shirt look.
  Combining all three = more robust retrieval.
"""

import numpy as np
import faiss
import pandas as pd
import pickle
import math
from pathlib import Path
from PIL import Image
from sentence_transformers import SentenceTransformer
import open_clip
import torch
from rank_bm25 import BM25Okapi

from .config import (
    DATA_DIR, FAISS_DIR, EMBEDDING_MODEL,
    CLIP_MODEL_NAME, CLIP_PRETRAINED,
    HYBRID_WEIGHT_TEXT, HYBRID_WEIGHT_IMAGE, HYBRID_WEIGHT_BM25,
    CATEGORY_ROLES,
)


class EmbeddingService:

    def __init__(self):
        print("Loading sentence-transformer model...")
        self.text_model = SentenceTransformer(EMBEDDING_MODEL)

        print("Loading CLIP model...")
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
            CLIP_MODEL_NAME, pretrained=CLIP_PRETRAINED
        )
        self.clip_tokenizer = open_clip.get_tokenizer(CLIP_MODEL_NAME)
        self.clip_model.eval()

        self.products_df: pd.DataFrame | None = None
        self.outfits_df: pd.DataFrame | None = None

        # Text FAISS index
        self.text_index: faiss.Index | None = None
        # Image FAISS index
        self.image_index: faiss.Index | None = None

        self.product_ids: list[str] = []
        self.bm25: BM25Okapi | None = None
        self.bm25_corpus: list[list[str]] = []

    # ─────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────

    def load_data(self):
        self.products_df = pd.read_csv(DATA_DIR / "products.csv")
        self.outfits_df = pd.read_csv(DATA_DIR / "outfits.csv")
        self.products_df["id"] = self.products_df["id"].astype(str)
        print(f"Loaded {len(self.products_df)} products, {len(self.outfits_df)} outfits")

    # ─────────────────────────────────────────────
    # Text representation
    # ─────────────────────────────────────────────

    def _product_to_text(self, row: pd.Series) -> str:
        parts = [
            row["name"],
            f"by {row['brand']}",
            f"Category: {row.get('category_label', row['category'])}",
            f"Occasion: {row['occasion']}",
            f"Gender: {row['gender']}",
            f"Style: {row['wear_type']}",
        ]
        if pd.notna(row.get("description")):
            parts.append(str(row["description"])[:200])
        if pd.notna(row.get("tags")):
            parts.append(f"Tags: {row['tags']}")
        return ". ".join(parts)

    # ─────────────────────────────────────────────
    # Build all indexes
    # ─────────────────────────────────────────────

    def build_index(self):
        FAISS_DIR.mkdir(exist_ok=True)
        self.product_ids = self.products_df["id"].tolist()

        # ── 1. Text FAISS ──
        print("Building text embeddings (sentence-transformers)...")
        texts = [self._product_to_text(row) for _, row in self.products_df.iterrows()]
        text_embs = self.text_model.encode(texts, show_progress_bar=True, batch_size=32)
        text_embs = np.array(text_embs, dtype="float32")
        faiss.normalize_L2(text_embs)

        self.text_index = faiss.IndexFlatIP(text_embs.shape[1])
        self.text_index.add(text_embs)
        faiss.write_index(self.text_index, str(FAISS_DIR / "text.index"))
        print(f"  ✅ Text index: {self.text_index.ntotal} vectors, dim={text_embs.shape[1]}")

        # ── 2. Image FAISS (CLIP) ──
        print("Building image embeddings (CLIP)...")
        image_embs = self._build_clip_image_embeddings()
        faiss.normalize_L2(image_embs)

        self.image_index = faiss.IndexFlatIP(image_embs.shape[1])
        self.image_index.add(image_embs)
        faiss.write_index(self.image_index, str(FAISS_DIR / "image.index"))
        print(f"  ✅ Image index: {self.image_index.ntotal} vectors, dim={image_embs.shape[1]}")

        # ── 3. BM25 ──
        print("Building BM25 keyword index...")
        self.bm25_corpus = [text.lower().split() for text in texts]
        self.bm25 = BM25Okapi(self.bm25_corpus)
        with open(FAISS_DIR / "bm25.pkl", "wb") as f:
            pickle.dump((self.bm25, self.bm25_corpus), f)

        # ── 4. Save product IDs ──
        with open(FAISS_DIR / "product_ids.pkl", "wb") as f:
            pickle.dump(self.product_ids, f)

        print("✅ All indexes built and saved!")

    def _build_clip_image_embeddings(self) -> np.ndarray:
        """
        WHY CLIP for images:
        CLIP (Contrastive Language-Image Pretraining) was trained to align
        text and image representations. So when a user says "navy blazer",
        the CLIP text embedding is close to the CLIP image embedding of an
        actual navy blazer photo. This enables cross-modal search.
        """
        embeddings = []
        missing_count = 0

        for _, row in self.products_df.iterrows():
            img_path = DATA_DIR / str(row.get("image", ""))

            if img_path.exists():
                try:
                    img = Image.open(img_path).convert("RGB")
                    img_tensor = self.clip_preprocess(img).unsqueeze(0)

                    with torch.no_grad():
                        emb = self.clip_model.encode_image(img_tensor)
                    embeddings.append(emb.squeeze().numpy().astype("float32"))
                    continue
                except Exception as e:
                    print(f"  ⚠ Image error for {row['id']}: {e}")

            # Fallback: use CLIP text encoder for this product
            # WHY: Better than zero vector — text embedding is still in same CLIP space
            missing_count += 1
            text = f"{row['name']} {row.get('category_label', '')} {row.get('occasion', '')}"
            tokens = self.clip_tokenizer([text])
            with torch.no_grad():
                emb = self.clip_model.encode_text(tokens)
            embeddings.append(emb.squeeze().numpy().astype("float32"))

        if missing_count:
            print(f"  ⚠ {missing_count} images missing — used CLIP text fallback")

        return np.array(embeddings, dtype="float32")

    # ─────────────────────────────────────────────
    # Load saved indexes
    # ─────────────────────────────────────────────

    def load_index(self):
        text_path = FAISS_DIR / "text.index"
        image_path = FAISS_DIR / "image.index"
        ids_path = FAISS_DIR / "product_ids.pkl"
        bm25_path = FAISS_DIR / "bm25.pkl"

        if all(p.exists() for p in [text_path, image_path, ids_path, bm25_path]):
            self.text_index = faiss.read_index(str(text_path))
            self.image_index = faiss.read_index(str(image_path))
            with open(ids_path, "rb") as f:
                self.product_ids = pickle.load(f)
            with open(bm25_path, "rb") as f:
                self.bm25, self.bm25_corpus = pickle.load(f)
            print(f"✅ Indexes loaded — text:{self.text_index.ntotal}, image:{self.image_index.ntotal}, bm25:{len(self.bm25_corpus)}")
        else:
            print("No saved indexes found — building from scratch...")
            self.build_index()

    # ─────────────────────────────────────────────
    # Hybrid Search
    # ─────────────────────────────────────────────

    def hybrid_search(
        self,
        query: str,
        k: int = 20,
        filter_gender: str | None = None,
        filter_category_role: str | None = None,
    ) -> list[dict]:
        """
        3-signal hybrid search with score fusion.

        Pipeline:
          1. FAISS text search  → cosine scores (0 to 1)
          2. FAISS image search via CLIP text encoder → cosine scores (0 to 1)
          3. BM25 keyword search → raw scores, min-max normalised to (0 to 1)
          4. Weighted sum → final ranking

        WHY min-max normalise BM25:
          BM25 scores are unbounded (can be 0 to ~20), FAISS cosine is 0-1.
          Normalise before combining so one signal doesn't dominate.
        """
        fetch_k = min(len(self.product_ids), k * 6)

        # ── Text FAISS ──
        t_emb = self.text_model.encode([query], show_progress_bar=False).astype("float32")
        faiss.normalize_L2(t_emb)
        t_scores, t_indices = self.text_index.search(t_emb, fetch_k)
        text_score_map = {self.product_ids[i]: float(s) for s, i in zip(t_scores[0], t_indices[0]) if i != -1}

        # ── Image FAISS (via CLIP text encoder) ──
        # WHY text encoder here: user sends text query, we embed it with CLIP text encoder
        # which is in the SAME embedding space as CLIP image encoder → cross-modal search
        tokens = self.clip_tokenizer([query])
        with torch.no_grad():
            clip_text_emb = self.clip_model.encode_text(tokens).numpy().astype("float32")
        faiss.normalize_L2(clip_text_emb)
        i_scores, i_indices = self.image_index.search(clip_text_emb, fetch_k)
        image_score_map = {self.product_ids[i]: float(s) for s, i in zip(i_scores[0], i_indices[0]) if i != -1}

        # ── BM25 ──
        query_tokens = query.lower().split()
        bm25_raw = self.bm25.get_scores(query_tokens)
        bm25_min, bm25_max = bm25_raw.min(), bm25_raw.max()
        bm25_range = bm25_max - bm25_min if bm25_max > bm25_min else 1.0
        bm25_norm = (bm25_raw - bm25_min) / bm25_range
        bm25_score_map = {self.product_ids[i]: float(bm25_norm[i]) for i in range(len(self.product_ids))}

        # ── Fuse scores ──
        all_ids = set(text_score_map) | set(image_score_map) | set(bm25_score_map)
        fused = {}
        for pid in all_ids:
            fused[pid] = (
                HYBRID_WEIGHT_TEXT  * text_score_map.get(pid, 0.0)
                + HYBRID_WEIGHT_IMAGE * image_score_map.get(pid, 0.0)
                + HYBRID_WEIGHT_BM25  * bm25_score_map.get(pid, 0.0)
            )

        # ── Sort + Filter ──
        target_cats = CATEGORY_ROLES.get(filter_category_role, []) if filter_category_role else None
        results = []

        for pid, score in sorted(fused.items(), key=lambda x: -x[1]):
            row = self.products_df[self.products_df["id"] == pid]
            if row.empty:
                continue
            product = row.iloc[0].to_dict()

            if filter_gender and product["gender"] != filter_gender:
                continue
            if target_cats and product["category"] not in target_cats:
                continue

            results.append({
                "product": product,
                "score": score,
                "score_breakdown": {
                    "text": round(text_score_map.get(pid, 0.0), 4),
                    "image": round(image_score_map.get(pid, 0.0), 4),
                    "bm25": round(bm25_score_map.get(pid, 0.0), 4),
                },
            })
            if len(results) >= k:
                break

        return results

    # ─────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────

    def get_product_by_id(self, product_id: str) -> dict | None:
        row = self.products_df[self.products_df["id"] == str(product_id)]
        return row.iloc[0].to_dict() if not row.empty else None