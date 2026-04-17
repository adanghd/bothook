import json
from pathlib import Path
from typing import Dict

from ratecard.core.models import ContentType, Platform, PlatformStats

# --- Content type multipliers ---
CONTENT_MULTIPLIERS: Dict[ContentType, float] = {
    ContentType.IG_FEED:        1.0,
    ContentType.IG_STORY:       0.4,
    ContentType.IG_REEL:        1.3,
    ContentType.IG_HIGHLIGHT:   0.6,
    ContentType.TT_VIDEO:       1.0,
    ContentType.TT_DUET:        0.7,
    ContentType.TT_LIVE:        0.8,
    ContentType.YT_DEDICATED:   2.5,
    ContentType.YT_INTEGRATION: 1.2,
    ContentType.YT_SHORT:       0.5,
    ContentType.YT_COMMUNITY:   0.3,
    ContentType.TW_TWEET:       0.4,
    ContentType.TW_THREAD:      0.7,
    ContentType.LI_POST:        1.0,
    ContentType.LI_ARTICLE:     1.5,
    ContentType.FB_POST:        0.6,
    ContentType.FB_STORY:       0.35,
}

# --- Add-on multipliers ---
EXCLUSIVITY_ADDONS: Dict[int, float] = {
    30: 0.25,
    60: 0.40,
    90: 0.60,
}

USAGE_RIGHTS_ADDONS: Dict[int, float] = {
    30: 0.15,
    60: 0.25,
    90: 0.35,
}

BUNDLE_DISCOUNTS: Dict[int, float] = {
    1: 0.0,
    2: 0.05,
    3: 0.10,
    4: 0.15,
    5: 0.18,
    6: 0.20,
}

# --- Minimum floor prices (IDR) ---
MINIMUM_RATES: Dict[ContentType, float] = {
    ContentType.IG_FEED:          500_000,
    ContentType.IG_STORY:         200_000,
    ContentType.IG_REEL:          750_000,
    ContentType.IG_HIGHLIGHT:     300_000,
    ContentType.TT_VIDEO:         500_000,
    ContentType.TT_DUET:          350_000,
    ContentType.TT_LIVE:          400_000,
    ContentType.YT_DEDICATED:   2_000_000,
    ContentType.YT_INTEGRATION: 1_000_000,
    ContentType.YT_SHORT:         400_000,
    ContentType.YT_COMMUNITY:     150_000,
    ContentType.TW_TWEET:         150_000,
    ContentType.TW_THREAD:        300_000,
    ContentType.LI_POST:          400_000,
    ContentType.LI_ARTICLE:       600_000,
    ContentType.FB_POST:          250_000,
    ContentType.FB_STORY:         150_000,
}


def load_defaults(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def calculate_rate(
    stats: PlatformStats,
    content_type: ContentType,
    quantity: int = 1,
    exclusivity_days: int = 0,
    usage_rights_days: int = 0,
    defaults: dict = None,
) -> float:
    """
    Calculate endorsement rate for a single content type.
    Returns final price in IDR, rounded to nearest Rp 1.000.
    """
    if defaults is None:
        raise ValueError("defaults dict required (load from platform_defaults.json)")

    platform_key = stats.platform.value
    cpm = defaults["cpm_baselines_idr"][platform_key]
    benchmark_er = defaults["benchmark_engagement_rates"][platform_key]
    er_weight = defaults["er_weight"]

    # Base: impressions-based CPM
    base = (stats.avg_monthly_impressions / 1000) * cpm

    # Engagement rate multiplier
    if benchmark_er > 0:
        er_multiplier = 1 + (stats.engagement_rate / benchmark_er) * er_weight
    else:
        er_multiplier = 1.0

    # Content type factor
    content_factor = CONTENT_MULTIPLIERS.get(content_type, 1.0)

    rate = base * er_multiplier * content_factor

    # Apply floor price
    rate = max(rate, MINIMUM_RATES.get(content_type, 0))

    # Add-ons applied on top of base rate
    if exclusivity_days > 0:
        addon = EXCLUSIVITY_ADDONS.get(exclusivity_days, 0.60)
        rate *= (1 + addon)

    if usage_rights_days > 0:
        addon = USAGE_RIGHTS_ADDONS.get(usage_rights_days, 0.35)
        rate *= (1 + addon)

    # Multiply by quantity
    rate *= quantity

    # Round to nearest Rp 1.000
    return round(rate, -3)


def get_bundle_discount(num_platforms: int) -> float:
    """Return bundle discount fraction for given number of platforms."""
    capped = min(num_platforms, 6)
    return BUNDLE_DISCOUNTS.get(capped, 0.0)


def format_idr(amount: float) -> str:
    """Format number as Indonesian Rupiah string, e.g. Rp 2.500.000"""
    amount_int = int(amount)
    formatted = f"{amount_int:,}".replace(",", ".")
    return f"Rp {formatted}"


# IDR to USD exchange rate (configurable)
IDR_TO_USD_RATE = 16_500


def format_usd(amount: float) -> str:
    """Format number as USD string, e.g. $807.88"""
    usd = amount / IDR_TO_USD_RATE
    if usd >= 1:
        return f"${usd:,.2f}"
    return f"${usd:.2f}"


def format_price(amount: float, lang: str = "id") -> str:
    """Format price based on language — IDR for 'id', USD for 'en'."""
    if lang == "en":
        return format_usd(amount)
    return format_idr(amount)


# ─────────────────────────────────────────
# Affiliate pricing
# ─────────────────────────────────────────

# Commission rate baselines per affiliate platform (IDR market, 2026)
# TikTok Shop biasanya komisi lebih tinggi, Shopee lebih bervariasi
AFFILIATE_BASE_COMMISSION: Dict[str, float] = {
    "tiktok_shop":      0.10,   # 10% baseline
    "shopee_affiliate": 0.07,   # 7% baseline
}

# Conversion rate tier thresholds (decimal)
CONVERSION_TIERS = [
    (0.05, 0.08),   # >=5% conv -> +8% commission bonus
    (0.03, 0.05),   # >=3% conv -> +5% commission bonus
    (0.01, 0.02),   # >=1% conv -> +2% commission bonus
]


def calculate_affiliate_rate(
    platform_value: str,
    avg_monthly_gmv: int,
    avg_conversion_rate: float,
    avg_commission_pct: float = 0.0,
) -> dict:
    """
    Hitung rekomendasi commission rate + projected earnings untuk affiliate deal.

    Returns dict:
        commission_min_pct / commission_target_pct / commission_max_pct  (decimal)
        projected_monthly_earning_min / target                            (IDR)
        base_fee_suggested                                                (IDR, rounded)
        min_campaign_value                                                (IDR GMV comit)
    """
    base = AFFILIATE_BASE_COMMISSION.get(platform_value, 0.08)

    # Bonus berdasarkan conversion strength (semakin tinggi conv, semakin bisa nego tinggi)
    conv_bonus = 0.0
    for threshold, bonus in CONVERSION_TIERS:
        if avg_conversion_rate >= threshold:
            conv_bonus = bonus
            break

    recommended_min = max(0.05, avg_commission_pct, base)
    recommended_target = min(0.25, base + conv_bonus)
    if recommended_target < recommended_min:
        recommended_target = recommended_min
    recommended_max = min(0.30, recommended_target + 0.05)

    # Base fee kecil (0.5% dari GMV, min Rp 500K)
    base_fee = max(500_000, avg_monthly_gmv * 0.005)
    base_fee = round(base_fee, -3)

    # Min campaign value: setengah dari avg bulanan GMV
    min_campaign = avg_monthly_gmv * 0.5
    min_campaign = round(min_campaign, -3)

    projected_min = round(avg_monthly_gmv * recommended_min, -3)
    projected_target = round(avg_monthly_gmv * recommended_target, -3)

    return {
        "commission_min_pct":          recommended_min,
        "commission_target_pct":       recommended_target,
        "commission_max_pct":          recommended_max,
        "projected_monthly_earning_min":    projected_min,
        "projected_monthly_earning_target": projected_target,
        "base_fee_suggested":          base_fee,
        "min_campaign_value":          min_campaign,
    }
