"""Semantic relevance classification and market pricing refinement engine."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .ai_analyzer import deduce_native_analysis
from .models import (
    COMMERCIAL_PAGE_TYPES,
    CommerceIntelligence,
    CommerceSummary,
    EnrichedCommerceMatch,
    KnowledgeGraph,
    MatchRelevance,
    PageType,
    StockStatus,
    VisualAnalysis,
    VisualMatch,
)

# Digital document / media listings (printables, lesson plans, wallpapers) — never a physical good.
DIGITAL_DOCUMENT_PATTERN = re.compile(
    r"\bworksheet\b|\blesson\s*plan\b|\breading\s*comprehension\b"
    r"|\bcoloring\s*(?:page|book)\b|\bwallpaper\b|\bclipart\b|\bstock\s*vector\b",
    re.I,
)

# Standard linguistic stop words (grammatical particles, prepositions, conjunctions)
# STRICTLY NO DOMAIN OR CATEGORY NOUNS (no shoes, watches, electronics, colors, etc.)
LINGUISTIC_STOP_WORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "with",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


def _clean_tokens(text: str) -> set[str]:
    """Extracts normalized alphanumeric tokens excluding linguistic stop words."""
    raw_tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in raw_tokens if len(t) > 1 and t not in LINGUISTIC_STOP_WORDS}


def is_noise_item(title: str, url: str) -> bool:
    """Detects whether a listing is a digital document or printable rather than a physical good."""
    return bool(DIGITAL_DOCUMENT_PATTERN.search(f"{title} {url}"))


def classify_match_relevance(
    item: EnrichedCommerceMatch,
    analysis: VisualAnalysis | None = None,
) -> MatchRelevance:
    """Classifies an enriched item into exact_match, similar, reference, or unrelated."""
    title = item.title or ""
    url = item.direct_url or item.original_url or ""
    page_type = item.page_type

    # 1. Check for digital document / printable reference items (worksheets, wallpapers, coloring pages)
    if is_noise_item(title, url):
        return MatchRelevance.REFERENCE

    # 2. Non-commercial page types default to reference
    if page_type in (PageType.ARTICLE, PageType.SOCIAL, PageType.PORTFOLIO):
        return MatchRelevance.REFERENCE

    # If no analysis is available, fall back to basic page type deduction
    if analysis is None or not analysis.attributes:
        if page_type in COMMERCIAL_PAGE_TYPES:
            return MatchRelevance.SIMILAR
        return MatchRelevance.REFERENCE

    target_brand = (analysis.attributes.brand or "").strip().lower()
    target_model = (analysis.attributes.model_or_name or "").strip().lower()
    target_category = (analysis.attributes.category or "").strip().lower()

    item_title_lower = title.lower()
    item_brand_lower = (item.brand or "").lower()
    item_merchant_lower = (item.merchant_name or "").lower()

    # Brand alignment check
    brand_matched = False
    if target_brand and (
        target_brand in item_brand_lower
        or target_brand in item_title_lower
        or target_brand in item_merchant_lower
    ):
        brand_matched = True

    # Model tokens check
    model_tokens = _clean_tokens(target_model)
    # Remove brand token if present in model tokens
    if target_brand:
        model_tokens.discard(target_brand)

    title_tokens = _clean_tokens(title)

    matching_model_tokens = model_tokens.intersection(title_tokens)
    model_match_ratio = len(matching_model_tokens) / len(model_tokens) if model_tokens else 0.0

    # Exact match: Both brand matches and significant model tokens match
    # E.g. "Nike" + ["free", "rn", "flyknit"]
    if brand_matched and (model_match_ratio >= 0.5 or len(matching_model_tokens) >= 2):
        return MatchRelevance.EXACT_MATCH

    # If brand matches strongly or model matches strongly
    if brand_matched or model_match_ratio >= 0.5:
        return MatchRelevance.SIMILAR

    # Check category overlap (e.g. sneaker / shoe / footwear)
    category_tokens = _clean_tokens(target_category)
    if category_tokens.intersection(title_tokens) and page_type in COMMERCIAL_PAGE_TYPES:
        return MatchRelevance.SIMILAR

    # Check visual tags overlap
    analysis_tags = {t.lower() for t in analysis.tags}
    if len(analysis_tags.intersection(title_tokens)) >= 2 and page_type in COMMERCIAL_PAGE_TYPES:
        return MatchRelevance.SIMILAR

    # If it's a product page but neither brand, model, nor category matches
    return MatchRelevance.UNRELATED


def recompute_market_summary(
    items: Sequence[EnrichedCommerceMatch],
    original_summary: CommerceSummary,
) -> CommerceSummary:
    """Recomputes market pricing analytics strictly over verified product matches."""
    # Filter candidates: Must have price > 0 and be a commercial product
    priced_products = [
        item
        for item in items
        if item.price is not None
        and item.price.amount > 0
        and item.page_type in COMMERCIAL_PAGE_TYPES
    ]

    # Preference hierarchy:
    # 1. Exact matches with price
    # 2. If no exact matches, Similar matches with price
    # 3. If no similar matches, all priced products
    exact_matches = [
        item for item in priced_products if item.relevance == MatchRelevance.EXACT_MATCH
    ]
    similar_matches = [item for item in priced_products if item.relevance == MatchRelevance.SIMILAR]

    if exact_matches:
        active_pool = exact_matches
    elif similar_matches:
        active_pool = similar_matches
    else:
        active_pool = priced_products

    if not active_pool:
        return CommerceSummary(
            target_product=original_summary.target_product,
            total_matches=len(items),
            total_priced_matches=0,
            min_price=None,
            max_price=None,
            avg_price=None,
            currency=original_summary.currency or "USD",
            best_deal=None,
        )

    amounts = [item.price.amount for item in active_pool if item.price is not None]
    min_val = min(amounts)
    max_val = max(amounts)
    avg_val = round(sum(amounts) / len(amounts), 2)

    # Best deal is lowest priced in active verified pool (preferring in-stock items)
    in_stock_candidates = [
        item for item in active_pool if item.stock_status != StockStatus.OUT_OF_STOCK
    ]
    candidate_pool = in_stock_candidates if in_stock_candidates else active_pool
    best_item = min(candidate_pool, key=lambda item: item.price.amount if item.price else float("inf"))
    currency = (
        (best_item.price.currency if best_item.price else None)
        or original_summary.currency
        or "USD"
    )

    return CommerceSummary(
        target_product=original_summary.target_product,
        total_matches=len(items),
        total_priced_matches=len(active_pool),
        min_price=min_val,
        max_price=max_val,
        avg_price=avg_val,
        currency=currency,
        best_deal=best_item,
    )


# Presentation order: exact matches first, then similar, then reference, then unrelated.
_RELEVANCE_RANK: dict[MatchRelevance | None, int] = {
    MatchRelevance.EXACT_MATCH: 0,
    MatchRelevance.SIMILAR: 1,
    MatchRelevance.REFERENCE: 2,
    MatchRelevance.UNRELATED: 3,
}


def sort_commerce_items(
    items: Sequence[EnrichedCommerceMatch],
) -> list[EnrichedCommerceMatch]:
    """Sorts items by relevance, then commercial listings, then priced listings, then match score."""

    def _sort_key(item: EnrichedCommerceMatch) -> tuple[int, bool, bool, int]:
        has_price = item.price is not None and item.price.amount > 0
        return (
            _RELEVANCE_RANK.get(item.relevance, 4),
            item.page_type not in COMMERCIAL_PAGE_TYPES,
            not has_price,
            -item.match_score,
        )

    return sorted(items, key=_sort_key)


def process_commerce_relevance(
    commerce: CommerceIntelligence,
    analysis: VisualAnalysis | None = None,
    *,
    visual_matches: Sequence[VisualMatch] | None = None,
    knowledge_graph: KnowledgeGraph | None = None,
    ocr_text: str | None = None,
) -> CommerceIntelligence:
    """Classifies items for relevance, recomputes verified pricing, sorts, and attaches the analysis.

    When ``analysis`` is not supplied, a keyless native deduction is derived from the Lens signals.
    """
    if analysis is None:
        analysis = deduce_native_analysis(
            visual_matches=visual_matches,
            knowledge_graph=knowledge_graph,
            ocr_text=ocr_text,
        )

    commerce.analysis = analysis
    if not commerce.items:
        return commerce

    # 1. Name the target product the matches are evaluated against
    if analysis and analysis.attributes:
        attrs = analysis.attributes
        name = attrs.model_or_name or attrs.category or ""
        if attrs.brand and not name.lower().startswith(attrs.brand.lower()):
            name = f"{attrs.brand} {name}".strip()
        if name:
            commerce.summary.target_product = name

    # 2. Prefer Gemini's direct per-candidate evaluations, else classify locally
    eval_map = {e.index: e for e in analysis.match_evaluations} if analysis else {}
    for idx, item in enumerate(commerce.items):
        evaluation = eval_map.get(idx)
        if evaluation is not None:
            item.relevance = evaluation.relevance
            item.relevance_reason = evaluation.reason
        else:
            item.relevance = classify_match_relevance(item, analysis)

    # 3. Recompute verified pricing and order items for presentation
    commerce.summary = recompute_market_summary(commerce.items, commerce.summary)
    commerce.items = sort_commerce_items(commerce.items)

    return commerce
