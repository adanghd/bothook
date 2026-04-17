"""
PDF Rate Card & Proposal Generator
Uses ReportLab to produce professional A4 PDF documents.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ratecard.core.models import (
    ADDON_LABELS,
    ADDON_LABELS_EN,
    AFFILIATE_PLATFORM_LABELS,
    CONTENT_TYPE_LABELS,
    PAYMENT_SCHEME_LABELS,
    PLATFORM_LABELS,
    PRICING_MODEL_LABELS,
    TIER_BONUSES,
    TIER_BONUSES_EN,
    ContentType,
    CreatorProfile,
    Package,
    PackageItem,
    PaymentScheme,
    Platform,
    PricingModel,
    Proposal,
    TierName,
    CONTENT_TYPE_PLATFORM,
)
from ratecard.core.pricing import calculate_affiliate_rate, format_idr, format_price


# ── Color palette ──────────────────────────────────────────
BRAND_PINK = colors.HexColor("#E91E8C")
BRAND_DARK = colors.HexColor("#2D2D3F")
BRAND_LIGHT_BG = colors.HexColor("#FDF2F8")
BRAND_LIGHT_PINK = colors.HexColor("#FCE7F3")

GRAY_50 = colors.HexColor("#F9FAFB")
GRAY_100 = colors.HexColor("#F3F4F6")
GRAY_200 = colors.HexColor("#E5E7EB")
GRAY_300 = colors.HexColor("#D1D5DB")
GRAY_400 = colors.HexColor("#9CA3AF")
GRAY_500 = colors.HexColor("#6B7280")
GRAY_600 = colors.HexColor("#4B5563")
GRAY_700 = colors.HexColor("#374151")
GRAY_800 = colors.HexColor("#1F2937")
GRAY_900 = colors.HexColor("#111827")

GREEN_600 = colors.HexColor("#16A34A")
GREEN_50 = colors.HexColor("#F0FDF4")
AMBER_600 = colors.HexColor("#D97706")

TIER_COLORS = {
    TierName.BRONZE: colors.HexColor("#B45309"),
    TierName.SILVER: colors.HexColor("#64748B"),
    TierName.GOLD:   colors.HexColor("#B8860B"),
}
TIER_BG_COLORS = {
    TierName.BRONZE: colors.HexColor("#FEF3C7"),
    TierName.SILVER: colors.HexColor("#F1F5F9"),
    TierName.GOLD:   colors.HexColor("#FFFBEB"),
}
TIER_EMOJI = {
    TierName.BRONZE: "BRONZE",
    TierName.SILVER: "SILVER",
    TierName.GOLD:   "GOLD",
}


# ── Translations ───────────────────────────────────────────
_T = {
    "id": {
        "influencer_rc": "INFLUENCER RATE CARD",
        "affiliate_rc": "AFFILIATE RATE CARD",
        "rate_card": "RATE CARD",
        "influencer_sub": "Endorsement & Sponsored Content Pricing",
        "affiliate_sub": "TikTok Shop & Shopee Affiliate Commission Rates",
        "all_sub": "Endorsement, Sponsored Content & Affiliate Pricing",
        "platform_stats": "Platform Statistics",
        "followers": "Followers",
        "avg_views": "Avg Views",
        "eng_rate": "Eng. Rate",
        "impressions_mo": "Impressions/mo",
        "packages": "Paket Endorsement",
        "content": "Konten",
        "qty": "Qty",
        "unit_price": "Harga Satuan",
        "subtotal": "Subtotal",
        "subtotal_content": "Subtotal Konten",
        "bundle_discount": "Bundle Discount",
        "client_discount": "Diskon Klien",
        "total": "TOTAL",
        "includes": "Termasuk",
        "quote_valid": "Quote berlaku {days} hari sejak tanggal dokumen.",
        "addons_title": "Add-ons (opsional)",
        "addon": "Add-on",
        "detail": "Detail",
        "extra_cost": "Biaya Tambahan",
        "exclusivity": "Exclusivity (kategori produk)",
        "usage_rights": "Usage Rights (brand repost)",
        "days": "hari",
        "custom": "Custom",
        "terms_title": "Syarat & Ketentuan",
        "payment": "Pembayaran",
        "revision": "Revisi",
        "notes": "Catatan",
        "footer": "Rate Card — {name}  |  Dibuat {date}  |  Berlaku hingga {valid}",
        "commission_rates": "Commission Rates & Projected Earnings",
        "minimum": "MINIMUM",
        "target": "TARGET",
        "maximum": "MAXIMUM",
        "projected_earning": "PROJECTED EARNING",
        "per_month_target": "per bulan (target)",
        "base_fee": "BASE FEE",
        "suggested_upfront": "suggested upfront",
        "min_campaign_gmv": "Min. campaign GMV",
        "avg_gmv_month": "Avg GMV/bulan",
        "top_categories": "Kategori unggulan",
        "deal_schemes": "3 Skema Deal",
        "commission_only": "Commission Only (tanpa upfront)",
        "hybrid": "Hybrid (base fee + komisi)",
        "flat_fee": "Flat Fee (rate card endorsement)",
        "usage_d": "Usage {d}d",
        "excl_d": "Excl. {d}d",
    },
    "en": {
        "influencer_rc": "INFLUENCER RATE CARD",
        "affiliate_rc": "AFFILIATE RATE CARD",
        "rate_card": "RATE CARD",
        "influencer_sub": "Endorsement & Sponsored Content Pricing",
        "affiliate_sub": "TikTok Shop & Shopee Affiliate Commission Rates",
        "all_sub": "Endorsement, Sponsored Content & Affiliate Pricing",
        "platform_stats": "Platform Statistics",
        "followers": "Followers",
        "avg_views": "Avg Views",
        "eng_rate": "Eng. Rate",
        "impressions_mo": "Impressions/mo",
        "packages": "Endorsement Packages",
        "content": "Content",
        "qty": "Qty",
        "unit_price": "Unit Price",
        "subtotal": "Subtotal",
        "subtotal_content": "Content Subtotal",
        "bundle_discount": "Bundle Discount",
        "client_discount": "Client Discount",
        "total": "TOTAL",
        "includes": "Includes",
        "quote_valid": "Quote valid for {days} days from document date.",
        "addons_title": "Add-ons (optional)",
        "addon": "Add-on",
        "detail": "Detail",
        "extra_cost": "Extra Cost",
        "exclusivity": "Exclusivity (product category)",
        "usage_rights": "Usage Rights (brand repost)",
        "days": "days",
        "custom": "Custom",
        "terms_title": "Terms & Conditions",
        "payment": "Payment",
        "revision": "Revisions",
        "notes": "Notes",
        "footer": "Rate Card — {name}  |  Created {date}  |  Valid until {valid}",
        "commission_rates": "Commission Rates & Projected Earnings",
        "minimum": "MINIMUM",
        "target": "TARGET",
        "maximum": "MAXIMUM",
        "projected_earning": "PROJECTED EARNING",
        "per_month_target": "per month (target)",
        "base_fee": "BASE FEE",
        "suggested_upfront": "suggested upfront",
        "min_campaign_gmv": "Min. campaign GMV",
        "avg_gmv_month": "Avg GMV/month",
        "top_categories": "Top categories",
        "deal_schemes": "3 Deal Schemes",
        "commission_only": "Commission Only (no upfront)",
        "hybrid": "Hybrid (base fee + commission)",
        "flat_fee": "Flat Fee (endorsement rate card)",
        "usage_d": "Usage {d}d",
        "excl_d": "Excl. {d}d",
        "payment_terms_default": "50% deposit before production, 50% after content goes live",
        "revision_policy_default": "Max 2 revisions included per package",
        "additional_notes_default": "Prices are exclusive of VAT. Rates apply to 1 brand per content.",
    },
}


def _t(key: str, lang: str = "id", **kwargs) -> str:
    """Get translated string."""
    text = _T.get(lang, _T["id"]).get(key, _T["id"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text


def _hex_to_color(hex_str: str):
    hex_str = hex_str.lstrip("#")
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return colors.Color(r / 255, g / 255, b / 255)


def _load_template(template_path: Optional[Path]) -> dict:
    defaults = {
        "brand_color_hex": "#E91E8C",
        "accent_color_hex": "#333333",
        "font_name": "Helvetica",
        "currency_symbol": "Rp",
        "payment_terms": "50% DP, 50% setelah konten tayang",
        "revision_policy": "Maks 2x revisi termasuk dalam paket",
        "additional_notes": "Harga belum termasuk PPN. Rate berlaku untuk 1 brand per konten.",
    }
    if template_path and template_path.exists():
        with open(template_path) as f:
            loaded = json.load(f)
        defaults.update({k: v for k, v in loaded.items() if v is not None})
    return defaults


def _styles(brand_color, font_name: str = "Helvetica"):
    return {
        "title": ParagraphStyle(
            "title",
            fontName=f"{font_name}-Bold",
            fontSize=24,
            textColor=colors.white,
            spaceAfter=2,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName=font_name,
            fontSize=11,
            textColor=colors.Color(1, 1, 1, 0.85),
            spaceAfter=1,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName=f"{font_name}-Bold",
            fontSize=13,
            textColor=BRAND_DARK,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "section_badge": ParagraphStyle(
            "section_badge",
            fontName=f"{font_name}-Bold",
            fontSize=9,
            textColor=brand_color,
        ),
        "body": ParagraphStyle(
            "body",
            fontName=font_name,
            fontSize=9,
            textColor=GRAY_700,
            spaceAfter=2,
            leading=13,
        ),
        "small": ParagraphStyle(
            "small",
            fontName=font_name,
            fontSize=8,
            textColor=GRAY_500,
            spaceAfter=2,
            leading=11,
        ),
        "tier_title": ParagraphStyle(
            "tier_title",
            fontName=f"{font_name}-Bold",
            fontSize=12,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "price_big": ParagraphStyle(
            "price_big",
            fontName=f"{font_name}-Bold",
            fontSize=16,
            textColor=brand_color,
            alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName=font_name,
            fontSize=7,
            textColor=GRAY_400,
            alignment=TA_CENTER,
        ),
    }


# ── Helper: colored header banner ──────────────────────────

def _build_header_banner(profile: CreatorProfile, style: dict, brand_color, mode: str = "all", lang: str = "id") -> List:
    """Build a visually prominent header banner with creator info."""
    elements = []

    mode_keys = {"influencer": "influencer_rc", "affiliate": "affiliate_rc", "all": "rate_card"}
    sub_keys = {"influencer": "influencer_sub", "affiliate": "affiliate_sub", "all": "all_sub"}

    doc_date = datetime.now().strftime("%d %B %Y")
    label = _t(mode_keys.get(mode, "rate_card"), lang)
    sub_label = _t(sub_keys.get(mode, "all_sub"), lang)

    # Build banner content as a table with colored background
    name_para = Paragraph(
        profile.name or "Creator Name",
        ParagraphStyle("bn", fontName="Helvetica-Bold", fontSize=22, textColor=colors.white, leading=26),
    )
    type_para = Paragraph(
        f"<b>{label}</b>",
        ParagraphStyle("bt", fontName="Helvetica-Bold", fontSize=10, textColor=colors.Color(1, 1, 1, 0.7), spaceAfter=2),
    )

    info_parts = []
    if profile.niche:
        info_parts.append(profile.niche)
    if profile.location:
        info_parts.append(profile.location)
    if profile.contact_email:
        info_parts.append(profile.contact_email)
    info_text = "  |  ".join(info_parts)

    info_para = Paragraph(
        info_text,
        ParagraphStyle("bi", fontName="Helvetica", fontSize=9, textColor=colors.Color(1, 1, 1, 0.75)),
    )
    date_para = Paragraph(
        doc_date,
        ParagraphStyle("bd", fontName="Helvetica", fontSize=9, textColor=colors.Color(1, 1, 1, 0.6), alignment=TA_RIGHT),
    )

    # Two-column layout: left = name+info, right = date
    inner = Table(
        [[type_para, ""],
         [name_para, date_para],
         [info_para, ""]],
        colWidths=[12.5 * cm, 4.5 * cm],
    )
    inner.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (1, 1), (1, 1), "BOTTOM"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Wrap in outer table for colored background
    banner = Table([[inner]], colWidths=[18 * cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), brand_color),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    elements.append(banner)

    # Subtitle bar
    if sub_label:
        sub_para = Paragraph(
            sub_label,
            ParagraphStyle("sl", fontName="Helvetica", fontSize=8, textColor=GRAY_500, alignment=TA_CENTER),
        )
        sub_bar = Table([[sub_para]], colWidths=[18 * cm])
        sub_bar.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GRAY_50),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [0, 0, 4, 4]),
        ]))
        elements.append(sub_bar)

    elements.append(Spacer(1, 8 * mm))
    return elements


# ── Section header with accent line ────────────────────────

def _section_header(text: str, brand_color) -> List:
    """Create a styled section header with accent line."""
    elements = []
    elements.append(HRFlowable(width="100%", thickness=2, color=brand_color, spaceAfter=4))
    elements.append(Paragraph(
        text,
        ParagraphStyle("sh", fontName="Helvetica-Bold", fontSize=12, textColor=BRAND_DARK, spaceAfter=6),
    ))
    return elements


# ── Stats table ────────────────────────────────────────────

def _build_stats_table(profile: CreatorProfile, style: dict, brand_color, lang: str = "id") -> List:
    elements = []
    elements.extend(_section_header(_t("platform_stats", lang), brand_color))

    hdr_style = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)
    hdr_style_r = ParagraphStyle("thr", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_RIGHT)

    rows = [[
        Paragraph("Platform", hdr_style),
        Paragraph(_t("followers", lang), hdr_style_r),
        Paragraph(_t("avg_views", lang), hdr_style_r),
        Paragraph(_t("eng_rate", lang), hdr_style_r),
        Paragraph(_t("impressions_mo", lang), hdr_style_r),
    ]]

    cell_style = ParagraphStyle("cell", fontName="Helvetica", fontSize=9, textColor=GRAY_700)
    cell_style_r = ParagraphStyle("cellr", fontName="Helvetica", fontSize=9, textColor=GRAY_700, alignment=TA_RIGHT)
    cell_style_bold = ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_800)

    for s in profile.platform_stats:
        if s.followers == 0:
            continue
        rows.append([
            Paragraph(PLATFORM_LABELS.get(s.platform, s.platform.value), cell_style_bold),
            Paragraph(f"{s.followers:,}".replace(",", "."), cell_style_r),
            Paragraph(f"{s.avg_views:,}".replace(",", "."), cell_style_r),
            Paragraph(f"{s.engagement_rate * 100:.2f}%", cell_style_r),
            Paragraph(f"{s.avg_monthly_impressions:,}".replace(",", "."), cell_style_r),
        ])

    t = Table(rows, colWidths=[4 * cm, 3.25 * cm, 3.25 * cm, 3 * cm, 4.5 * cm])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
        ("GRID", (0, 0), (-1, 0), 0, BRAND_DARK),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]
    t.setStyle(TableStyle(style_cmds))
    elements.append(t)
    elements.append(Spacer(1, 8 * mm))
    return elements


# ── Package card ───────────────────────────────────────────

def _build_package_card(pkg: Package, brand_color, lang: str = "id") -> List:
    """Build a single package card with tier header, items, and price."""
    elements = []
    tier_color = TIER_COLORS.get(pkg.tier, brand_color)
    tier_bg = TIER_BG_COLORS.get(pkg.tier, GRAY_50)
    tier_label = TIER_EMOJI.get(pkg.tier, pkg.tier.value.upper())

    # ── Tier header ──
    header_left = Paragraph(
        f"{pkg.name}",
        ParagraphStyle("pkgn", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white),
    )
    header_right = Paragraph(
        tier_label,
        ParagraphStyle("pkgt", fontName="Helvetica-Bold", fontSize=9, textColor=colors.Color(1, 1, 1, 0.6), alignment=TA_RIGHT),
    )
    header_row = Table([[header_left, header_right]], colWidths=[14 * cm, 4 * cm])
    header_row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), tier_color),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [5, 5, 0, 0]),
    ]))
    elements.append(header_row)

    # ── Items table ──
    col_hdr = ParagraphStyle("ch", fontName="Helvetica-Bold", fontSize=8, textColor=GRAY_500)
    col_hdr_c = ParagraphStyle("chc", fontName="Helvetica-Bold", fontSize=8, textColor=GRAY_500, alignment=TA_CENTER)
    col_hdr_r = ParagraphStyle("chr", fontName="Helvetica-Bold", fontSize=8, textColor=GRAY_500, alignment=TA_RIGHT)

    rows = [[
        Paragraph(_t("content", lang), col_hdr),
        Paragraph(_t("qty", lang), col_hdr_c),
        Paragraph(_t("unit_price", lang), col_hdr_r),
        Paragraph(_t("subtotal", lang), col_hdr_r),
    ]]

    item_style = ParagraphStyle("is", fontName="Helvetica", fontSize=9, textColor=GRAY_700)
    item_style_c = ParagraphStyle("isc", fontName="Helvetica", fontSize=9, textColor=GRAY_700, alignment=TA_CENTER)
    item_style_r = ParagraphStyle("isr", fontName="Helvetica", fontSize=9, textColor=GRAY_700, alignment=TA_RIGHT)

    for item in pkg.items:
        label = CONTENT_TYPE_LABELS.get(item.content_type, item.content_type.value)
        addons = []
        if item.usage_rights_days:
            addons.append(_t("usage_d", lang, d=item.usage_rights_days))
        if item.exclusivity_days:
            addons.append(_t("excl_d", lang, d=item.exclusivity_days))
        addon_str = f"<br/><font size='7' color='#9CA3AF'>{', '.join(addons)}</font>" if addons else ""

        rows.append([
            Paragraph(f"{label}{addon_str}", item_style),
            Paragraph(str(item.quantity), item_style_c),
            Paragraph(format_price(item.unit_price, lang), item_style_r),
            Paragraph(format_price(item.unit_price * item.quantity, lang), item_style_r),
        ])

    # Subtotal
    rows.append([
        Paragraph(_t("subtotal_content", lang), ParagraphStyle("st", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_600)),
        "", "",
        Paragraph(format_price(pkg.base_price, lang), ParagraphStyle("stv", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_600, alignment=TA_RIGHT)),
    ])

    # Bundle discount
    if pkg.bundle_discount_pct > 0:
        rows.append([
            Paragraph(f"{_t('bundle_discount', lang)} ({pkg.bundle_discount_pct * 100:.0f}%)", ParagraphStyle("bd", fontName="Helvetica", fontSize=9, textColor=GREEN_600)),
            "", "",
            Paragraph(f"- {format_price(pkg.base_price * pkg.bundle_discount_pct, lang)}", ParagraphStyle("bdv", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT, textColor=GREEN_600)),
        ])

    # Add-ons
    for addon in pkg.addons:
        labels = ADDON_LABELS_EN if lang == "en" else ADDON_LABELS
        addon_label = labels.get(addon.addon_type, addon.addon_type.value)
        qty_str = f" x{addon.quantity}" if addon.quantity > 1 else ""
        if addon.included_in_tier:
            rows.append([
                Paragraph(f"{addon_label}{qty_str} <font color='#16A34A'>(INCLUDED)</font>", ParagraphStyle("ai", fontName="Helvetica", fontSize=8, textColor=GRAY_400)),
                "", "",
                Paragraph(f"<strike>{format_price(addon.price, lang)}</strike>", ParagraphStyle("aiv", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT, textColor=GRAY_300)),
            ])
        else:
            rows.append([
                Paragraph(f"{addon_label}{qty_str}", ParagraphStyle("ao", fontName="Helvetica", fontSize=9, textColor=GRAY_700)),
                "", "",
                Paragraph(f"+ {format_price(addon.price * addon.quantity, lang)}", ParagraphStyle("aov", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT, textColor=GRAY_700)),
            ])

    # Client discount
    if pkg.client_discount_pct > 0:
        price_after_bundle = pkg.base_price * (1 - pkg.bundle_discount_pct)
        rows.append([
            Paragraph(f"{_t('client_discount', lang)} ({pkg.client_discount_pct * 100:.0f}%)", ParagraphStyle("cd", fontName="Helvetica", fontSize=9, textColor=GREEN_600)),
            "", "",
            Paragraph(f"- {format_price((price_after_bundle + pkg.addon_total) * pkg.client_discount_pct, lang)}", ParagraphStyle("cdv", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT, textColor=GREEN_600)),
        ])

    # Final total row
    rows.append([
        Paragraph(_t("total", lang), ParagraphStyle("tot", fontName="Helvetica-Bold", fontSize=12, textColor=brand_color)),
        "", "",
        Paragraph(format_price(pkg.final_price, lang), ParagraphStyle("totv", fontName="Helvetica-Bold", fontSize=12, alignment=TA_RIGHT, textColor=brand_color)),
    ])

    n = len(rows)
    t = Table(rows, colWidths=[8 * cm, 1.5 * cm, 4 * cm, 4.5 * cm])
    style_cmds = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_50),
        ("LINEBELOW", (0, 0), (-1, 0), 1, GRAY_200),
        # Body rows
        ("ROWBACKGROUNDS", (0, 1), (-1, n - 2), [colors.white, colors.white]),
        ("LINEBELOW", (0, 1), (-1, n - 2), 0.3, GRAY_100),
        # Total row
        ("BACKGROUND", (0, n - 1), (-1, n - 1), BRAND_LIGHT_BG),
        ("LINEABOVE", (0, n - 1), (-1, n - 1), 1.5, brand_color),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        # Border
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("ROUNDEDCORNERS", [0, 0, 5, 5]),
    ]
    t.setStyle(TableStyle(style_cmds))
    elements.append(t)

    # Tier perks
    if lang == "en":
        tier_bonus = TIER_BONUSES_EN.get(pkg.tier, {})
    else:
        tier_bonus = TIER_BONUSES.get(pkg.tier, {})
    perks = tier_bonus.get("perks", [])
    if perks:
        perks_str = "  ·  ".join(perks)
        perk_para = Paragraph(
            f"{_t('includes', lang)}: {perks_str}",
            ParagraphStyle("perks", fontName="Helvetica", fontSize=7, textColor=GREEN_600),
        )
        perk_bar = Table([[perk_para]], colWidths=[18 * cm])
        perk_bar.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GREEN_50),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("ROUNDEDCORNERS", [0, 0, 4, 4]),
        ]))
        elements.append(perk_bar)

    # Validity
    elements.append(Paragraph(
        _t("quote_valid", lang, days=pkg.valid_days),
        ParagraphStyle("val", fontName="Helvetica-Oblique", fontSize=7, textColor=GRAY_400, spaceBefore=3),
    ))
    elements.append(Spacer(1, 8 * mm))
    return elements


# ── Affiliate block ────────────────────────────────────────

def _build_affiliate_block(profile: CreatorProfile, brand_color, style: dict, lang: str = "id") -> List:
    """Affiliate commission rate & projected earning for rate card PDF."""
    elements = []
    if not profile.has_affiliate:
        return elements

    active = [a for a in profile.affiliate_stats if a.enabled and a.avg_monthly_gmv > 0]
    if not active:
        return elements

    elements.extend(_section_header(_t("commission_rates", lang), brand_color))

    for aff in active:
        sug = calculate_affiliate_rate(
            aff.platform.value,
            aff.avg_monthly_gmv,
            aff.avg_conversion_rate,
            aff.avg_commission_pct,
        )

        platform_name = AFFILIATE_PLATFORM_LABELS.get(aff.platform, aff.platform.value)

        # Platform name badge
        plat_para = Paragraph(
            platform_name,
            ParagraphStyle("pn", fontName="Helvetica-Bold", fontSize=11, textColor=brand_color),
        )
        gmv_para = Paragraph(
            f"{_t('avg_gmv_month', lang)}: {format_price(aff.avg_monthly_gmv, lang)}",
            ParagraphStyle("gp", fontName="Helvetica", fontSize=8, textColor=GRAY_500, alignment=TA_RIGHT),
        )
        plat_row = Table([[plat_para, gmv_para]], colWidths=[9 * cm, 9 * cm])
        plat_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(plat_row)

        # Commission cards: Min / Target / Max
        card_hdr = ParagraphStyle("cdh", fontName="Helvetica-Bold", fontSize=7, textColor=GRAY_500, alignment=TA_CENTER)
        card_val = ParagraphStyle("cdv", fontName="Helvetica-Bold", fontSize=16, alignment=TA_CENTER)
        card_label = ParagraphStyle("cdl", fontName="Helvetica", fontSize=7, textColor=GRAY_400, alignment=TA_CENTER)

        min_block = [
            Paragraph(_t("minimum", lang), card_hdr),
            Paragraph(f"{sug['commission_min_pct'] * 100:.1f}%", ParagraphStyle("mv", parent=card_val, textColor=GRAY_600)),
        ]
        target_block = [
            Paragraph(_t("target", lang), card_hdr),
            Paragraph(f"{sug['commission_target_pct'] * 100:.1f}%", ParagraphStyle("tv", parent=card_val, textColor=brand_color)),
        ]
        max_block = [
            Paragraph(_t("maximum", lang), card_hdr),
            Paragraph(f"{sug['commission_max_pct'] * 100:.1f}%", ParagraphStyle("xv", parent=card_val, textColor=GRAY_600)),
        ]
        earning_block = [
            Paragraph(_t("projected_earning", lang), card_hdr),
            Paragraph(format_price(sug["projected_monthly_earning_target"], lang), ParagraphStyle("ev", parent=card_val, fontSize=13, textColor=brand_color)),
            Paragraph(_t("per_month_target", lang), card_label),
        ]
        fee_block = [
            Paragraph(_t("base_fee", lang), card_hdr),
            Paragraph(format_price(sug["base_fee_suggested"], lang), ParagraphStyle("fv", parent=card_val, fontSize=13, textColor=GRAY_700)),
            Paragraph(_t("suggested_upfront", lang), card_label),
        ]

        # Row 1: Commission percentages
        comm_data = [[min_block[0], target_block[0], max_block[0]],
                     [min_block[1], target_block[1], max_block[1]]]
        comm_t = Table(comm_data, colWidths=[6 * cm, 6 * cm, 6 * cm])
        comm_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BACKGROUND", (1, 0), (1, -1), BRAND_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
            ("LINEBEFORE", (1, 0), (1, -1), 0.5, GRAY_200),
            ("LINEBEFORE", (2, 0), (2, -1), 0.5, GRAY_200),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        elements.append(comm_t)
        elements.append(Spacer(1, 2 * mm))

        # Row 2: Earning + Fee
        earn_data = [
            [earning_block[0], fee_block[0]],
            [earning_block[1], fee_block[1]],
            [earning_block[2], fee_block[2]],
        ]
        earn_t = Table(earn_data, colWidths=[10 * cm, 8 * cm])
        earn_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT_BG),
            ("BACKGROUND", (1, 0), (1, -1), GRAY_50),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
            ("LINEBEFORE", (1, 0), (1, -1), 0.5, GRAY_200),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        elements.append(earn_t)

        elements.append(Paragraph(
            f"{_t('min_campaign_gmv', lang)}: {format_price(sug['min_campaign_value'], lang)}",
            ParagraphStyle("mcg", fontName="Helvetica", fontSize=7, textColor=GRAY_400, spaceBefore=3),
        ))
        elements.append(Spacer(1, 6 * mm))

    if profile.affiliate_categories:
        cat_str = "  ·  ".join(profile.affiliate_categories)
        elements.append(Paragraph(
            f"<b>{_t('top_categories', lang)}:</b> {cat_str}",
            ParagraphStyle("cat", fontName="Helvetica", fontSize=9, textColor=GRAY_700),
        ))
        elements.append(Spacer(1, 2 * mm))

    # Deal schemes info box
    scheme_para = Paragraph(
        f"<b>{_t('deal_schemes', lang)}:</b>  "
        f"{_t('commission_only', lang)}  ·  "
        f"{_t('hybrid', lang)}  ·  "
        f"{_t('flat_fee', lang)}",
        ParagraphStyle("sch", fontName="Helvetica", fontSize=8, textColor=GRAY_600),
    )
    scheme_box = Table([[scheme_para]], colWidths=[18 * cm])
    scheme_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRAY_50),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(scheme_box)
    elements.append(Spacer(1, 8 * mm))
    return elements


# ── Add-ons table ──────────────────────────────────────────

def _build_addon_table(brand_color, style: dict, category: str = "influencer", lang: str = "id") -> List:
    """Build add-ons pricing table including custom add-ons from database."""
    from ratecard.core.database import list_custom_addons

    elements = []
    elements.extend(_section_header(_t("addons_title", lang), brand_color))

    hdr_style = ParagraphStyle("ah", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)
    hdr_style_c = ParagraphStyle("ahc", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_CENTER)
    hdr_style_r = ParagraphStyle("ahr", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_RIGHT)

    cell = ParagraphStyle("ac", fontName="Helvetica", fontSize=9, textColor=GRAY_700)
    cell_desc = ParagraphStyle("acd", fontName="Helvetica", fontSize=7, textColor=GRAY_400)
    cell_c = ParagraphStyle("acc", fontName="Helvetica", fontSize=9, textColor=GRAY_700, alignment=TA_CENTER)
    cell_r = ParagraphStyle("acr", fontName="Helvetica-Bold", fontSize=9, textColor=brand_color, alignment=TA_RIGHT)

    d = _t("days", lang)
    addon_data = [
        [Paragraph(_t("addon", lang), hdr_style), Paragraph(_t("detail", lang), hdr_style_c), Paragraph(_t("extra_cost", lang), hdr_style_r)],
        [Paragraph(_t("exclusivity", lang), cell), Paragraph(f"30 {d}", cell_c), Paragraph("+25%", cell_r)],
        [Paragraph(_t("exclusivity", lang), cell), Paragraph(f"60 {d}", cell_c), Paragraph("+40%", cell_r)],
        [Paragraph(_t("exclusivity", lang), cell), Paragraph(f"90 {d}", cell_c), Paragraph("+60%", cell_r)],
        [Paragraph(_t("usage_rights", lang), cell), Paragraph(f"30 {d}", cell_c), Paragraph("+15%", cell_r)],
        [Paragraph(_t("usage_rights", lang), cell), Paragraph(f"60 {d}", cell_c), Paragraph("+25%", cell_r)],
        [Paragraph(_t("usage_rights", lang), cell), Paragraph(f"90 {d}", cell_c), Paragraph("+35%", cell_r)],
    ]

    # Append custom add-ons from database
    custom_addons = list_custom_addons(category=category, enabled_only=True)
    for ca in custom_addons:
        name_text = ca.name
        if ca.description:
            name_text += f"<br/><font size='7' color='#9CA3AF'>{ca.description}</font>"
        if ca.price_type == "percentage":
            price_text = f"+{ca.price_value:.0f}%"
        else:
            price_text = format_price(ca.price_value, lang)
        addon_data.append([
            Paragraph(name_text, cell),
            Paragraph(_t("custom", lang), cell_c),
            Paragraph(price_text, cell_r),
        ])

    at = Table(addon_data, colWidths=[10 * cm, 4 * cm, 4 * cm])
    at.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, GRAY_200),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(at)
    elements.append(Spacer(1, 8 * mm))
    return elements


# ── Terms ──────────────────────────────────────────────────

def _build_terms(tmpl: dict, style: dict, brand_color, lang: str = "id") -> List:
    """Build terms & conditions section."""
    elements = []
    elements.extend(_section_header(_t("terms_title", lang), brand_color))

    if lang == "en":
        payment_val = _t("payment_terms_default", lang)
        revision_val = _t("revision_policy_default", lang)
        notes_val = _t("additional_notes_default", lang)
    else:
        payment_val = tmpl["payment_terms"]
        revision_val = tmpl["revision_policy"]
        notes_val = tmpl["additional_notes"]

    terms_items = [
        (_t("payment", lang), payment_val),
        (_t("revision", lang), revision_val),
        (_t("notes", lang), notes_val),
    ]

    term_rows = []
    for label, value in terms_items:
        term_rows.append([
            Paragraph(f"<b>{label}</b>", ParagraphStyle("tl", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_700)),
            Paragraph(value, ParagraphStyle("tv", fontName="Helvetica", fontSize=9, textColor=GRAY_600)),
        ])

    tt = Table(term_rows, colWidths=[4 * cm, 14 * cm])
    tt.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRAY_50, colors.white]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_200),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(tt)
    elements.append(Spacer(1, 10 * mm))
    return elements


# ── Footer ─────────────────────────────────────────────────

def _build_footer(profile: CreatorProfile, style: dict, brand_color, lang: str = "id") -> List:
    """Build PDF footer."""
    elements = []
    doc_date = datetime.now().strftime("%d %B %Y")
    valid_date = (datetime.now() + timedelta(days=30)).strftime("%d %B %Y")

    footer_text = Paragraph(
        _t("footer", lang, name=profile.name, date=doc_date, valid=valid_date),
        style["footer"],
    )
    footer_bar = Table([[footer_text]], colWidths=[18 * cm])
    footer_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRAY_50),
        ("LINEABOVE", (0, 0), (-1, 0), 1, GRAY_200),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(footer_bar)
    return elements


# ══════════════════════════════════════════════════════════
# MAIN: generate_rate_card
# ══════════════════════════════════════════════════════════

def generate_rate_card(
    profile: CreatorProfile,
    packages: List[Package],
    output_path: Path,
    template_path: Optional[Path] = None,
    mode: str = "all",
    lang: str = "id",
) -> Path:
    """
    Generate a professional rate card PDF.

    mode: "influencer" (stats + packages + addons only),
          "affiliate" (affiliate commission rates only),
          "all" (everything combined).
    """
    tmpl = _load_template(template_path)
    brand_color = _hex_to_color(tmpl["brand_color_hex"])
    font = tmpl.get("font_name", "Helvetica")
    style = _styles(brand_color, font)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    elements = []

    # ── Header banner ──────────────────────────────────────
    elements.extend(_build_header_banner(profile, style, brand_color, mode, lang))

    # ── Influencer sections ────────────────────────────────
    if mode in ("influencer", "all"):
        active_stats = [s for s in profile.platform_stats if s.followers > 0]
        if active_stats:
            elements.extend(_build_stats_table(profile, style, brand_color, lang))

        if packages:
            elements.extend(_section_header(_t("packages", lang), brand_color))
            elements.append(Spacer(1, 2 * mm))
            for pkg in packages:
                elements.extend(_build_package_card(pkg, brand_color, lang))

        elements.extend(_build_addon_table(brand_color, style, category="influencer", lang=lang))

    # ── Affiliate sections ─────────────────────────────────
    if mode in ("affiliate", "all"):
        elements.extend(_build_affiliate_block(profile, brand_color, style, lang))
        elements.extend(_build_addon_table(brand_color, style, category="affiliate", lang=lang))

    # ── Terms + Footer ─────────────────────────────────────
    elements.extend(_build_terms(tmpl, style, brand_color, lang))
    elements.extend(_build_footer(profile, style, brand_color, lang))

    doc.build(elements)
    return output_path


# ══════════════════════════════════════════════════════════
# PROPOSAL PDF
# ══════════════════════════════════════════════════════════

def _build_affiliate_terms_block(proposal: Proposal, brand_color, style: dict) -> List:
    """Negotiated affiliate terms block for proposal PDF."""
    elements = []
    aff = proposal.affiliate_terms
    if aff is None:
        return elements

    elements.extend(_section_header("Affiliate Deal Terms", brand_color))

    rows = [
        ["Komisi", f"{aff.commission_pct * 100:.1f}% dari GMV"],
        ["Durasi Deal", f"{aff.duration_days} hari"],
    ]
    if aff.base_fee > 0:
        rows.append(["Base Fee (Flat)", format_idr(aff.base_fee)])
    if aff.min_campaign_value > 0:
        rows.append(["Min. Campaign GMV", format_idr(aff.min_campaign_value)])
    if aff.projected_gmv > 0:
        rows.append(["Projected GMV", format_idr(aff.projected_gmv)])
    if aff.projected_earning > 0:
        rows.append(["Projected Earning", format_idr(aff.projected_earning)])
    if aff.exclusivity_days > 0:
        rows.append(["Exclusivity", f"{aff.exclusivity_days} hari"])
    if aff.categories:
        rows.append(["Kategori", " · ".join(aff.categories)])

    data = [[
        Paragraph(f"<b>{r[0]}</b>", style["body"]),
        Paragraph(str(r[1]), ParagraphStyle("rv", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT, textColor=GRAY_700)),
    ] for r in rows]

    t = Table(data, colWidths=[6 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BRAND_LIGHT_BG, colors.white]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_200),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 4 * mm))

    if proposal.pricing_model == PricingModel.COMMISSION:
        elements.append(Paragraph(
            "Skema: Commission Only — fee berdasarkan performa penjualan.",
            style["small"],
        ))
    elif proposal.pricing_model == PricingModel.HYBRID:
        elements.append(Paragraph(
            "Skema: Hybrid — base fee dibayar upfront + komisi berjalan selama durasi deal.",
            style["small"],
        ))
    elements.append(Spacer(1, 6 * mm))
    return elements


def generate_proposal(
    proposal: Proposal,
    profile: CreatorProfile,
    output_path: Path,
    template_path: Optional[Path] = None,
) -> Path:
    """Generate a client-specific proposal PDF."""
    tmpl = _load_template(template_path)
    brand_color = _hex_to_color(tmpl["brand_color_hex"])
    font = tmpl.get("font_name", "Helvetica")
    style = _styles(brand_color, font)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    elements = []
    doc_date = datetime.now().strftime("%d %B %Y")

    # ── Header banner ────────────────────────────────────────
    pm_label = PRICING_MODEL_LABELS.get(proposal.pricing_model, proposal.pricing_model.value.title())

    title_para = Paragraph(
        "PROPOSAL KERJASAMA",
        ParagraphStyle("pt", fontName="Helvetica-Bold", fontSize=22, textColor=colors.white, leading=26),
    )
    name_para = Paragraph(
        profile.name or "Creator Name",
        ParagraphStyle("pn", fontName="Helvetica", fontSize=11, textColor=colors.Color(1, 1, 1, 0.8)),
    )
    scheme_para = Paragraph(
        f"Skema: {pm_label}",
        ParagraphStyle("ps", fontName="Helvetica-Bold", fontSize=9, textColor=colors.Color(1, 1, 1, 0.6)),
    )
    date_para = Paragraph(
        doc_date,
        ParagraphStyle("pd", fontName="Helvetica", fontSize=9, textColor=colors.Color(1, 1, 1, 0.6), alignment=TA_RIGHT),
    )

    inner = Table(
        [[scheme_para, ""],
         [title_para, date_para],
         [name_para, ""]],
        colWidths=[12.5 * cm, 4.5 * cm],
    )
    inner.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (1, 1), (1, 1), "BOTTOM"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    banner = Table([[inner]], colWidths=[18 * cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), brand_color),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    elements.append(banner)
    elements.append(Spacer(1, 8 * mm))

    # Client info card
    info_data = [
        ["Kepada", proposal.client_name],
        ["Perusahaan", proposal.client_company or "-"],
        ["Campaign", proposal.campaign_name],
        ["Tanggal", doc_date],
        ["Valid hingga", (datetime.now() + timedelta(days=14)).strftime("%d %B %Y")],
    ]
    info_rows = []
    for label, value in info_data:
        info_rows.append([
            Paragraph(f"<b>{label}</b>", ParagraphStyle("il", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_500)),
            Paragraph(value, ParagraphStyle("iv", fontName="Helvetica", fontSize=9, textColor=GRAY_800)),
        ])
    info_t = Table(info_rows, colWidths=[4 * cm, 14 * cm])
    info_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRAY_50, colors.white]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_200),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(info_t)
    elements.append(Spacer(1, 6 * mm))

    # ── Packages ─────────────────────────────────────────────
    if proposal.packages:
        elements.extend(_section_header("Rincian Penawaran", brand_color))
        elements.append(Spacer(1, 2 * mm))
        for pkg in proposal.packages:
            elements.extend(_build_package_card(pkg, brand_color))

    # ── Affiliate Terms ──────────────────────────────────────
    elements.extend(_build_affiliate_terms_block(proposal, brand_color, style))

    # ── Grand Total ──────────────────────────────────────────
    if proposal.pricing_model == PricingModel.COMMISSION:
        total_label = "EST. EARNING (COMMISSION)"
    elif proposal.pricing_model == PricingModel.HYBRID:
        total_label = "TOTAL (BASE + EST. KOMISI)"
    else:
        total_label = "TOTAL INVESTASI"

    gt_rows = []
    has_fee = proposal.payment_fee_pct > 0

    if has_fee:
        gt_rows.append([
            Paragraph("Harga Dasar", ParagraphStyle("bl", fontName="Helvetica", fontSize=10, textColor=GRAY_600)),
            Paragraph(format_idr(proposal.total_price), ParagraphStyle("br", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT, textColor=GRAY_600)),
        ])
        gt_rows.append([
            Paragraph(f"Fee Pembayaran (+{proposal.payment_fee_pct * 100:.0f}%)", ParagraphStyle("fl", fontName="Helvetica", fontSize=10, textColor=AMBER_600)),
            Paragraph(f"+ {format_idr(proposal.payment_fee_amount)}", ParagraphStyle("fr", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT, textColor=AMBER_600)),
        ])

    gt_rows.append([
        Paragraph(total_label, ParagraphStyle("gt", fontName="Helvetica-Bold", fontSize=14, textColor=brand_color)),
        Paragraph(format_idr(proposal.grand_total), ParagraphStyle("gtr", fontName="Helvetica-Bold", fontSize=14, textColor=brand_color, alignment=TA_RIGHT)),
    ])

    gt = Table(gt_rows, colWidths=[9 * cm, 9 * cm])
    gt_style_cmds = [
        ("BACKGROUND", (0, len(gt_rows) - 1), (-1, len(gt_rows) - 1), BRAND_LIGHT_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]
    if has_fee:
        gt_style_cmds.append(("LINEABOVE", (0, len(gt_rows) - 1), (-1, len(gt_rows) - 1), 1, brand_color))
    gt.setStyle(TableStyle(gt_style_cmds))
    elements.append(gt)
    elements.append(Spacer(1, 6 * mm))

    # Payment schedule
    ps_label = PAYMENT_SCHEME_LABELS.get(proposal.payment_scheme, "DP 50%")
    if proposal.payment_scheme != PaymentScheme.FULL_UPFRONT:
        elements.extend(_section_header("Jadwal Pembayaran", brand_color))

        pay_hdr = ParagraphStyle("ph", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)
        pay_hdr_r = ParagraphStyle("phr", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_RIGHT)

        pay_data = [[
            Paragraph("Tahap", pay_hdr),
            Paragraph("Keterangan", pay_hdr),
            Paragraph("Jumlah", pay_hdr_r),
        ]]

        if proposal.dp_amount > 0:
            pay_data.append([
                Paragraph("1. DP / Bayar Awal", style["body"]),
                Paragraph("Sebelum produksi dimulai", style["small"]),
                Paragraph(format_idr(proposal.dp_amount), ParagraphStyle("dpv", fontName="Helvetica-Bold", fontSize=10, alignment=TA_RIGHT, textColor=brand_color)),
            ])
            pay_data.append([
                Paragraph("2. Pelunasan", style["body"]),
                Paragraph("Setelah konten tayang", style["small"]),
                Paragraph(format_idr(proposal.remaining_amount), ParagraphStyle("rmv", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT, textColor=GRAY_700)),
            ])
        else:
            pay_data.append([
                Paragraph("1. Pembayaran Penuh", style["body"]),
                Paragraph("Setelah konten tayang", style["small"]),
                Paragraph(format_idr(proposal.grand_total), ParagraphStyle("fpv", fontName="Helvetica-Bold", fontSize=10, alignment=TA_RIGHT, textColor=brand_color)),
            ])

        pt = Table(pay_data, colWidths=[5 * cm, 8 * cm, 5 * cm])
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_50]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, GRAY_200),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY_200),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        elements.append(pt)
        elements.append(Paragraph(
            f"Skema: {ps_label}",
            ParagraphStyle("psl", fontName="Helvetica-Oblique", fontSize=7, textColor=GRAY_400, spaceBefore=3),
        ))
        elements.append(Spacer(1, 4 * mm))

    if proposal.notes:
        elements.append(Paragraph(f"Catatan: {proposal.notes}", style["small"]))

    # ── Terms ────────────────────────────────────────────────
    elements.extend(_build_terms(tmpl, style, brand_color))

    # ── Signature ────────────────────────────────────────────
    sig_data = [[
        Paragraph(
            f"Menyetujui,<br/><br/><br/>________________<br/><b>{proposal.client_company or proposal.client_name}</b>",
            ParagraphStyle("s1", fontName="Helvetica", fontSize=9, textColor=GRAY_700),
        ),
        Paragraph(
            f"Hormat saya,<br/><br/><br/>________________<br/><b>{profile.name}</b>",
            ParagraphStyle("s2", fontName="Helvetica", fontSize=9, textColor=GRAY_700),
        ),
    ]]
    sig = Table(sig_data, colWidths=[9 * cm, 9 * cm])
    sig.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(sig)

    # ── Footer ───────────────────────────────────────────────
    elements.append(Spacer(1, 10 * mm))
    footer_text = Paragraph(
        f"Proposal — {proposal.campaign_name}  |  {profile.name}  |  {doc_date}",
        style["footer"],
    )
    footer_bar = Table([[footer_text]], colWidths=[18 * cm])
    footer_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRAY_50),
        ("LINEABOVE", (0, 0), (-1, 0), 1, GRAY_200),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(footer_bar)

    doc.build(elements)
    return output_path
