from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"


PLATFORM_LABELS = {
    Platform.INSTAGRAM: "Instagram",
    Platform.TIKTOK: "TikTok",
    Platform.YOUTUBE: "YouTube",
    Platform.TWITTER: "Twitter / X",
    Platform.LINKEDIN: "LinkedIn",
    Platform.FACEBOOK: "Facebook",
}


class ContentType(str, Enum):
    # Instagram
    IG_FEED = "ig_feed"
    IG_STORY = "ig_story"
    IG_REEL = "ig_reel"
    IG_HIGHLIGHT = "ig_highlight"
    # TikTok
    TT_VIDEO = "tt_video"
    TT_DUET = "tt_duet"
    TT_LIVE = "tt_live"
    # YouTube
    YT_DEDICATED = "yt_dedicated"
    YT_INTEGRATION = "yt_integration"
    YT_SHORT = "yt_short"
    YT_COMMUNITY = "yt_community"
    # Twitter / X
    TW_TWEET = "tw_tweet"
    TW_THREAD = "tw_thread"
    # LinkedIn
    LI_POST = "li_post"
    LI_ARTICLE = "li_article"
    # Facebook
    FB_POST = "fb_post"
    FB_STORY = "fb_story"


CONTENT_TYPE_LABELS = {
    ContentType.IG_FEED:        "Instagram Feed Post",
    ContentType.IG_STORY:       "Instagram Story",
    ContentType.IG_REEL:        "Instagram Reel",
    ContentType.IG_HIGHLIGHT:   "Instagram Highlight",
    ContentType.TT_VIDEO:       "TikTok Video",
    ContentType.TT_DUET:        "TikTok Duet",
    ContentType.TT_LIVE:        "TikTok Live Mention",
    ContentType.YT_DEDICATED:   "YouTube Dedicated Video",
    ContentType.YT_INTEGRATION: "YouTube Integration/Mention",
    ContentType.YT_SHORT:       "YouTube Short",
    ContentType.YT_COMMUNITY:   "YouTube Community Post",
    ContentType.TW_TWEET:       "Tweet / X Post",
    ContentType.TW_THREAD:      "Twitter / X Thread",
    ContentType.LI_POST:        "LinkedIn Post",
    ContentType.LI_ARTICLE:     "LinkedIn Article",
    ContentType.FB_POST:        "Facebook Post",
    ContentType.FB_STORY:       "Facebook Story",
}

# Map each content type to its platform
CONTENT_TYPE_PLATFORM = {
    ContentType.IG_FEED:        Platform.INSTAGRAM,
    ContentType.IG_STORY:       Platform.INSTAGRAM,
    ContentType.IG_REEL:        Platform.INSTAGRAM,
    ContentType.IG_HIGHLIGHT:   Platform.INSTAGRAM,
    ContentType.TT_VIDEO:       Platform.TIKTOK,
    ContentType.TT_DUET:        Platform.TIKTOK,
    ContentType.TT_LIVE:        Platform.TIKTOK,
    ContentType.YT_DEDICATED:   Platform.YOUTUBE,
    ContentType.YT_INTEGRATION: Platform.YOUTUBE,
    ContentType.YT_SHORT:       Platform.YOUTUBE,
    ContentType.YT_COMMUNITY:   Platform.YOUTUBE,
    ContentType.TW_TWEET:       Platform.TWITTER,
    ContentType.TW_THREAD:      Platform.TWITTER,
    ContentType.LI_POST:        Platform.LINKEDIN,
    ContentType.LI_ARTICLE:     Platform.LINKEDIN,
    ContentType.FB_POST:        Platform.FACEBOOK,
    ContentType.FB_STORY:       Platform.FACEBOOK,
}


class TierName(str, Enum):
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# ── Affiliate ────────────────────────────────────────────

class AffiliatePlatform(str, Enum):
    TIKTOK_SHOP = "tiktok_shop"
    SHOPEE_AFFILIATE = "shopee_affiliate"


AFFILIATE_PLATFORM_LABELS = {
    AffiliatePlatform.TIKTOK_SHOP:      "TikTok Shop",
    AffiliatePlatform.SHOPEE_AFFILIATE: "Shopee Affiliate",
}


AFFILIATE_CATEGORIES = [
    "Fashion",
    "Beauty & Skincare",
    "Tech & Gadget",
    "Food & Beverage",
    "Home & Living",
    "Lifestyle",
    "Health & Wellness",
    "Parenting & Kids",
    "Sports & Outdoor",
    "Books & Education",
]


class PricingModel(str, Enum):
    FLAT = "flat"              # endorsement: flat fee only
    COMMISSION = "commission"  # affiliate: commission % only
    HYBRID = "hybrid"          # flat base + commission %


PRICING_MODEL_LABELS = {
    PricingModel.FLAT:       "Flat Fee (Endorsement)",
    PricingModel.COMMISSION: "Commission Only (Affiliate)",
    PricingModel.HYBRID:     "Hybrid (Base + Commission)",
}


# ── Payment Terms ──────────────────────────────────────────

class PaymentScheme(str, Enum):
    FULL_UPFRONT = "full_upfront"      # 100% bayar di depan
    DP_50 = "dp_50"                    # 50% DP, 50% setelah tayang
    DP_30 = "dp_30"                    # 30% DP, 70% setelah tayang (+5% fee)
    POST_DELIVERY = "post_delivery"    # 100% bayar setelah jadi (+10% fee)


PAYMENT_SCHEME_LABELS = {
    PaymentScheme.FULL_UPFRONT: "100% Di Depan",
    PaymentScheme.DP_50:        "DP 50% + 50% Setelah Tayang",
    PaymentScheme.DP_30:        "DP 30% + 70% Setelah Tayang",
    PaymentScheme.POST_DELIVERY: "100% Setelah Jadi",
}

PAYMENT_SCHEME_LABELS_EN = {
    PaymentScheme.FULL_UPFRONT: "100% Upfront",
    PaymentScheme.DP_50:        "50% Deposit + 50% After Delivery",
    PaymentScheme.DP_30:        "30% Deposit + 70% After Delivery",
    PaymentScheme.POST_DELIVERY: "100% After Delivery",
}

# Fee markup (fraction) — creator's risk compensation
PAYMENT_SCHEME_FEES = {
    PaymentScheme.FULL_UPFRONT: 0.0,    # no fee
    PaymentScheme.DP_50:        0.0,    # standard, no fee
    PaymentScheme.DP_30:        0.05,   # +5%
    PaymentScheme.POST_DELIVERY: 0.10,  # +10%
}

# DP percentage (fraction)
PAYMENT_SCHEME_DP = {
    PaymentScheme.FULL_UPFRONT: 1.0,
    PaymentScheme.DP_50:        0.5,
    PaymentScheme.DP_30:        0.3,
    PaymentScheme.POST_DELIVERY: 0.0,
}


# ── Add-ons & Tier Bonuses ────────────────────────────────

class AddOnType(str, Enum):
    RAW_FOOTAGE = "raw_footage"
    SEO_SCRIPT = "seo_script"
    WEBSITE_FEATURE = "website_feature"
    CROSS_PROMO = "cross_promo"
    WHITELISTING = "whitelisting"
    RUSH_DELIVERY = "rush_delivery"
    EXTRA_REVISION = "extra_revision"


ADDON_LABELS = {
    AddOnType.RAW_FOOTAGE:      "Raw Footage / File Mentah",
    AddOnType.SEO_SCRIPT:       "SEO Script & Caption",
    AddOnType.WEBSITE_FEATURE:  "Feature di Website Creator",
    AddOnType.CROSS_PROMO:      "Cross-Promote Platform Lain",
    AddOnType.WHITELISTING:     "Whitelisting (Izin Paid Ads)",
    AddOnType.RUSH_DELIVERY:    "Rush Delivery (< 3 hari)",
    AddOnType.EXTRA_REVISION:   "Revisi Tambahan (per round)",
}

ADDON_LABELS_EN = {
    AddOnType.RAW_FOOTAGE:      "Raw Footage",
    AddOnType.SEO_SCRIPT:       "SEO Script & Caption",
    AddOnType.WEBSITE_FEATURE:  "Website Feature",
    AddOnType.CROSS_PROMO:      "Cross-Platform Promotion",
    AddOnType.WHITELISTING:     "Whitelisting (Paid Ads License)",
    AddOnType.RUSH_DELIVERY:    "Rush Delivery (< 3 days)",
    AddOnType.EXTRA_REVISION:   "Extra Revision (per round)",
}

# Price as fraction of package base_price
ADDON_PRICE_PCT = {
    AddOnType.RAW_FOOTAGE:      0.15,   # +15%
    AddOnType.SEO_SCRIPT:       0.10,   # +10%
    AddOnType.WEBSITE_FEATURE:  0.20,   # +20%
    AddOnType.CROSS_PROMO:      0.10,   # +10%
    AddOnType.WHITELISTING:     0.25,   # +25%
    AddOnType.RUSH_DELIVERY:    0.30,   # +30%
    AddOnType.EXTRA_REVISION:   0.10,   # +10% per round
}

# What's included FREE per tier
TIER_BONUSES = {
    TierName.BRONZE: {
        "revision_rounds": 1,
        "included_addons": [],
        "delivery_days": 7,
        "perks": ["1x revisi", "Delivery 7 hari kerja"],
    },
    TierName.SILVER: {
        "revision_rounds": 2,
        "included_addons": [AddOnType.SEO_SCRIPT],
        "delivery_days": 5,
        "perks": ["2x revisi", "SEO caption included", "Delivery 5 hari kerja"],
    },
    TierName.GOLD: {
        "revision_rounds": 3,
        "included_addons": [
            AddOnType.SEO_SCRIPT,
            AddOnType.RAW_FOOTAGE,
            AddOnType.CROSS_PROMO,
            AddOnType.WEBSITE_FEATURE,
        ],
        "delivery_days": 3,
        "perks": [
            "3x revisi", "SEO script included", "Raw footage included",
            "Cross-promo included", "Feature di website",
            "Priority delivery 3 hari",
        ],
    },
}

TIER_BONUSES_EN = {
    TierName.BRONZE: {
        "perks": ["1x revision", "7 business days delivery"],
    },
    TierName.SILVER: {
        "perks": ["2x revisions", "SEO caption included", "5 business days delivery"],
    },
    TierName.GOLD: {
        "perks": [
            "3x revisions", "SEO script included", "Raw footage included",
            "Cross-promo included", "Website feature",
            "Priority 3-day delivery",
        ],
    },
}


@dataclass
class PlatformStats:
    platform: Platform
    followers: int = 0
    avg_views: int = 0
    engagement_rate: float = 0.0      # decimal: 0.045 = 4.5%
    avg_monthly_impressions: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class AffiliateStats:
    platform: AffiliatePlatform
    avg_monthly_gmv: int = 0              # IDR, rata-rata sales/bulan via affiliate link
    avg_conversion_rate: float = 0.0      # decimal: 0.03 = 3% (clicks -> sales)
    avg_commission_pct: float = 0.0       # decimal: 0.08 = 8% (avg commission earned)
    enabled: bool = True
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class CreatorProfile:
    id: int = 1
    name: str = ""
    niche: str = ""
    location: str = ""
    contact_email: str = ""
    logo_path: Optional[str] = None
    brand_color_hex: str = "#E91E8C"
    currency: str = "IDR"
    platform_stats: List[PlatformStats] = field(default_factory=list)
    affiliate_stats: List[AffiliateStats] = field(default_factory=list)
    affiliate_categories: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def get_stats(self, platform: Platform) -> Optional[PlatformStats]:
        for s in self.platform_stats:
            if s.platform == platform:
                return s
        return None

    def get_affiliate_stats(self, platform: AffiliatePlatform) -> Optional[AffiliateStats]:
        for s in self.affiliate_stats:
            if s.platform == platform:
                return s
        return None

    @property
    def has_affiliate(self) -> bool:
        return any(s.avg_monthly_gmv > 0 and s.enabled for s in self.affiliate_stats)


@dataclass
class PackageItem:
    content_type: ContentType
    quantity: int = 1
    unit_price: float = 0.0
    revision_rounds: int = 2
    usage_rights_days: int = 0
    exclusivity_days: int = 0


@dataclass
class PackageAddOn:
    addon_type: AddOnType
    price: float = 0.0
    quantity: int = 1
    included_in_tier: bool = False


@dataclass
class Package:
    id: Optional[int] = None
    tier: TierName = TierName.BRONZE
    name: str = ""
    items: List[PackageItem] = field(default_factory=list)
    addons: List[PackageAddOn] = field(default_factory=list)
    base_price: float = 0.0
    bundle_discount_pct: float = 0.0
    client_discount_pct: float = 0.0
    final_price: float = 0.0
    valid_days: int = 7
    notes: str = ""

    @property
    def total_items(self) -> int:
        return sum(i.quantity for i in self.items)

    @property
    def addon_total(self) -> float:
        return sum(a.price * a.quantity for a in self.addons if not a.included_in_tier)

    @property
    def included_addon_types(self) -> list:
        return [a.addon_type for a in self.addons if a.included_in_tier]


@dataclass
class AffiliateTerms:
    """Affiliate-specific deal terms (appended to Proposal when pricing_model != FLAT)."""
    commission_pct: float = 0.08           # e.g., 0.10 = 10%
    base_fee: float = 0.0                  # base fee IDR (0 if pure commission)
    min_campaign_value: float = 0.0        # minimum GMV klien harus comitted (IDR)
    categories: List[str] = field(default_factory=list)   # kategori produk yang dicover
    exclusivity_days: int = 0
    duration_days: int = 30                # campaign duration
    projected_gmv: float = 0.0             # est. GMV yang diproyeksikan
    projected_earning: float = 0.0         # est. rupiah yang didapat creator


@dataclass
class CustomAddOn:
    """User-defined add-on service for rate cards."""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    price_type: str = "percentage"    # "percentage" or "fixed"
    price_value: float = 0.0          # % of base price (e.g. 15.0 = 15%) or fixed IDR
    category: str = "influencer"      # "influencer" or "affiliate"
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Proposal:
    id: Optional[int] = None
    client_name: str = ""
    client_company: str = ""
    client_email: str = ""
    campaign_name: str = ""
    packages: List[Package] = field(default_factory=list)
    total_price: float = 0.0           # base price (before payment fee)
    discount_pct: float = 0.0
    status: ProposalStatus = ProposalStatus.DRAFT
    pricing_model: PricingModel = PricingModel.FLAT
    payment_scheme: PaymentScheme = PaymentScheme.DP_50
    affiliate_terms: Optional[AffiliateTerms] = None
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    notes: str = ""

    @property
    def payment_fee_pct(self) -> float:
        """Fee markup based on payment scheme."""
        return PAYMENT_SCHEME_FEES.get(self.payment_scheme, 0.0)

    @property
    def payment_fee_amount(self) -> float:
        """Fee amount in IDR."""
        return self.total_price * self.payment_fee_pct

    @property
    def grand_total(self) -> float:
        """Total price including payment fee."""
        return self.total_price + self.payment_fee_amount

    @property
    def dp_amount(self) -> float:
        """Down payment amount."""
        dp_pct = PAYMENT_SCHEME_DP.get(self.payment_scheme, 0.5)
        return self.grand_total * dp_pct

    @property
    def remaining_amount(self) -> float:
        """Remaining amount after DP."""
        return self.grand_total - self.dp_amount
