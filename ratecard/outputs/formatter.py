"""
Telegram Markdown formatter for rate card data.
Produces MarkdownV2-safe messages within Telegram's 4096-char limit.
Supports Indonesian (default) and English output.
"""
from typing import List

from ratecard.core.models import (
    ADDON_LABELS,
    AFFILIATE_PLATFORM_LABELS,
    CONTENT_TYPE_LABELS,
    PLATFORM_LABELS,
    TIER_BONUSES,
    CreatorProfile,
    Package,
    Proposal,
    TierName,
    CONTENT_TYPE_PLATFORM,
)
from ratecard.core.pricing import calculate_affiliate_rate, format_idr


def format_usd(amount_idr: float, rate: float = 16_000) -> str:
    """Convert IDR to USD string (approximate)."""
    usd = amount_idr / rate
    if usd >= 1000:
        return f"${usd:,.0f}"
    elif usd >= 100:
        return f"${usd:.0f}"
    else:
        return f"${usd:.1f}"


# English content type labels
CONTENT_TYPE_LABELS_EN = {
    "ig_feed": "IG Feed Post", "ig_story": "IG Story", "ig_reel": "IG Reel",
    "ig_highlight": "IG Highlight Cover", "tt_video": "TikTok Video",
    "tt_duet": "TikTok Duet/Stitch", "tt_live": "TikTok Live Session",
    "yt_dedicated": "YouTube Dedicated Video", "yt_integration": "YouTube Brand Integration",
    "yt_short": "YouTube Short", "yt_community": "YouTube Community Post",
    "tw_tweet": "X/Twitter Post", "tw_thread": "X/Twitter Thread",
    "li_post": "LinkedIn Post", "li_article": "LinkedIn Article",
    "fb_post": "Facebook Post", "fb_story": "Facebook Story",
}

MAX_MSG_LEN = 4000  # leave buffer below 4096

_SPECIAL = r"\_*[]()~`>#+-=|{}.!"


def _esc(text: str) -> str:
    """Escape MarkdownV2 special characters."""
    for ch in _SPECIAL:
        text = text.replace(ch, f"\\{ch}")
    return text


def _tier_emoji(tier: TierName) -> str:
    return {
        TierName.BRONZE: "🥉",
        TierName.SILVER: "🥈",
        TierName.GOLD:   "🥇",
    }.get(tier, "📦")


def format_rate_card(profile: CreatorProfile, packages: List[Package]) -> List[str]:
    """
    Format rate card as list of Telegram MarkdownV2 messages.
    Splits automatically if content exceeds MAX_MSG_LEN.
    """
    lines = []
    lines.append(f"📊 *{_esc(profile.name or 'Rate Card')}*")
    if profile.niche:
        lines.append(f"_{_esc(profile.niche)}_")
    if profile.contact_email:
        lines.append(f"✉️ {_esc(profile.contact_email)}")
    lines.append("")

    # Platform stats
    active_stats = [s for s in profile.platform_stats if s.followers > 0]
    if active_stats:
        lines.append("*📈 Platform Stats*")
        for s in active_stats:
            platform_label = PLATFORM_LABELS.get(s.platform, s.platform.value)
            followers_fmt = f"{s.followers:,}".replace(",", "\\.")
            er_fmt = f"{s.engagement_rate*100:.2f}\\%"
            lines.append(f"  • *{_esc(platform_label)}* — {followers_fmt} followers \\| ER: {er_fmt}")
        lines.append("")

    # Packages
    lines.append("*💼 Paket Endorsement*")
    lines.append("")

    for pkg in packages:
        emoji = _tier_emoji(pkg.tier)
        lines.append(f"{emoji} *{_esc(pkg.name)}*")

        # Group items by platform
        platform_items: dict = {}
        for item in pkg.items:
            plat = CONTENT_TYPE_PLATFORM.get(item.content_type)
            platform_items.setdefault(plat, []).append(item)

        for plat, items in platform_items.items():
            plat_label = PLATFORM_LABELS.get(plat, plat.value if plat else "")
            lines.append(f"  _{_esc(plat_label)}_")
            for item in items:
                label = CONTENT_TYPE_LABELS.get(item.content_type, item.content_type.value)
                price_str = _esc(format_idr(item.unit_price))
                lines.append(f"  ├ {_esc(label)}: `{price_str}`")

        # Addons
        for addon in pkg.addons:
            label = ADDON_LABELS.get(addon.addon_type, addon.addon_type.value)
            qty = f" ×{addon.quantity}" if addon.quantity > 1 else ""
            if addon.included_in_tier:
                lines.append(f"  ├ ✅ {_esc(label)}{qty} \\(INCLUDED\\)")
            else:
                lines.append(f"  ├ ➕ {_esc(label)}{qty}: `{_esc(format_idr(addon.price * addon.quantity))}`")

        # Summary
        if pkg.bundle_discount_pct > 0:
            disc_pct = f"{pkg.bundle_discount_pct*100:.0f}\\%"
            lines.append(f"  Bundle disc: \\-{disc_pct}")
        lines.append(f"  *TOTAL: `{_esc(format_idr(pkg.final_price))}`*")

        # Tier perks
        tier_bonus = TIER_BONUSES.get(pkg.tier, {})
        perks = tier_bonus.get("perks", [])
        if perks:
            perks_str = " · ".join(perks)
            lines.append(f"  ✨ _{_esc(perks_str)}_")
        lines.append(f"  _Valid {pkg.valid_days} hari_")
        lines.append("")

    # Footer
    from datetime import datetime
    lines.append(f"_{_esc('Dibuat: ' + datetime.now().strftime('%d %b %Y'))}_")

    # Split into chunks
    return _split_messages(lines)


def format_proposal_summary(proposal: Proposal) -> List[str]:
    """Format a compact proposal summary for Telegram."""
    lines = []
    status_emoji = {"draft": "📝", "sent": "📤", "accepted": "✅", "rejected": "❌"}.get(
        proposal.status.value, "📋"
    )
    lines.append(f"{status_emoji} *Proposal \\#{proposal.id or '?'}*")
    lines.append(f"Client: *{_esc(proposal.client_name)}*")
    if proposal.client_company:
        lines.append(f"Perusahaan: {_esc(proposal.client_company)}")
    lines.append(f"Campaign: _{_esc(proposal.campaign_name)}_")
    lines.append("")

    for pkg in proposal.packages:
        emoji = _tier_emoji(pkg.tier)
        lines.append(f"{emoji} {_esc(pkg.name)}: `{_esc(format_idr(pkg.final_price))}`")

    lines.append("")
    lines.append(f"*💰 Total: `{_esc(format_idr(proposal.total_price))}`*")
    lines.append(f"Status: *{_esc(proposal.status.value.upper())}*")

    if proposal.created_at:
        lines.append(f"_Dibuat: {_esc(proposal.created_at.strftime('%d %b %Y'))}_")

    return _split_messages(lines)


def format_proposal_history(proposals) -> str:
    """Format list of proposals as a Telegram table."""
    if not proposals:
        return "_Belum ada proposal\\._"

    lines = ["*📋 History Proposal*", ""]
    status_emoji = {"draft": "📝", "sent": "📤", "accepted": "✅", "rejected": "❌"}

    for p in proposals:
        emoji = status_emoji.get(p.status.value, "📋")
        date_str = p.created_at.strftime("%d/%m/%y") if p.created_at else "?"
        lines.append(
            f"{emoji} *\\#{p.id}* {_esc(p.client_name)} — "
            f"`{_esc(format_idr(p.total_price))}` _{_esc(date_str)}_"
        )

    return "\n".join(lines)


def format_rate_card_en(profile: CreatorProfile, packages: List[Package]) -> List[str]:
    """
    Format rate card in English as Telegram MarkdownV2 messages.
    Prices shown in both IDR and approximate USD.
    """
    lines = []
    lines.append(f"📊 *{_esc(profile.name or 'Rate Card')}*")
    if profile.niche:
        lines.append(f"_{_esc(profile.niche)}_")
    if profile.location:
        lines.append(f"📍 {_esc(profile.location)}")
    if profile.contact_email:
        lines.append(f"✉️ {_esc(profile.contact_email)}")
    lines.append("")

    # Platform stats
    active_stats = [s for s in profile.platform_stats if s.followers > 0]
    if active_stats:
        lines.append("*📈 Platform Overview*")
        for s in active_stats:
            platform_label = PLATFORM_LABELS.get(s.platform, s.platform.value)
            followers_fmt = f"{s.followers:,}".replace(",", "\\,")
            er_fmt = f"{s.engagement_rate*100:.2f}\\%"
            lines.append(f"  • *{_esc(platform_label)}* — {followers_fmt} followers \\| ER: {er_fmt}")
        lines.append("")

    # Packages
    lines.append("*💼 Endorsement Packages*")
    lines.append("")

    for pkg in packages:
        emoji = _tier_emoji(pkg.tier)
        lines.append(f"{emoji} *{_esc(pkg.name)}*")

        platform_items: dict = {}
        for item in pkg.items:
            plat = CONTENT_TYPE_PLATFORM.get(item.content_type)
            platform_items.setdefault(plat, []).append(item)

        for plat, items in platform_items.items():
            plat_label = PLATFORM_LABELS.get(plat, plat.value if plat else "")
            lines.append(f"  _{_esc(plat_label)}_")
            for item in items:
                label_en = CONTENT_TYPE_LABELS_EN.get(item.content_type.value, item.content_type.value.replace("_", " ").title())
                price_idr = _esc(format_idr(item.unit_price))
                price_usd = _esc(format_usd(item.unit_price))
                lines.append(f"  ├ {_esc(label_en)}: `{price_idr}` \\(~{price_usd}\\)")

        # Addons
        for addon in pkg.addons:
            label = ADDON_LABELS.get(addon.addon_type, addon.addon_type.value)
            qty = f" ×{addon.quantity}" if addon.quantity > 1 else ""
            if addon.included_in_tier:
                lines.append(f"  ├ ✅ {_esc(label)}{qty} \\(INCLUDED\\)")
            else:
                price_idr = _esc(format_idr(addon.price * addon.quantity))
                price_usd = _esc(format_usd(addon.price * addon.quantity))
                lines.append(f"  ├ ➕ {_esc(label)}{qty}: `{price_idr}` \\(~{price_usd}\\)")

        if pkg.bundle_discount_pct > 0:
            disc_pct = f"{pkg.bundle_discount_pct*100:.0f}\\%"
            lines.append(f"  Bundle discount: \\-{disc_pct}")
        price_idr_total = _esc(format_idr(pkg.final_price))
        price_usd_total = _esc(format_usd(pkg.final_price))
        lines.append(f"  *TOTAL: `{price_idr_total}` \\(~{price_usd_total}\\)*")

        # Tier perks
        tier_bonus = TIER_BONUSES.get(pkg.tier, {})
        perks = tier_bonus.get("perks", [])
        if perks:
            perks_str = " · ".join(perks)
            lines.append(f"  ✨ _{_esc(perks_str)}_")
        lines.append(f"  _Valid {pkg.valid_days} days_")
        lines.append("")

    # Affiliate section
    active_aff = [a for a in profile.affiliate_stats if a.enabled and a.avg_monthly_gmv > 0]
    if active_aff:
        lines.append("*🛍 Affiliate Deal Rates*")
        for aff in active_aff:
            sug = calculate_affiliate_rate(
                aff.platform.value, aff.avg_monthly_gmv,
                aff.avg_conversion_rate, aff.avg_commission_pct,
            )
            plat_label = AFFILIATE_PLATFORM_LABELS.get(aff.platform, aff.platform.value)
            lines.append(f"  *{_esc(plat_label)}*")
            lines.append(f"  ├ Target commission: {sug['commission_target_pct']*100:.1f}\\%")
            lines.append(f"  ├ Est\\. monthly earning: `{_esc(format_idr(sug['projected_monthly_earning_target']))}`")
            lines.append(f"  └ Base fee: `{_esc(format_idr(sug['base_fee_suggested']))}`")
        lines.append("")
        lines.append(f"_3 deal models: Commission Only \\| Hybrid \\(base fee \\+ commission\\) \\| Flat Fee_")
        lines.append("")

    # Footer
    from datetime import datetime
    lines.append(f"_{_esc('Generated: ' + datetime.now().strftime('%d %b %Y'))}_")

    return _split_messages(lines)


def format_rate_card_affiliate(profile: CreatorProfile) -> List[str]:
    """Format affiliate-only rate summary for Telegram MarkdownV2."""
    active_aff = [a for a in profile.affiliate_stats if a.enabled and a.avg_monthly_gmv > 0]
    if not active_aff:
        return [_esc("Belum ada data affiliate. Setup dulu via web dashboard /profile.")]

    lines = ["*🛍 Affiliate Rate Card*", ""]
    for aff in active_aff:
        sug = calculate_affiliate_rate(
            aff.platform.value, aff.avg_monthly_gmv,
            aff.avg_conversion_rate, aff.avg_commission_pct,
        )
        plat_label = AFFILIATE_PLATFORM_LABELS.get(aff.platform, aff.platform.value)
        lines.append(f"*{_esc(plat_label)}*")
        lines.append(f"  GMV/bln: `{_esc(format_idr(aff.avg_monthly_gmv))}`")
        lines.append(f"  Conv rate: {aff.avg_conversion_rate*100:.2f}\\%")
        lines.append(f"  📊 Target komisi: *{sug['commission_target_pct']*100:.1f}\\%* \\(min {sug['commission_min_pct']*100:.1f}\\%\\)")
        lines.append(f"  💰 Est\\. earning: `{_esc(format_idr(sug['projected_monthly_earning_target']))}`/bln")
        lines.append(f"  📋 Base fee: `{_esc(format_idr(sug['base_fee_suggested']))}`")
        lines.append(f"  🎯 Min campaign: `{_esc(format_idr(sug['min_campaign_value']))}`")
        lines.append("")

    if profile.affiliate_categories:
        cats = " · ".join(profile.affiliate_categories)
        lines.append(f"🏷 Kategori: _{_esc(cats)}_")

    return _split_messages(lines)


def _split_messages(lines: List[str]) -> List[str]:
    """Split lines into messages that fit within MAX_MSG_LEN."""
    messages = []
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > MAX_MSG_LEN and current:
            messages.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        messages.append("\n".join(current))

    return messages
