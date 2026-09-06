"""Unit tests for semantic relevance classification and verified pricing analytics."""

from __future__ import annotations

from google_lens_scraper.models import (
    CommerceIntelligence,
    CommerceSummary,
    EnrichedCommerceMatch,
    MatchRelevance,
    NormalizedPrice,
    PageType,
    ProductAttributes,
    VisualAnalysis,
)
from google_lens_scraper.relevance import (
    classify_match_relevance,
    is_noise_item,
    process_commerce_relevance,
    recompute_market_summary,
    sort_commerce_items,
)


def _make_analysis() -> VisualAnalysis:
    return VisualAnalysis(
        summary="Nike Free RN Flyknit athletic running shoe in red colorway.",
        attributes=ProductAttributes(
            brand="Nike",
            model_or_name="Free RN Flyknit",
            category="Athletic Footwear / Running Shoes",
            color="Red / Burgundy / White",
            confidence_score=0.98,
        ),
        tags=["Nike", "Free RN", "Flyknit", "Running Shoes", "Red Sneakers"],
    )


def test_is_noise_item():
    assert is_noise_item(
        "History of Nike - Reading Comprehension Worksheet - No Prep Sub",
        "https://teacherspayteachers.com/Product/123",
    )
    assert is_noise_item(
        "Nike Logo Free Vector Clipart Wallpaper",
        "https://wallpapers.com/pic.jpg",
    )
    assert not is_noise_item(
        "Nike Free RN Flyknit 2017",
        "https://goat.com/sneakers/free-rn-flyknit-2017",
    )


def test_classify_exact_match():
    analysis = _make_analysis()
    match = EnrichedCommerceMatch(
        title="Nike Free RN Flyknit 2017",
        direct_url="https://goat.com/sneakers/free-rn-flyknit-2017",
        brand="Nike",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$120.00", amount=120.0, currency="USD"),
    )
    rel = classify_match_relevance(match, analysis)
    assert rel == MatchRelevance.EXACT_MATCH


def test_classify_similar_product():
    analysis = _make_analysis()
    # Different model of Nike shoe
    match = EnrichedCommerceMatch(
        title="Nike Air Zoom Pegasus 38",
        direct_url="https://nike.com/t/pegasus-38",
        brand="Nike",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$130.00", amount=130.0, currency="USD"),
    )
    rel = classify_match_relevance(match, analysis)
    assert rel == MatchRelevance.SIMILAR


def test_classify_noise_worksheet_excluded_from_exact():
    analysis = _make_analysis()
    # TPT educational worksheet with $2.00 price
    match = EnrichedCommerceMatch(
        title="History of Nike - Reading Comprehension Worksheet - No Prep Sub",
        direct_url="https://teacherspayteachers.com/Product/123",
        brand="Dallas Penner",
        page_type=PageType.PRODUCT,  # Even if mistakenly classified as product by merchant tag
        price=NormalizedPrice(raw="$2.00", amount=2.0, currency="USD"),
    )
    rel = classify_match_relevance(match, analysis)
    # Must be categorized as reference or unrelated, never exact_match
    assert rel in (MatchRelevance.REFERENCE, MatchRelevance.UNRELATED)


def test_classify_unrelated_accessory():
    analysis = _make_analysis()
    match = EnrichedCommerceMatch(
        title="Beats Studio Pro Wireless Headphones",
        direct_url="https://apple.com/beats-studio-pro",
        brand="Beats",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$24.95", amount=24.95, currency="CAD"),
    )
    rel = classify_match_relevance(match, analysis)
    assert rel == MatchRelevance.UNRELATED


def test_recompute_market_summary_excludes_noise():
    # 1. Real exact match: GOAT $120
    exact = EnrichedCommerceMatch(
        title="Nike Free RN Flyknit 2017",
        direct_url="https://goat.com/sneakers/free-rn-flyknit-2017",
        brand="Nike",
        merchant_name="GOAT",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$120.00", amount=120.0, currency="USD"),
        relevance=MatchRelevance.EXACT_MATCH,
    )

    # 2. Fake noise deal: TPT $2 worksheet
    worksheet = EnrichedCommerceMatch(
        title="History of Nike - Reading Comprehension Worksheet",
        direct_url="https://teacherspayteachers.com/Product/123",
        merchant_name="TPT",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$2.00", amount=2.0, currency="USD"),
        relevance=MatchRelevance.REFERENCE,
    )

    # 3. Random demo store: $3064
    shopify_demo = EnrichedCommerceMatch(
        title="Reel Store - Shopify Theme Test",
        direct_url="https://reelstore.com/demo",
        merchant_name="Reel Store",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$3064.00", amount=3064.0, currency="USD"),
        relevance=MatchRelevance.UNRELATED,
    )

    items = [worksheet, exact, shopify_demo]
    initial_summary = CommerceSummary(total_matches=3, currency="USD")

    cleaned_summary = recompute_market_summary(items, initial_summary)

    # The verified pricing MUST strictly use exact matches when available
    assert cleaned_summary.total_priced_matches == 1
    assert cleaned_summary.min_price == 120.0
    assert cleaned_summary.max_price == 120.0
    assert cleaned_summary.avg_price == 120.0
    # Best deal must be GOAT, not the $2.00 worksheet!
    assert cleaned_summary.best_deal is not None
    assert cleaned_summary.best_deal.merchant_name == "GOAT"
    assert cleaned_summary.best_deal.price is not None
    assert cleaned_summary.best_deal.price.amount == 120.0


def test_sort_commerce_items():
    item_ref = EnrichedCommerceMatch(
        title="Nike Free Review Blog",
        page_type=PageType.ARTICLE,
        relevance=MatchRelevance.REFERENCE,
        match_score=95,
    )
    item_sim = EnrichedCommerceMatch(
        title="Nike Free RN 2018",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$90", amount=90.0, currency="USD"),
        relevance=MatchRelevance.SIMILAR,
        match_score=80,
    )
    item_exact = EnrichedCommerceMatch(
        title="Nike Free RN Flyknit",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$120", amount=120.0, currency="USD"),
        relevance=MatchRelevance.EXACT_MATCH,
        match_score=90,
    )

    sorted_list = sort_commerce_items([item_ref, item_sim, item_exact])
    assert sorted_list[0] == item_exact
    assert sorted_list[1] == item_sim
    assert sorted_list[2] == item_ref


def test_process_commerce_relevance_end_to_end():
    analysis = _make_analysis()
    items = [
        EnrichedCommerceMatch(
            title="History of Nike - Reading Comprehension Worksheet",
            direct_url="https://teacherspayteachers.com/Product/123",
            merchant_name="TPT",
            page_type=PageType.PRODUCT,
            price=NormalizedPrice(raw="$2.00", amount=2.0, currency="USD"),
        ),
        EnrichedCommerceMatch(
            title="Nike Free RN Flyknit 2017",
            direct_url="https://goat.com/sneakers/free-rn-flyknit-2017",
            brand="Nike",
            merchant_name="GOAT",
            page_type=PageType.PRODUCT,
            price=NormalizedPrice(raw="$120.00", amount=120.0, currency="USD"),
        ),
    ]
    commerce = CommerceIntelligence(
        summary=CommerceSummary(total_matches=2, currency="USD"),
        items=items,
    )

    result = process_commerce_relevance(commerce, analysis)

    assert result.items[0].title == "Nike Free RN Flyknit 2017"
    assert result.items[0].relevance == MatchRelevance.EXACT_MATCH
    assert result.items[1].relevance == MatchRelevance.REFERENCE
    assert result.summary.best_deal is not None
    assert result.summary.best_deal.merchant_name == "GOAT"
    assert result.summary.min_price == 120.0


def test_classify_luxury_watch_agnostic():
    watch_analysis = VisualAnalysis(
        summary="Rolex Submariner Date 126610LN luxury dive watch.",
        attributes=ProductAttributes(
            brand="Rolex",
            model_or_name="Submariner Date 126610LN",
            category="Luxury Watches / Diving Watches",
            color="Black Dial / Silver Oystersteel",
        ),
        tags=["Rolex", "Submariner", "126610LN", "Luxury Watch", "Diver"],
    )

    exact_item = EnrichedCommerceMatch(
        title="Rolex Submariner Date 126610LN 41mm Oystersteel",
        brand="Rolex",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$14,500", amount=14500.0, currency="USD"),
    )
    assert classify_match_relevance(exact_item, watch_analysis) == MatchRelevance.EXACT_MATCH

    similar_item = EnrichedCommerceMatch(
        title="Rolex Cosmograph Daytona 116500LN",
        brand="Rolex",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$31,000", amount=31000.0, currency="USD"),
    )
    assert classify_match_relevance(similar_item, watch_analysis) == MatchRelevance.SIMILAR

    ref_item = EnrichedCommerceMatch(
        title="History and Evolution of the Rolex Submariner",
        brand="Rolex",
        page_type=PageType.ARTICLE,
    )
    assert classify_match_relevance(ref_item, watch_analysis) == MatchRelevance.REFERENCE

    unrelated_item = EnrichedCommerceMatch(
        title="Leather Watch Strap 20mm Replacement",
        brand="Barton",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$25", amount=25.0, currency="USD"),
    )
    assert classify_match_relevance(unrelated_item, watch_analysis) == MatchRelevance.UNRELATED


def test_classify_electronics_agnostic():
    audio_analysis = VisualAnalysis(
        summary="Sony WH-1000XM5 wireless noise canceling headphones in silver finish.",
        attributes=ProductAttributes(
            brand="Sony",
            model_or_name="WH-1000XM5",
            category="Wireless Noise Canceling Headphones",
            color="Silver",
        ),
        tags=["Sony", "WH-1000XM5", "Headphones", "Noise Canceling", "Bluetooth"],
    )

    exact_headphone = EnrichedCommerceMatch(
        title="Sony WH-1000XM5 Wireless Noise Canceling Headphones - Silver",
        brand="Sony",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$399.99", amount=399.99, currency="USD"),
    )
    assert classify_match_relevance(exact_headphone, audio_analysis) == MatchRelevance.EXACT_MATCH

    competing_headphone = EnrichedCommerceMatch(
        title="Bose QuietComfort 45 Wireless Headphones",
        brand="Bose",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$329.00", amount=329.0, currency="USD"),
    )
    # Different brand, but category tokens ("headphones", "wireless") overlap
    assert classify_match_relevance(competing_headphone, audio_analysis) == MatchRelevance.SIMILAR


def test_classify_furniture_agnostic():
    chair_analysis = VisualAnalysis(
        summary="Herman Miller Aeron ergonomic mesh office chair.",
        attributes=ProductAttributes(
            brand="Herman Miller",
            model_or_name="Aeron Chair",
            category="Ergonomic Office Chairs / Task Seating",
            color="Mineral / Satin Aluminum",
        ),
        tags=["Herman Miller", "Aeron", "Office Chair", "Ergonomic Seating"],
    )

    exact_chair = EnrichedCommerceMatch(
        title="Herman Miller Aeron Ergonomic Office Chair Size B",
        brand="Herman Miller",
        page_type=PageType.PRODUCT,
        price=NormalizedPrice(raw="$1,450.00", amount=1450.0, currency="USD"),
    )
    assert classify_match_relevance(exact_chair, chair_analysis) == MatchRelevance.EXACT_MATCH


def test_process_commerce_relevance_with_ai_evaluations():
    from google_lens_scraper.models import CandidateMatchEvaluation

    analysis = _make_analysis()
    analysis.match_evaluations = [
        CandidateMatchEvaluation(
            index=0,
            relevance=MatchRelevance.EXACT_MATCH,
            reason="Direct marketplace listing for identical sneaker",
        ),
        CandidateMatchEvaluation(
            index=1,
            relevance=MatchRelevance.REFERENCE,
            reason="Worksheet document",
        ),
    ]
    items = [
        EnrichedCommerceMatch(
            title="Nike Free RN Flyknit 2017",
            direct_url="https://goat.com/sneakers/free-rn-flyknit-2017",
            brand="Nike",
            merchant_name="GOAT",
            page_type=PageType.PRODUCT,
            price=NormalizedPrice(raw="$120.00", amount=120.0, currency="USD"),
        ),
        EnrichedCommerceMatch(
            title="History of Nike - Reading Comprehension Worksheet",
            direct_url="https://teacherspayteachers.com/Product/123",
            merchant_name="TPT",
            page_type=PageType.PRODUCT,
            price=NormalizedPrice(raw="$2.00", amount=2.0, currency="USD"),
        ),
    ]
    commerce = CommerceIntelligence(
        summary=CommerceSummary(total_matches=2, currency="USD"),
        items=items,
    )

    result = process_commerce_relevance(commerce, analysis)

    assert result.summary.target_product is not None
    assert "Nike" in result.summary.target_product
    assert result.items[0].relevance == MatchRelevance.EXACT_MATCH
    assert result.items[0].relevance_reason == "Direct marketplace listing for identical sneaker"
    assert result.items[1].relevance == MatchRelevance.REFERENCE
