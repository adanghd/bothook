from typing import List, Optional

from ratecard.core.models import (
    ADDON_PRICE_PCT,
    TIER_BONUSES,
    AddOnType,
    ContentType,
    CreatorProfile,
    Package,
    PackageAddOn,
    PackageItem,
    Platform,
    TierName,
    CONTENT_TYPE_PLATFORM,
)
from ratecard.core.pricing import calculate_rate, get_bundle_discount

# Default content types per tier per platform
TIER_CONTENT_DEFAULTS = {
    TierName.BRONZE: {
        Platform.INSTAGRAM: [ContentType.IG_FEED],
        Platform.TIKTOK:    [ContentType.TT_VIDEO],
        Platform.YOUTUBE:   [ContentType.YT_INTEGRATION],
        Platform.TWITTER:   [ContentType.TW_TWEET],
        Platform.LINKEDIN:  [ContentType.LI_POST],
        Platform.FACEBOOK:  [ContentType.FB_POST],
    },
    TierName.SILVER: {
        Platform.INSTAGRAM: [ContentType.IG_FEED, ContentType.IG_STORY],
        Platform.TIKTOK:    [ContentType.TT_VIDEO],
        Platform.YOUTUBE:   [ContentType.YT_INTEGRATION, ContentType.YT_SHORT],
        Platform.TWITTER:   [ContentType.TW_TWEET, ContentType.TW_THREAD],
        Platform.LINKEDIN:  [ContentType.LI_POST],
        Platform.FACEBOOK:  [ContentType.FB_POST, ContentType.FB_STORY],
    },
    TierName.GOLD: {
        Platform.INSTAGRAM: [ContentType.IG_FEED, ContentType.IG_STORY, ContentType.IG_REEL],
        Platform.TIKTOK:    [ContentType.TT_VIDEO, ContentType.TT_LIVE],
        Platform.YOUTUBE:   [ContentType.YT_DEDICATED, ContentType.YT_SHORT],
        Platform.TWITTER:   [ContentType.TW_TWEET, ContentType.TW_THREAD],
        Platform.LINKEDIN:  [ContentType.LI_POST, ContentType.LI_ARTICLE],
        Platform.FACEBOOK:  [ContentType.FB_POST, ContentType.FB_STORY],
    },
}

TIER_CONFIG = {
    TierName.BRONZE: {
        "valid_days": 7,
        "revision_rounds": 1,
        "usage_rights_days": 0,
        "exclusivity_days": 0,
    },
    TierName.SILVER: {
        "valid_days": 14,
        "revision_rounds": 2,
        "usage_rights_days": 30,
        "exclusivity_days": 0,
    },
    TierName.GOLD: {
        "valid_days": 30,
        "revision_rounds": 3,
        "usage_rights_days": 60,
        "exclusivity_days": 30,
    },
}


def build_package(
    profile: CreatorProfile,
    tier: TierName,
    platforms: Optional[List[Platform]] = None,
    defaults: dict = None,
    client_discount_pct: float = 0.0,
    extra_addons: Optional[List[AddOnType]] = None,
    extra_revision_rounds: int = 0,
) -> Package:
    """
    Build a Package for the given tier using the creator's platform stats.
    If platforms is None, uses all platforms that have stats configured.
    extra_addons: additional paid add-ons beyond tier bonuses.
    extra_revision_rounds: paid extra revisions (each = +10% of base).
    """
    if defaults is None:
        raise ValueError("defaults dict required")

    if platforms is None:
        platforms = [s.platform for s in profile.platform_stats if s.avg_monthly_impressions > 0]

    config = TIER_CONFIG[tier]
    content_defaults = TIER_CONTENT_DEFAULTS[tier]

    items: List[PackageItem] = []

    for platform in platforms:
        stats = profile.get_stats(platform)
        if stats is None or stats.avg_monthly_impressions == 0:
            continue

        for content_type in content_defaults.get(platform, []):
            unit_price = calculate_rate(
                stats=stats,
                content_type=content_type,
                quantity=1,
                exclusivity_days=config["exclusivity_days"],
                usage_rights_days=config["usage_rights_days"],
                defaults=defaults,
            )
            item = PackageItem(
                content_type=content_type,
                quantity=1,
                unit_price=unit_price,
                revision_rounds=config["revision_rounds"],
                usage_rights_days=config["usage_rights_days"],
                exclusivity_days=config["exclusivity_days"],
            )
            items.append(item)

    base_price = sum(i.unit_price * i.quantity for i in items)

    # ── Build addons ──────────────────────────────────────
    tier_bonus = TIER_BONUSES.get(tier, {})
    included_types = set(tier_bonus.get("included_addons", []))
    addons: List[PackageAddOn] = []

    # Tier-included addons (free)
    for addon_type in included_types:
        addons.append(PackageAddOn(
            addon_type=addon_type,
            price=round(base_price * ADDON_PRICE_PCT.get(addon_type, 0), -3),
            quantity=1,
            included_in_tier=True,
        ))

    # User-selected paid extras
    if extra_addons:
        for addon_type in extra_addons:
            if addon_type in included_types:
                continue  # already free
            if addon_type == AddOnType.EXTRA_REVISION:
                continue  # handled below
            price = round(base_price * ADDON_PRICE_PCT.get(addon_type, 0), -3)
            addons.append(PackageAddOn(
                addon_type=addon_type,
                price=price,
                quantity=1,
                included_in_tier=False,
            ))

    # Extra revision rounds
    if extra_revision_rounds > 0:
        rev_price = round(base_price * ADDON_PRICE_PCT.get(AddOnType.EXTRA_REVISION, 0.10), -3)
        addons.append(PackageAddOn(
            addon_type=AddOnType.EXTRA_REVISION,
            price=rev_price,
            quantity=extra_revision_rounds,
            included_in_tier=False,
        ))

    paid_addon_total = sum(a.price * a.quantity for a in addons if not a.included_in_tier)

    # ── Pricing ───────────────────────────────────────────
    num_platforms = len(set(CONTENT_TYPE_PLATFORM[i.content_type] for i in items)) if items else 0
    bundle_discount = get_bundle_discount(num_platforms)

    price_after_bundle = base_price * (1 - bundle_discount)
    final_price = (price_after_bundle + paid_addon_total) * (1 - client_discount_pct)
    final_price = round(final_price, -3)

    tier_labels = {
        TierName.BRONZE: "Bronze — Lite Package",
        TierName.SILVER: "Silver — Standard Package",
        TierName.GOLD:   "Gold — Premium Package",
    }

    return Package(
        tier=tier,
        name=tier_labels[tier],
        items=items,
        addons=addons,
        base_price=base_price,
        bundle_discount_pct=bundle_discount,
        client_discount_pct=client_discount_pct,
        final_price=final_price,
        valid_days=config["valid_days"],
    )


def build_all_packages(
    profile: CreatorProfile,
    defaults: dict,
    platforms: Optional[List[Platform]] = None,
    client_discount_pct: float = 0.0,
) -> List[Package]:
    """Build Bronze, Silver, and Gold packages for a profile."""
    packages = []
    for tier in [TierName.BRONZE, TierName.SILVER, TierName.GOLD]:
        pkg = build_package(
            profile=profile,
            tier=tier,
            platforms=platforms,
            defaults=defaults,
            client_discount_pct=client_discount_pct,
        )
        packages.append(pkg)
    return packages
