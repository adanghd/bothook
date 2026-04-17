"""Reusable InlineKeyboard builders for rate card bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ratecard.core.models import (
    AFFILIATE_PLATFORM_LABELS,
    PLATFORM_LABELS,
    AffiliatePlatform,
    Platform,
    TierName,
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Rate Card", callback_data="rc_cat_menu"),
         InlineKeyboardButton("📝 Buat Proposal", callback_data="prop_start")],
        [InlineKeyboardButton("📈 Update Stats", callback_data="stats_menu"),
         InlineKeyboardButton("📋 History", callback_data="history")],
        [InlineKeyboardButton("🧩 Add-ons", callback_data="addon_menu"),
         InlineKeyboardButton("📥 Export Excel", callback_data="export_xlsx")],
    ])


def ratecard_category_keyboard() -> InlineKeyboardMarkup:
    """First step: pick Influencer or Affiliate."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Influencer (Endorsement)", callback_data="rc_cat_influencer")],
        [InlineKeyboardButton("🛍 Affiliate (TikTok Shop / Shopee)", callback_data="rc_cat_affiliate")],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
    ])


def ratecard_tier_keyboard() -> InlineKeyboardMarkup:
    """Tier selection for influencer rate card."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥉 Bronze — Lite", callback_data="rc_tier_Bronze"),
         InlineKeyboardButton("🥈 Silver — Standard", callback_data="rc_tier_Silver")],
        [InlineKeyboardButton("🥇 Gold — Premium", callback_data="rc_tier_Gold"),
         InlineKeyboardButton("📊 Semua Tier", callback_data="rc_tier_all")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="rc_cat_menu")],
    ])


def ratecard_lang_keyboard(tier_value: str) -> InlineKeyboardMarkup:
    """Language picker after tier is selected."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇩 Bahasa Indonesia", callback_data=f"rc_lang_{tier_value}_id"),
         InlineKeyboardButton("🇬🇧 English", callback_data=f"rc_lang_{tier_value}_en")],
        [InlineKeyboardButton("🔙 Pilih Tier", callback_data="rc_tier_menu")],
    ])


def ratecard_format_keyboard(tier_value: str, lang: str) -> InlineKeyboardMarkup:
    """Output format picker after language is selected."""
    base = f"rc_fmt_{tier_value}_{lang}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Text Message", callback_data=f"{base}_text"),
         InlineKeyboardButton("📄 PDF File", callback_data=f"{base}_pdf")],
        [InlineKeyboardButton("📱+📄 Keduanya", callback_data=f"{base}_both")],
        [InlineKeyboardButton("🔙 Pilih Bahasa", callback_data=f"rc_tier_{tier_value}")],
    ])


def ratecard_aff_lang_keyboard() -> InlineKeyboardMarkup:
    """Language picker for affiliate rate card."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇩 Bahasa Indonesia", callback_data="rc_aff_lang_id"),
         InlineKeyboardButton("🇬🇧 English", callback_data="rc_aff_lang_en")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="rc_cat_menu")],
    ])


def ratecard_aff_format_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Format picker for affiliate rate card."""
    base = f"rc_aff_fmt_{lang}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Text Message", callback_data=f"{base}_text"),
         InlineKeyboardButton("📄 PDF File", callback_data=f"{base}_pdf")],
        [InlineKeyboardButton("📱+📄 Keduanya", callback_data=f"{base}_both")],
        [InlineKeyboardButton("🔙 Pilih Bahasa", callback_data="rc_cat_affiliate")],
    ])


def rate_card_after_keyboard(category: str = "influencer") -> InlineKeyboardMarkup:
    """Keyboard shown after viewing a rate card."""
    if category == "affiliate":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Download PDF", callback_data="rc_aff_pdf"),
             InlineKeyboardButton("🔄 Pilih Lain", callback_data="rc_cat_menu")],
            [InlineKeyboardButton("🔙 Menu Utama", callback_data="menu")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Download PDF", callback_data="rc_pdf"),
         InlineKeyboardButton("🔄 Pilih Tier Lain", callback_data="rc_tier_menu")],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data="menu")],
    ])


def rate_card_menu_keyboard() -> InlineKeyboardMarkup:
    return rate_card_after_keyboard()


def platform_select_keyboard(selected: list = None, done_label: str = "✅ Lanjut") -> InlineKeyboardMarkup:
    selected = selected or []
    rows = []
    for platform in Platform:
        label = PLATFORM_LABELS.get(platform, platform.value)
        tick = "✓ " if platform.value in selected else ""
        rows.append([InlineKeyboardButton(
            f"{tick}{label}",
            callback_data=f"plat_{platform.value}",
        )])
    rows.append([
        InlineKeyboardButton(done_label, callback_data="plat_done"),
        InlineKeyboardButton("❌ Batal", callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def tier_select_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥉 Bronze — Lite", callback_data="tier_Bronze")],
        [InlineKeyboardButton("🥈 Silver — Standard", callback_data="tier_Silver")],
        [InlineKeyboardButton("🥇 Gold — Premium", callback_data="tier_Gold")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel")],
    ])


def proposal_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Konfirmasi & Simpan", callback_data="prop_confirm"),
         InlineKeyboardButton("❌ Batal", callback_data="cancel")],
    ])


def proposal_action_keyboard(proposal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Kirim PDF", callback_data=f"prop_pdf_{proposal_id}"),
         InlineKeyboardButton("✅ Mark Accepted", callback_data=f"prop_accept_{proposal_id}")],
        [InlineKeyboardButton("❌ Mark Rejected", callback_data=f"prop_reject_{proposal_id}"),
         InlineKeyboardButton("🔙 Menu", callback_data="menu")],
    ])


def stats_platform_keyboard() -> InlineKeyboardMarkup:
    rows = []
    # Social media platforms in pairs
    platforms = list(Platform)
    for i in range(0, len(platforms), 2):
        row = []
        for j in range(2):
            if i + j < len(platforms):
                p = platforms[i + j]
                label = PLATFORM_LABELS.get(p, p.value)
                row.append(InlineKeyboardButton(f"📱 {label}", callback_data=f"stats_{p.value}"))
        rows.append(row)
    # Affiliate platforms
    aff_row = []
    for aff_p in AffiliatePlatform:
        label = AFFILIATE_PLATFORM_LABELS.get(aff_p, aff_p.value)
        aff_row.append(InlineKeyboardButton(f"🛍 {label}", callback_data=f"stats_aff_{aff_p.value}"))
    rows.append(aff_row)
    rows.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def addon_list_keyboard(addons: list) -> InlineKeyboardMarkup:
    """All-in-one: list custom add-ons with toggle/delete + add button."""
    rows = []
    for addon in addons:
        status = "✅" if addon.enabled else "⬜"
        cat = "🎬" if addon.category == "influencer" else "🛍"
        price = f"+{addon.price_value:.0f}%" if addon.price_type == "percentage" else f"Rp {addon.price_value:,.0f}".replace(",", ".")
        rows.append([
            InlineKeyboardButton(
                f"{status} {cat} {addon.name} ({price})",
                callback_data=f"addon_toggle_{addon.id}",
            ),
            InlineKeyboardButton("🗑", callback_data=f"addon_del_{addon.id}"),
        ])
    rows.append([
        InlineKeyboardButton("➕ Tambah Add-on", callback_data="addon_add"),
    ])
    rows.append([
        InlineKeyboardButton("🔙 Menu Utama", callback_data="menu"),
    ])
    return InlineKeyboardMarkup(rows)


def addon_category_keyboard() -> InlineKeyboardMarkup:
    """Pick category for new add-on."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Influencer", callback_data="addon_cat_influencer"),
         InlineKeyboardButton("🛍 Affiliate", callback_data="addon_cat_affiliate")],
        [InlineKeyboardButton("❌ Batal", callback_data="addon_cancel")],
    ])


def addon_pricetype_keyboard() -> InlineKeyboardMarkup:
    """Pick price type for new add-on."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Persentase (%)", callback_data="addon_pt_percentage"),
         InlineKeyboardButton("💰 Harga Tetap (Rp)", callback_data="addon_pt_fixed")],
        [InlineKeyboardButton("❌ Batal", callback_data="addon_cancel")],
    ])


def addon_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Simpan", callback_data="addon_save"),
         InlineKeyboardButton("❌ Batal", callback_data="addon_cancel")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Menu Utama", callback_data="menu"),
    ]])
