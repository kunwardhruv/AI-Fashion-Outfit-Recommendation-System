"""
LLM Service — Groq Llama 3.3 70B integration.

Two main jobs:
1. extract_user_intent()  → Parse what the user actually wants (gender, occasion, style)
2. generate_explanation() → Write human-readable rationale for the recommended outfit
"""

import json
import re
from groq import Groq
from .config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def extract_user_intent(message: str, conversation_history: list | None = None) -> dict:
    """
    WHY LLM here instead of regex:
    Users say things like "I'm a 22-year-old dude going to my cousin's shaadi next week"
    → We need to extract: gender=men, occasion=wedding, age_group=20s
    Regex would fail on natural language variation; LLM handles it gracefully.
    """

    system_prompt = """You are a fashion intent parser. Extract structured information from user fashion requests.

Return ONLY a valid JSON object with these fields:
- "gender": "men" or "women" (infer from pronouns/age context; default "men" if ambiguous)
- "occasion": one of exactly ["office", "wedding", "casual", "sports", "vacation", "party", "festive", "winter"]
- "age_group": one of ["teen", "20s", "30s", "40s", "50s+"] (infer from stated age or context)
- "style_keywords": array of style descriptors like ["formal", "casual", "ethnic", "smart", "streetwear"]
- "specific_items": array of any specific clothing items mentioned (e.g. ["white shirt", "jeans"])
- "color_preferences": array of colors mentioned (empty if none)

RULES:
- business meeting → office
- shaadi/wedding → wedding
- beach/holiday/trip → vacation
- club/party/dinner → party
- eid/diwali/festival → festive
- gym/run/sport → sports
- cold/snow → winter
- otherwise → casual

Output ONLY the JSON. No markdown. No explanation. No backticks."""

    messages_to_send = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        messages_to_send.extend(conversation_history[-6:])

    messages_to_send.append({"role": "user", "content": message})

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages_to_send,
            max_tokens=400,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[Intent extraction error] {e}")
        return {
            "gender": "men",
            "occasion": "casual",
            "age_group": "20s",
            "style_keywords": [],
            "specific_items": [],
            "color_preferences": [],
        }


def generate_explanation(
    outfit_items: list[dict],
    user_query: str,
    occasion: str,
    gender: str,
    stylist_rationale: str | None = None,
) -> str:
    """
    WHY LLM for explanation:
    - We have 25 stylist rationales from curated outfits as reference
    - LLM adapts that expert language to the user's specific query
    - Result feels personal, not templated
    """

    items_desc = "\n".join(
        [
            f"- [{item.get('outfit_role', item.get('category', 'item')).upper()}] "
            f"{item['name']} (₹{item.get('price_inr', 'N/A')}) — {str(item.get('description', ''))[:120]}"
            for item in outfit_items
        ]
    )

    reference = f"\nStylist reference note: {stylist_rationale}" if stylist_rationale else ""

    prompt = f"""User asked: "{user_query}"
Occasion: {occasion} | Gender: {gender}

Outfit recommended:
{items_desc}
{reference}

Write a warm, expert 3-4 sentence explanation of WHY this outfit works.
Focus on: color harmony, occasion fit, overall aesthetic.
Be specific about the items. Sound like a knowledgeable friend, not a robot."""

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a warm, knowledgeable fashion stylist. Give specific, helpful outfit explanations.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=350,
            temperature=0.75,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Explanation error] {e}")
        return "This outfit was selected to match your occasion and style preferences perfectly."


def generate_no_match_response(user_query: str) -> str:
    """Friendly fallback when we can't assemble a full outfit."""
    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly fashion assistant. Be helpful and concise.",
                },
                {
                    "role": "user",
                    "content": f'User asked: "{user_query}". Our dataset is limited. Write a 1-2 sentence friendly response asking them to clarify gender and occasion, and mention we\'ll try our best.',
                },
            ],
            max_tokens=100,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Could you tell me a bit more about the occasion and whether you're looking for men's or women's fashion? I'll find the perfect outfit!"
