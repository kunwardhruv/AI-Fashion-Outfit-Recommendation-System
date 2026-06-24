"""
Recommendation Engine — 2-tier hybrid system

Tier 1: Expert-curated outfit matching (25 outfits as ground truth)
Tier 2: Multi-modal hybrid search (text + image CLIP + BM25) → assemble outfit

Compatibility Graph (bonus):
  25 curated outfits → NetworkX graph where products are nodes,
  co-occurrence in same outfit = weighted edge.
  Used to find "what commonly pairs with X" from expert data.
"""

import pandas as pd
import numpy as np
import networkx as nx
from .config import CATEGORY_ROLES, ROLE_LABELS
from .embeddings import EmbeddingService


def _safe_str(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    return str(val).strip()


def _clean_product(product: dict) -> dict:
    """
    WHY this function exists:
    pandas loads empty CSV cells as float('nan').
    Python's json.dumps() cannot serialize NaN — it throws ValueError.
    So we replace every NaN/Infinity with None before returning to FastAPI.
    None serializes cleanly as JSON null.
    """
    cleaned = {}
    for k, v in product.items():
        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            cleaned[k] = None
        elif isinstance(v, np.integer):
            # numpy int types also fail JSON serialization
            cleaned[k] = int(v)
        elif isinstance(v, np.floating):
            cleaned[k] = float(v) if not (np.isnan(v) or np.isinf(v)) else None
        else:
            cleaned[k] = v
    return cleaned


def _get_role(category: str) -> str:
    for role, cats in CATEGORY_ROLES.items():
        if category in cats:
            return role
    return "other"


class RecommendationEngine:

    def __init__(self, emb: EmbeddingService):
        self.emb = emb
        self.compatibility_graph = self._build_compatibility_graph()

    # ─────────────────────────────────────────────
    # Compatibility Graph
    # WHY: 25 expert outfits encode stylist knowledge about what pairs with what.
    # Building a graph from them lets us query: "given a navy blazer, what bottom
    # did stylists pair it with?" — without any ML training required.
    # ─────────────────────────────────────────────

    def _build_compatibility_graph(self) -> nx.Graph:
        """
        Nodes = product IDs
        Edges = appeared together in same curated outfit (weight = frequency)
        """
        G = nx.Graph()
        outfits_df = self.emb.outfits_df

        id_cols = ["hero_id", "second_id", "layer_id", "footwear_id", "accessory_1_id", "accessory_2_id"]

        for _, outfit in outfits_df.iterrows():
            items_in_outfit = []
            for col in id_cols:
                pid = _safe_str(outfit.get(col))
                if pid and pid.lower() != "nan":
                    items_in_outfit.append(pid)

            # Add all pairwise edges
            for i, a in enumerate(items_in_outfit):
                for b in items_in_outfit[i + 1:]:
                    if G.has_edge(a, b):
                        G[a][b]["weight"] += 1
                    else:
                        G.add_edge(a, b, weight=1)

        print(f"✅ Compatibility graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def get_compatible_items(self, product_id: str, role_filter: str | None = None) -> list[str]:
        """
        Given a product ID, return IDs of items that experts paired it with,
        sorted by edge weight (most frequent pairing first).
        """
        if product_id not in self.compatibility_graph:
            return []
        neighbors = sorted(
            self.compatibility_graph[product_id].items(),
            key=lambda x: -x[1]["weight"]
        )
        result = [pid for pid, _ in neighbors]
        if role_filter:
            target_cats = CATEGORY_ROLES.get(role_filter, [])
            result = [
                pid for pid in result
                if (p := self.emb.get_product_by_id(pid)) and p["category"] in target_cats
            ]
        return result

    # ─────────────────────────────────────────────
    # Tier 1: Curated outfit matching
    # ─────────────────────────────────────────────

    def _score_curated_outfit(self, outfit: pd.Series, gender: str, occasion: str, style_kws: list[str]) -> float:
        score = 0.0
        if outfit["gender"] == gender:
            score += 3.0
        if outfit["occasion"] == occasion:
            score += 4.0
        haystack = (
            _safe_str(outfit.get("theme")).lower()
            + " " + _safe_str(outfit.get("stylist_rationale")).lower()
        )
        for kw in style_kws:
            if kw.lower() in haystack:
                score += 0.5
        return score

    def find_curated_outfit(self, gender: str, occasion: str, style_kws: list[str]) -> dict | None:
        outfits_df = self.emb.outfits_df
        if outfits_df is None or outfits_df.empty:
            return None
        scores = outfits_df.apply(
            lambda row: self._score_curated_outfit(row, gender, occasion, style_kws), axis=1
        )
        best_idx = scores.idxmax()
        return outfits_df.loc[best_idx].to_dict() if scores[best_idx] >= 3.0 else None

    def _expand_curated(self, curated: dict) -> list[dict]:
        item_slots = [
            ("hero_id", "hero"), ("second_id", "second"), ("layer_id", "layer"),
            ("footwear_id", "footwear"), ("accessory_1_id", "accessory_1"), ("accessory_2_id", "accessory_2"),
        ]
        items = []
        for id_col, _ in item_slots:
            pid = _safe_str(curated.get(id_col))
            if not pid or pid.lower() == "nan":
                continue
            product = self.emb.get_product_by_id(pid)
            if product is None:
                continue
            role = _get_role(product["category"])
            product["outfit_role"] = role
            product["role_label"] = ROLE_LABELS.get(role, role.title())
            # ✅ Clean NaN/Infinity before returning
            items.append(_clean_product(product))
        return items

    # ─────────────────────────────────────────────
    # Tier 2: Hybrid search assembly
    # ─────────────────────────────────────────────

    def _assemble_from_hybrid(self, gender: str, occasion: str, style_kws: list[str]) -> list[dict]:
        query_base = f"{gender} {occasion} {' '.join(style_kws)} fashion outfit"
        outfit: dict[str, dict] = {}

        # Step 1: topwear or full-outfit hero
        for role in ["topwear", "full_outfit"]:
            if role not in outfit:
                results = self.emb.hybrid_search(query_base, k=5, filter_gender=gender, filter_category_role=role)
                if results:
                    p = _clean_product(results[0]["product"])
                    p["outfit_role"] = role
                    p["role_label"] = ROLE_LABELS.get(role, role.title())
                    p["search_scores"] = results[0].get("score_breakdown", {})
                    outfit[role] = p
                    break

        # Step 2: bottomwear — graph first, fallback hybrid
        if "full_outfit" not in outfit:
            hero_id = outfit.get("topwear", {}).get("id")
            bottom_from_graph = self.get_compatible_items(hero_id, role_filter="bottomwear") if hero_id else []

            if bottom_from_graph:
                p = self.emb.get_product_by_id(bottom_from_graph[0])
                if p:
                    p = _clean_product(p)
                    p["outfit_role"] = "bottomwear"
                    p["role_label"] = ROLE_LABELS["bottomwear"]
                    p["compatibility_source"] = "graph"
                    outfit["bottomwear"] = p
            else:
                results = self.emb.hybrid_search(query_base, k=5, filter_gender=gender, filter_category_role="bottomwear")
                if results:
                    p = _clean_product(results[0]["product"])
                    p["outfit_role"] = "bottomwear"
                    p["role_label"] = ROLE_LABELS["bottomwear"]
                    outfit["bottomwear"] = p

        # Step 3: Footwear
        results = self.emb.hybrid_search(
            f"{gender} {occasion} shoes footwear", k=5, filter_gender=gender, filter_category_role="footwear"
        )
        if results:
            p = _clean_product(results[0]["product"])
            p["outfit_role"] = "footwear"
            p["role_label"] = ROLE_LABELS["footwear"]
            outfit["footwear"] = p

        # Step 4: Optional layer
        results = self.emb.hybrid_search(query_base, k=5, filter_gender=gender, filter_category_role="layer")
        if results:
            p = _clean_product(results[0]["product"])
            p["outfit_role"] = "layer"
            p["role_label"] = ROLE_LABELS["layer"]
            outfit["layer"] = p

        # Step 5: Accessory — graph first, fallback hybrid
        hero_id = (outfit.get("topwear") or outfit.get("full_outfit") or {}).get("id")
        acc_from_graph = self.get_compatible_items(hero_id, role_filter="accessory") if hero_id else []
        if acc_from_graph:
            p = self.emb.get_product_by_id(acc_from_graph[0])
            if p:
                p = _clean_product(p)
                p["outfit_role"] = "accessory"
                p["role_label"] = ROLE_LABELS["accessory"]
                outfit["accessory"] = p
        else:
            results = self.emb.hybrid_search(
                f"{gender} {occasion} accessory", k=5, filter_gender=gender, filter_category_role="accessory"
            )
            if results:
                p = _clean_product(results[0]["product"])
                p["outfit_role"] = "accessory"
                p["role_label"] = ROLE_LABELS["accessory"]
                outfit["accessory"] = p

        return list(outfit.values())

    # ─────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────

    def recommend(self, intent: dict) -> dict:
        gender = intent.get("gender") or "men"
        occasion = intent.get("occasion") or "casual"
        style_kws = intent.get("style_keywords") or []

        # Tier 1: curated
        curated = self.find_curated_outfit(gender, occasion, style_kws)
        if curated:
            items = self._expand_curated(curated)
            return {
                "source": "curated",
                "outfit_id": curated.get("outfit_id"),
                "theme": _safe_str(curated.get("theme")),
                "occasion": occasion,
                "gender": gender,
                "palette": _safe_str(curated.get("palette")),
                "stylist_rationale": _safe_str(curated.get("stylist_rationale")),
                "items": items,
                "total_price": _sum_price(items),
            }

        # Tier 2: multi-modal hybrid
        items = self._assemble_from_hybrid(gender, occasion, style_kws)
        return {
            "source": "hybrid_generated",
            "outfit_id": None,
            "theme": f"{' '.join(style_kws)} {occasion}".strip().title() or occasion.title(),
            "occasion": occasion,
            "gender": gender,
            "palette": None,
            "stylist_rationale": None,
            "items": items,
            "total_price": _sum_price(items),
        }


def _sum_price(items: list[dict]) -> float:
    total = 0.0
    for item in items:
        try:
            v = item.get("price_inr")
            if v is not None:
                total += float(v)
        except (ValueError, TypeError):
            pass
    return total