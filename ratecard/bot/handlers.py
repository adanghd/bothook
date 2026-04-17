"""
Telegram bot handlers for the rate card system.
Registers all /ratecard, /proposal, /stats, /history, /exportxlsx commands.
"""
import logging
from pathlib import Path

from telegram import Update, ParseMode, InputFile
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Dispatcher,
    Filters,
    MessageHandler,
)

from config import PLATFORM_DEFAULTS_PATH, PROPOSALS_DIR, RATE_CARD_TEMPLATE_PATH
from ratecard.core import database as db
from ratecard.core.models import (
    AFFILIATE_PLATFORM_LABELS,
    PLATFORM_LABELS,
    TIER_BONUSES,
    AffiliatePlatform,
    AffiliateStats,
    CustomAddOn,
    Package,
    Platform,
    PlatformStats,
    Proposal,
    ProposalStatus,
    TierName,
)
from ratecard.core.packages import build_all_packages, build_package
from ratecard.core.pricing import format_idr, load_defaults
from ratecard.outputs.formatter import (
    format_proposal_history,
    format_proposal_summary,
    format_rate_card,
    format_rate_card_affiliate,
    format_rate_card_en,
)
from ratecard.outputs.pdf_generator import generate_proposal, generate_rate_card
from ratecard.bot.keyboards import (
    addon_category_keyboard,
    addon_confirm_keyboard,
    addon_list_keyboard,
    addon_pricetype_keyboard,
    back_to_menu_keyboard,
    main_menu_keyboard,
    platform_select_keyboard,
    proposal_action_keyboard,
    proposal_confirm_keyboard,
    rate_card_after_keyboard,
    rate_card_menu_keyboard,
    ratecard_aff_format_keyboard,
    ratecard_aff_lang_keyboard,
    ratecard_category_keyboard,
    ratecard_format_keyboard,
    ratecard_lang_keyboard,
    ratecard_tier_keyboard,
    stats_platform_keyboard,
    tier_select_keyboard,
)

log = logging.getLogger(__name__)

# ConversationHandler states
(
    PROP_CLIENT_NAME,
    PROP_CLIENT_COMPANY,
    PROP_CAMPAIGN,
    PROP_TIER,
    PROP_PLATFORMS,
    PROP_CONFIRM,
    STATS_VALUE,
    ADDON_NAME,
    ADDON_DESC,
    ADDON_PRICE_VALUE,
) = range(10)

# Temporary conversation data storage keyed by user_id
_conv_data: dict = {}


def _defaults():
    return load_defaults(PLATFORM_DEFAULTS_PATH)


# ──────────────────────────────────────────────────────────
# /start / /menu
# ──────────────────────────────────────────────────────────

def cmd_start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Halo! Ini Rate Card Manager kamu.\nPilih menu di bawah:",
        reply_markup=main_menu_keyboard(),
    )


def cmd_menu(update: Update, context: CallbackContext):
    update.message.reply_text("Menu Rate Card:", reply_markup=main_menu_keyboard())


# ──────────────────────────────────────────────────────────
# /ratecard — category → tier → language → format → output
# ──────────────────────────────────────────────────────────

def cmd_ratecard(update: Update, context: CallbackContext):
    """Show Influencer / Affiliate category picker."""
    update.message.reply_text(
        "📊 Mau lihat rate card apa?",
        reply_markup=ratecard_category_keyboard(),
    )


def cb_rc_cat_menu(update: Update, context: CallbackContext):
    """Show category picker from callback."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "📊 Mau lihat rate card apa?",
        reply_markup=ratecard_category_keyboard(),
    )


def cb_rc_cat_influencer(update: Update, context: CallbackContext):
    """Influencer selected → show tier picker."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "🎬 *Influencer Rate Card*\nPilih tier paket endorsement:",
        parse_mode=ParseMode.MARKDOWN_V2 if False else None,
        reply_markup=ratecard_tier_keyboard(),
    )


def cb_rc_cat_affiliate(update: Update, context: CallbackContext):
    """Affiliate selected → show language picker."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "🛍 Affiliate Rate Card\n(TikTok Shop / Shopee Affiliate)\n\nPilih bahasa:",
        reply_markup=ratecard_aff_lang_keyboard(),
    )


def cb_rc_tier_menu(update: Update, context: CallbackContext):
    """Show tier selection from callback."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "🎬 Influencer Rate Card\nPilih tier paket endorsement:",
        reply_markup=ratecard_tier_keyboard(),
    )


def cb_rc_tier(update: Update, context: CallbackContext):
    """Tier selected → show language picker."""
    query = update.callback_query
    tier_value = query.data.replace("rc_tier_", "")
    query.answer()

    tier_labels = {
        "Bronze": "🥉 Bronze — Lite",
        "Silver": "🥈 Silver — Standard",
        "Gold": "🥇 Gold — Premium",
        "all": "📊 Semua Tier",
    }
    tier_label = tier_labels.get(tier_value, tier_value)

    # Show tier perks if single tier
    perks_text = ""
    if tier_value != "all":
        try:
            bonus = TIER_BONUSES.get(TierName(tier_value), {})
            perks = bonus.get("perks", [])
            if perks:
                perks_text = "\n✨ " + " · ".join(perks)
        except ValueError:
            pass

    query.edit_message_text(
        f"Rate Card: {tier_label}{perks_text}\n\nPilih bahasa:",
        reply_markup=ratecard_lang_keyboard(tier_value),
    )


def cb_rc_lang(update: Update, context: CallbackContext):
    """Language selected → show output format picker."""
    query = update.callback_query
    # callback data: rc_lang_{tier}_{lang}
    payload = query.data.replace("rc_lang_", "")
    parts = payload.rsplit("_", 1)
    tier_value, lang = parts[0], parts[1]
    query.answer()

    lang_label = "🇮🇩 Bahasa Indonesia" if lang == "id" else "🇬🇧 English"
    query.edit_message_text(
        f"Bahasa: {lang_label}\n\nMau output format apa?",
        reply_markup=ratecard_format_keyboard(tier_value, lang),
    )


def _send_rate_card_text(query, profile, packages, lang, category="influencer"):
    """Send rate card as Telegram text message(s)."""
    after_kb = rate_card_after_keyboard(category)
    if category == "affiliate":
        msgs = format_rate_card_affiliate(profile)
    elif lang == "en":
        msgs = format_rate_card_en(profile, packages)
    else:
        msgs = format_rate_card(profile, packages)

    for i, msg in enumerate(msgs):
        if i == 0:
            query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN_V2,
                                     reply_markup=after_kb)
        else:
            query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


def _send_rate_card_pdf(query, profile, packages, category="influencer", lang="id"):
    """Send rate card as PDF file."""
    suffix = f"_{category}" if category != "all" else ""
    lang_suffix = f"_{lang}" if lang != "id" else ""
    filename = f"rate_card{suffix}{lang_suffix}.pdf"
    out_path = PROPOSALS_DIR / filename
    generate_rate_card(profile, packages, out_path, RATE_CARD_TEMPLATE_PATH, mode=category, lang=lang)
    after_kb = rate_card_after_keyboard(category)
    with open(out_path, "rb") as f:
        query.message.reply_document(
            document=InputFile(f, filename=filename),
            caption=f"Rate Card ({category.title()}) — {profile.name}",
            reply_markup=after_kb,
        )


def cb_rc_format(update: Update, context: CallbackContext):
    """Output format selected → send rate card in chosen format."""
    query = update.callback_query
    # callback data: rc_fmt_{tier}_{lang}_{format}
    payload = query.data.replace("rc_fmt_", "")
    # format is the last part: text, pdf, both
    parts = payload.rsplit("_", 1)
    rest, fmt = parts[0], parts[1]
    # rest = {tier}_{lang}
    rest_parts = rest.rsplit("_", 1)
    tier_value, lang = rest_parts[0], rest_parts[1]
    query.answer()

    profile = db.get_profile()
    if not profile or not profile.name:
        query.edit_message_text(
            "Profil belum diisi. Isi dulu via web dashboard /profile.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    active = [s for s in profile.platform_stats if s.avg_monthly_impressions > 0]
    if not active:
        query.edit_message_text(
            "Stats belum diisi. Update dulu via /stats.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    defaults = _defaults()
    all_packages = build_all_packages(profile, defaults)

    # Filter by tier
    if tier_value == "all":
        packages = all_packages
    else:
        packages = [p for p in all_packages if p.tier.value == tier_value]

    if fmt == "text":
        _send_rate_card_text(query, profile, packages, lang, "influencer")
    elif fmt == "pdf":
        query.edit_message_text("⏳ Generating PDF...")
        _send_rate_card_pdf(query, profile, packages, "influencer", lang)
    elif fmt == "both":
        _send_rate_card_text(query, profile, packages, lang, "influencer")
        _send_rate_card_pdf(query, profile, packages, "influencer", lang)


# ── Affiliate flow: lang → format → output ──

def cb_rc_aff_lang(update: Update, context: CallbackContext):
    """Affiliate language selected → show format picker."""
    query = update.callback_query
    lang = query.data.replace("rc_aff_lang_", "")
    query.answer()
    lang_label = "🇮🇩 Bahasa Indonesia" if lang == "id" else "🇬🇧 English"
    query.edit_message_text(
        f"🛍 Affiliate Rate Card\nBahasa: {lang_label}\n\nMau output format apa?",
        reply_markup=ratecard_aff_format_keyboard(lang),
    )


def cb_rc_aff_format(update: Update, context: CallbackContext):
    """Affiliate format selected → send affiliate-only output."""
    query = update.callback_query
    # callback: rc_aff_fmt_{lang}_{format}
    payload = query.data.replace("rc_aff_fmt_", "")
    parts = payload.rsplit("_", 1)
    lang, fmt = parts[0], parts[1]
    query.answer()

    profile = db.get_profile()
    if not profile or not profile.name:
        query.edit_message_text("Profil belum diisi.", reply_markup=back_to_menu_keyboard())
        return
    if not profile.has_affiliate:
        query.edit_message_text("Data affiliate belum ada. Setup dulu via /stats.", reply_markup=back_to_menu_keyboard())
        return

    if fmt == "text":
        _send_rate_card_text(query, profile, [], lang, "affiliate")
    elif fmt == "pdf":
        query.edit_message_text("⏳ Generating PDF...")
        _send_rate_card_pdf(query, profile, [], "affiliate", lang)
    elif fmt == "both":
        _send_rate_card_text(query, profile, [], lang, "affiliate")
        _send_rate_card_pdf(query, profile, [], "affiliate", lang)


def cb_rc_aff_pdf(update: Update, context: CallbackContext):
    """Quick affiliate PDF from after-keyboard."""
    query = update.callback_query
    query.answer("Generating PDF...")
    profile = db.get_profile()
    if not profile:
        query.answer("Profil kosong!", show_alert=True)
        return
    out_path = PROPOSALS_DIR / "rate_card_affiliate.pdf"
    generate_rate_card(profile, [], out_path, RATE_CARD_TEMPLATE_PATH, mode="affiliate")
    with open(out_path, "rb") as f:
        query.message.reply_document(
            document=InputFile(f, filename="rate_card_affiliate.pdf"),
            caption=f"Rate Card (Affiliate) — {profile.name}",
        )


def cb_rc_pdf(update: Update, context: CallbackContext):
    """Quick influencer PDF from after-keyboard."""
    query = update.callback_query
    query.answer("Generating PDF...")
    profile = db.get_profile()
    if not profile:
        query.answer("Profil kosong!", show_alert=True)
        return
    defaults = _defaults()
    packages = build_all_packages(profile, defaults)
    out_path = PROPOSALS_DIR / "rate_card_influencer.pdf"
    generate_rate_card(profile, packages, out_path, RATE_CARD_TEMPLATE_PATH, mode="influencer")
    with open(out_path, "rb") as f:
        query.message.reply_document(
            document=InputFile(f, filename="rate_card_influencer.pdf"),
            caption=f"Rate Card (Influencer) — {profile.name}",
        )


# ──────────────────────────────────────────────────────────
# /stats — update platform stats
# ──────────────────────────────────────────────────────────

def cmd_stats(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Pilih platform yang mau diupdate:",
        reply_markup=stats_platform_keyboard(),
    )


def cb_stats_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Pilih platform yang mau diupdate:", reply_markup=stats_platform_keyboard())


def cb_stats_platform(update: Update, context: CallbackContext):
    query = update.callback_query
    raw = query.data.replace("stats_", "")
    query.answer()
    user_id = query.from_user.id

    # Affiliate platform (stats_aff_tiktok_shop, stats_aff_shopee_affiliate)
    if raw.startswith("aff_"):
        aff_val = raw.replace("aff_", "")
        _conv_data[user_id] = {"step": "aff_gmv", "aff_platform": aff_val}
        label = AFFILIATE_PLATFORM_LABELS.get(AffiliatePlatform(aff_val), aff_val)

        # Show current stats if any
        profile = db.get_profile()
        current = ""
        if profile:
            aff = profile.get_affiliate_stats(AffiliatePlatform(aff_val))
            if aff and aff.avg_monthly_gmv > 0:
                from ratecard.core.pricing import format_idr as _fmt
                current = (
                    f"\n\n📊 Stats saat ini:"
                    f"\n  GMV/bln: {_fmt(aff.avg_monthly_gmv)}"
                    f"\n  Conv rate: {aff.avg_conversion_rate*100:.2f}%"
                    f"\n  Avg commission: {aff.avg_commission_pct*100:.2f}%"
                )

        query.edit_message_text(
            f"🛍 Update stats {label}{current}"
            f"\n\nKirim GMV bulanan rata-rata (Rp, contoh: 50000000):",
        )
        return STATS_VALUE

    # Regular social platform
    platform_value = raw
    _conv_data[user_id] = {"step": "followers", "platform": platform_value}
    label = PLATFORM_LABELS.get(Platform(platform_value), platform_value)

    # Show current stats if any
    profile = db.get_profile()
    current = ""
    if profile:
        s = profile.get_stats(Platform(platform_value))
        if s and s.followers > 0:
            current = (
                f"\n\n📊 Stats saat ini:"
                f"\n  Followers: {s.followers:,}"
                f"\n  Avg Views: {s.avg_views:,}"
                f"\n  ER: {s.engagement_rate*100:.2f}%"
                f"\n  Impressions/bln: {s.avg_monthly_impressions:,}"
            )

    query.edit_message_text(
        f"📱 Update stats {label}{current}"
        f"\n\nKirim jumlah followers kamu (angka saja, contoh: 50000):",
    )
    return STATS_VALUE


def handle_stats_input(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    data = _conv_data.get(user_id, {})
    step = data.get("step")

    try:
        value = float(update.message.text.strip().replace(",", "").replace(".", ""))
    except ValueError:
        update.message.reply_text("Format salah. Kirim angka saja, contoh: 50000")
        return STATS_VALUE

    # ── Affiliate stats flow ──
    if step == "aff_gmv":
        data["aff_gmv"] = int(value)
        data["step"] = "aff_conv"
        update.message.reply_text("Conversion rate dalam persen (contoh: 3.5 untuk 3.5%):")
        _conv_data[user_id] = data
        return STATS_VALUE

    if step == "aff_conv":
        data["aff_conv"] = value / 100
        data["step"] = "aff_comm"
        update.message.reply_text("Avg commission yang biasa lo dapet (%, contoh: 8 untuk 8%):")
        _conv_data[user_id] = data
        return STATS_VALUE

    if step == "aff_comm":
        data["aff_comm"] = value / 100
        aff_val = data["aff_platform"]
        stats = AffiliateStats(
            platform=AffiliatePlatform(aff_val),
            avg_monthly_gmv=data["aff_gmv"],
            avg_conversion_rate=data["aff_conv"],
            avg_commission_pct=data["aff_comm"],
            enabled=True,
        )
        db.upsert_affiliate_stats(stats)
        label = AFFILIATE_PLATFORM_LABELS.get(AffiliatePlatform(aff_val), aff_val)
        gmv_fmt = f"{stats.avg_monthly_gmv:,}".replace(",", ".")
        update.message.reply_text(
            f"✅ Stats {label} berhasil disimpan!\n\n"
            f"GMV/bulan: Rp {gmv_fmt}\n"
            f"Conversion Rate: {stats.avg_conversion_rate*100:.2f}%\n"
            f"Avg Commission: {stats.avg_commission_pct*100:.2f}%",
            reply_markup=stats_platform_keyboard(),
        )
        del _conv_data[user_id]
        return ConversationHandler.END

    # ── Social media stats flow ──
    platform_value = data.get("platform")

    if step == "followers":
        data["followers"] = int(value)
        data["step"] = "avg_views"
        update.message.reply_text("Rata-rata views per konten (contoh: 15000):")
    elif step == "avg_views":
        data["avg_views"] = int(value)
        data["step"] = "er"
        update.message.reply_text("Engagement rate dalam persen (contoh: 4.5 untuk 4.5%):")
    elif step == "er":
        data["er"] = value / 100
        data["step"] = "impressions"
        update.message.reply_text("Rata-rata impressions per bulan (contoh: 300000):")
    elif step == "impressions":
        data["impressions"] = int(value)
        stats = PlatformStats(
            platform=Platform(platform_value),
            followers=data["followers"],
            avg_views=data["avg_views"],
            engagement_rate=data["er"],
            avg_monthly_impressions=data["impressions"],
        )
        db.upsert_platform_stats(stats)
        platform_label = PLATFORM_LABELS.get(Platform(platform_value), platform_value)
        update.message.reply_text(
            f"✅ Stats {platform_label} berhasil disimpan!\n\n"
            f"Followers: {stats.followers:,}\n"
            f"Avg Views: {stats.avg_views:,}\n"
            f"Engagement Rate: {stats.engagement_rate*100:.2f}%\n"
            f"Avg Monthly Impressions: {stats.avg_monthly_impressions:,}",
            reply_markup=stats_platform_keyboard(),
        )
        del _conv_data[user_id]
        return ConversationHandler.END

    _conv_data[user_id] = data
    return STATS_VALUE


# ──────────────────────────────────────────────────────────
# /proposal wizard
# ──────────────────────────────────────────────────────────

def cmd_proposal(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    _conv_data[user_id] = {}
    update.message.reply_text(
        "Buat proposal baru.\n\nKirim *nama klien*:",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    return PROP_CLIENT_NAME


def cb_prop_start(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    _conv_data[user_id] = {}
    query.edit_message_text(
        "Buat proposal baru\\.\n\nKirim *nama klien*:",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    return PROP_CLIENT_NAME


def handle_client_name(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    _conv_data[user_id]["client_name"] = update.message.text.strip()
    update.message.reply_text("Nama *perusahaan* klien (atau ketik `-` jika tidak ada):",
                               parse_mode=ParseMode.MARKDOWN_V2)
    return PROP_CLIENT_COMPANY


def handle_client_company(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    val = update.message.text.strip()
    _conv_data[user_id]["client_company"] = "" if val == "-" else val
    update.message.reply_text("Nama *campaign* / produk yang mau di-endorse:",
                               parse_mode=ParseMode.MARKDOWN_V2)
    return PROP_CAMPAIGN


def handle_campaign(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    _conv_data[user_id]["campaign"] = update.message.text.strip()
    update.message.reply_text("Pilih *tier paket*:", parse_mode=ParseMode.MARKDOWN_V2,
                               reply_markup=tier_select_keyboard())
    return PROP_TIER


def cb_tier_select(update: Update, context: CallbackContext):
    query = update.callback_query
    tier_value = query.data.replace("tier_", "")
    query.answer()
    user_id = query.from_user.id
    _conv_data[user_id]["tier"] = tier_value
    _conv_data[user_id]["selected_platforms"] = []
    query.edit_message_text(
        "Pilih *platform* yang dimasukkan ke proposal (bisa lebih dari 1):",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=platform_select_keyboard(selected=[]),
    )
    return PROP_PLATFORMS


def cb_platform_toggle(update: Update, context: CallbackContext):
    query = update.callback_query
    platform_value = query.data.replace("plat_", "")
    query.answer()
    user_id = query.from_user.id
    selected = _conv_data[user_id].get("selected_platforms", [])

    if platform_value in selected:
        selected.remove(platform_value)
    else:
        selected.append(platform_value)

    _conv_data[user_id]["selected_platforms"] = selected
    query.edit_message_reply_markup(
        reply_markup=platform_select_keyboard(selected=selected)
    )
    return PROP_PLATFORMS


def cb_platform_done(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = _conv_data[user_id]
    selected = data.get("selected_platforms", [])

    if not selected:
        query.answer("Pilih minimal 1 platform!", show_alert=True)
        return PROP_PLATFORMS

    profile = db.get_profile()
    if not profile:
        query.edit_message_text("Profil belum ada. Setup dulu via /setprofile.")
        return ConversationHandler.END

    defaults = _defaults()
    platforms = [Platform(p) for p in selected]
    tier = TierName(data["tier"])
    pkg = build_package(profile, tier, platforms=platforms, defaults=defaults)

    data["package"] = pkg
    _conv_data[user_id] = data

    # Show summary
    lines = [
        f"*Konfirmasi Proposal*\n",
        f"Klien: {data['client_name']}",
        f"Perusahaan: {data.get('client_company') or '-'}",
        f"Campaign: {data['campaign']}",
        f"Paket: {pkg.name}",
        f"Platform: {', '.join(PLATFORM_LABELS.get(Platform(p), p) for p in selected)}",
        f"Total: *{format_idr(pkg.final_price)}*",
        f"\nLanjut simpan proposal?",
    ]
    query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN_V2 if False else None,  # plain text for simplicity
        reply_markup=proposal_confirm_keyboard(),
    )
    return PROP_CONFIRM


def cb_prop_confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer("Menyimpan...")
    user_id = query.from_user.id
    data = _conv_data.get(user_id, {})
    pkg = data.get("package")

    if not pkg:
        query.edit_message_text("Data proposal hilang. Coba lagi /proposal.")
        return ConversationHandler.END

    proposal = Proposal(
        client_name=data["client_name"],
        client_company=data.get("client_company", ""),
        campaign_name=data["campaign"],
        packages=[pkg],
        total_price=pkg.final_price,
        status=ProposalStatus.SENT,
    )

    proposal_id = db.create_proposal(proposal)
    proposal.id = proposal_id

    # Generate PDF
    profile = db.get_profile()
    pdf_path = PROPOSALS_DIR / f"proposal_{proposal_id}.pdf"
    generate_proposal(proposal, profile, pdf_path, RATE_CARD_TEMPLATE_PATH)

    # Update DB with pdf path
    proposal.pdf_path = str(pdf_path)
    db.update_proposal(proposal)

    # Send PDF
    with open(pdf_path, "rb") as f:
        query.message.reply_document(
            document=InputFile(f, filename=f"proposal_{proposal_id}.pdf"),
            caption=f"Proposal untuk {data['client_name']} — {data['campaign']}\nTotal: {format_idr(pkg.final_price)}",
            reply_markup=proposal_action_keyboard(proposal_id),
        )

    query.edit_message_text(f"Proposal #{proposal_id} berhasil dibuat dan dikirim!")
    del _conv_data[user_id]
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────
# /history
# ──────────────────────────────────────────────────────────

def cmd_history(update: Update, context: CallbackContext):
    proposals = db.list_proposals(limit=10)
    msg = format_proposal_history(proposals)
    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2,
                               reply_markup=back_to_menu_keyboard())


def cb_history(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    proposals = db.list_proposals(limit=10)
    msg = format_proposal_history(proposals)
    query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN_V2,
                             reply_markup=back_to_menu_keyboard())


# ──────────────────────────────────────────────────────────
# Proposal status updates
# ──────────────────────────────────────────────────────────

def cb_prop_accept(update: Update, context: CallbackContext):
    query = update.callback_query
    proposal_id = int(query.data.replace("prop_accept_", ""))
    proposal = db.get_proposal(proposal_id)
    if proposal:
        proposal.status = ProposalStatus.ACCEPTED
        db.update_proposal(proposal)
        query.answer("Proposal ditandai ACCEPTED")
        query.edit_message_reply_markup(reply_markup=proposal_action_keyboard(proposal_id))
    else:
        query.answer("Proposal tidak ditemukan", show_alert=True)


def cb_prop_reject(update: Update, context: CallbackContext):
    query = update.callback_query
    proposal_id = int(query.data.replace("prop_reject_", ""))
    proposal = db.get_proposal(proposal_id)
    if proposal:
        proposal.status = ProposalStatus.REJECTED
        db.update_proposal(proposal)
        query.answer("Proposal ditandai REJECTED")
        query.edit_message_reply_markup(reply_markup=proposal_action_keyboard(proposal_id))
    else:
        query.answer("Proposal tidak ditemukan", show_alert=True)


def cb_prop_pdf(update: Update, context: CallbackContext):
    query = update.callback_query
    proposal_id = int(query.data.replace("prop_pdf_", ""))
    proposal = db.get_proposal(proposal_id)
    if not proposal:
        query.answer("Proposal tidak ditemukan", show_alert=True)
        return
    query.answer("Generating PDF...")
    profile = db.get_profile()
    pdf_path = PROPOSALS_DIR / f"proposal_{proposal_id}.pdf"
    generate_proposal(proposal, profile, pdf_path, RATE_CARD_TEMPLATE_PATH)
    with open(pdf_path, "rb") as f:
        query.message.reply_document(
            document=InputFile(f, filename=f"proposal_{proposal_id}.pdf"),
            caption=f"Proposal #{proposal_id} — {proposal.client_name}",
        )


# ──────────────────────────────────────────────────────────
# /exportxlsx
# ──────────────────────────────────────────────────────────

def cmd_exportxlsx(update: Update, context: CallbackContext):
    from ratecard.outputs.xlsx_exporter import export_xlsx
    from config import DATA_DIR
    profile = db.get_profile()
    if not profile:
        update.message.reply_text("Profil belum ada.")
        return
    defaults = _defaults()
    packages = build_all_packages(profile, defaults)
    proposals = db.list_proposals(limit=100)
    out_path = DATA_DIR / "rate_card.xlsx"
    export_xlsx(profile, packages, proposals, out_path)
    with open(out_path, "rb") as f:
        update.message.reply_document(
            document=InputFile(f, filename="rate_card.xlsx"),
            caption="Rate Card & Proposal History",
        )


def cb_export_xlsx(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer("Generating Excel...")
    from ratecard.outputs.xlsx_exporter import export_xlsx
    from config import DATA_DIR
    profile = db.get_profile()
    if not profile:
        query.answer("Profil belum ada!", show_alert=True)
        return
    defaults = _defaults()
    packages = build_all_packages(profile, defaults)
    proposals = db.list_proposals(limit=100)
    out_path = DATA_DIR / "rate_card.xlsx"
    export_xlsx(profile, packages, proposals, out_path)
    with open(out_path, "rb") as f:
        query.message.reply_document(
            document=InputFile(f, filename="rate_card.xlsx"),
            caption="Rate Card & Proposal History",
        )


# ──────────────────────────────────────────────────────────
# /addon — manage custom add-ons
# ──────────────────────────────────────────────────────────

def _addon_view_text(addons):
    """Build the unified add-on view text."""
    if not addons:
        return (
            "🧩 Custom Add-ons\n\n"
            "Belum ada add-on. Tap tombol di bawah untuk tambah."
        )
    lines = ["🧩 Custom Add-ons\n"]
    lines.append("Tap nama untuk enable/disable, 🗑 untuk hapus.\n")
    for a in addons:
        st = "✅" if a.enabled else "⬜"
        cat = "🎬" if a.category == "influencer" else "🛍"
        if a.price_type == "percentage":
            price = f"+{a.price_value:.0f}%"
        else:
            price = f"Rp {a.price_value:,.0f}".replace(",", ".")
        desc = f" — {a.description}" if a.description else ""
        lines.append(f"{st} {cat} {a.name} ({price}){desc}")
    return "\n".join(lines)


def cmd_addon(update: Update, context: CallbackContext):
    addons = db.list_custom_addons()
    update.message.reply_text(
        _addon_view_text(addons),
        reply_markup=addon_list_keyboard(addons),
    )


def cb_addon_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    addons = db.list_custom_addons()
    query.edit_message_text(
        _addon_view_text(addons),
        reply_markup=addon_list_keyboard(addons),
    )


def cb_addon_toggle(update: Update, context: CallbackContext):
    query = update.callback_query
    addon_id = int(query.data.replace("addon_toggle_", ""))
    addons = db.list_custom_addons()
    target = next((a for a in addons if a.id == addon_id), None)
    if target:
        target.enabled = not target.enabled
        db.update_custom_addon(target)
        status = "enabled ✅" if target.enabled else "disabled ⬜"
        query.answer(f"{target.name} {status}")
    else:
        query.answer("Add-on tidak ditemukan", show_alert=True)
        return
    addons = db.list_custom_addons()
    query.edit_message_text(_addon_view_text(addons), reply_markup=addon_list_keyboard(addons))


def cb_addon_del(update: Update, context: CallbackContext):
    query = update.callback_query
    addon_id = int(query.data.replace("addon_del_", ""))
    addons = db.list_custom_addons()
    target = next((a for a in addons if a.id == addon_id), None)
    if target:
        db.delete_custom_addon(addon_id)
        query.answer(f"{target.name} dihapus!")
    else:
        query.answer("Add-on tidak ditemukan", show_alert=True)
        return
    addons = db.list_custom_addons()
    query.edit_message_text(_addon_view_text(addons), reply_markup=addon_list_keyboard(addons))


def cb_addon_add(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    _conv_data[user_id] = {"addon_flow": True}
    query.edit_message_text(
        "➕ Tambah Add-on Baru\n\nPilih kategori:",
        reply_markup=addon_category_keyboard(),
    )
    return ADDON_NAME


def cb_addon_cat(update: Update, context: CallbackContext):
    query = update.callback_query
    cat = query.data.replace("addon_cat_", "")
    query.answer()
    user_id = query.from_user.id
    _conv_data[user_id]["category"] = cat
    cat_label = "🎬 Influencer" if cat == "influencer" else "🛍 Affiliate"
    query.edit_message_text(f"Kategori: {cat_label}\n\nKirim nama add-on:")
    return ADDON_NAME


def handle_addon_name(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    _conv_data[user_id]["name"] = update.message.text.strip()
    update.message.reply_text("Deskripsi singkat (atau ketik - untuk skip):")
    return ADDON_DESC


def handle_addon_desc(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    val = update.message.text.strip()
    _conv_data[user_id]["description"] = "" if val == "-" else val
    update.message.reply_text(
        "Tipe harga:",
        reply_markup=addon_pricetype_keyboard(),
    )
    return ADDON_PRICE_VALUE


def cb_addon_pricetype(update: Update, context: CallbackContext):
    query = update.callback_query
    pt = query.data.replace("addon_pt_", "")
    query.answer()
    user_id = query.from_user.id
    _conv_data[user_id]["price_type"] = pt
    if pt == "percentage":
        query.edit_message_text("Kirim nilai persentase (contoh: 20 untuk +20%):")
    else:
        query.edit_message_text("Kirim harga tetap dalam Rp (contoh: 500000):")
    return ADDON_PRICE_VALUE


def handle_addon_price(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    data = _conv_data.get(user_id, {})
    try:
        value = float(update.message.text.strip().replace(",", "").replace(".", ""))
    except ValueError:
        update.message.reply_text("Format salah. Kirim angka saja.")
        return ADDON_PRICE_VALUE

    data["price_value"] = value
    _conv_data[user_id] = data

    cat_label = "🎬 Influencer" if data.get("category") == "influencer" else "🛍 Affiliate"
    if data.get("price_type") == "percentage":
        price_str = f"+{value:.0f}%"
    else:
        price_str = f"Rp {value:,.0f}".replace(",", ".")

    summary = (
        f"📋 Konfirmasi Add-on:\n\n"
        f"Nama: {data['name']}\n"
        f"Deskripsi: {data.get('description') or '-'}\n"
        f"Kategori: {cat_label}\n"
        f"Harga: {price_str}\n\n"
        f"Simpan?"
    )
    update.message.reply_text(summary, reply_markup=addon_confirm_keyboard())
    return ADDON_PRICE_VALUE


def cb_addon_save(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer("Menyimpan...")
    user_id = query.from_user.id
    data = _conv_data.get(user_id, {})

    addon = CustomAddOn(
        name=data["name"],
        description=data.get("description", ""),
        price_type=data.get("price_type", "percentage"),
        price_value=data.get("price_value", 0),
        category=data.get("category", "influencer"),
        enabled=True,
    )
    db.create_custom_addon(addon)
    del _conv_data[user_id]
    # Return to unified view
    addons = db.list_custom_addons()
    query.edit_message_text(
        f"✅ \"{addon.name}\" ditambahkan!\n\n" + _addon_view_text(addons),
        reply_markup=addon_list_keyboard(addons),
    )
    return ConversationHandler.END


def cb_addon_cancel(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer("Dibatalkan")
    user_id = query.from_user.id
    _conv_data.pop(user_id, None)
    addons = db.list_custom_addons()
    query.edit_message_text(_addon_view_text(addons), reply_markup=addon_list_keyboard(addons))
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────
# Cancel / menu callbacks
# ──────────────────────────────────────────────────────────

def cb_cancel(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer("Dibatalkan")
    user_id = query.from_user.id
    _conv_data.pop(user_id, None)
    query.edit_message_text("Dibatalkan.", reply_markup=back_to_menu_keyboard())
    return ConversationHandler.END


def cb_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Menu Rate Card:", reply_markup=main_menu_keyboard())


# ──────────────────────────────────────────────────────────
# Registration
# ──────────────────────────────────────────────────────────

def register_ratecard_handlers(dp: Dispatcher):
    """Register all rate card handlers on the given dispatcher."""

    # Stats update conversation
    stats_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_stats_platform, pattern=r"^stats_(?!menu)"),
        ],
        states={
            STATS_VALUE: [MessageHandler(Filters.text & ~Filters.command, handle_stats_input)],
        },
        fallbacks=[CallbackQueryHandler(cb_cancel, pattern="^cancel$")],
    )

    # Proposal creation conversation
    proposal_conv = ConversationHandler(
        entry_points=[
            CommandHandler("proposal", cmd_proposal),
            CallbackQueryHandler(cb_prop_start, pattern="^prop_start$"),
        ],
        states={
            PROP_CLIENT_NAME:    [MessageHandler(Filters.text & ~Filters.command, handle_client_name)],
            PROP_CLIENT_COMPANY: [MessageHandler(Filters.text & ~Filters.command, handle_client_company)],
            PROP_CAMPAIGN:       [MessageHandler(Filters.text & ~Filters.command, handle_campaign)],
            PROP_TIER:           [CallbackQueryHandler(cb_tier_select, pattern=r"^tier_")],
            PROP_PLATFORMS:      [
                CallbackQueryHandler(cb_platform_toggle, pattern=r"^plat_(?!done)"),
                CallbackQueryHandler(cb_platform_done, pattern="^plat_done$"),
            ],
            PROP_CONFIRM:        [CallbackQueryHandler(cb_prop_confirm, pattern="^prop_confirm$")],
        },
        fallbacks=[CallbackQueryHandler(cb_cancel, pattern="^cancel$")],
    )

    # Add-on management conversation
    addon_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_addon_add, pattern="^addon_add$"),
        ],
        states={
            ADDON_NAME: [
                CallbackQueryHandler(cb_addon_cat, pattern=r"^addon_cat_"),
                MessageHandler(Filters.text & ~Filters.command, handle_addon_name),
            ],
            ADDON_DESC: [
                MessageHandler(Filters.text & ~Filters.command, handle_addon_desc),
            ],
            ADDON_PRICE_VALUE: [
                CallbackQueryHandler(cb_addon_pricetype, pattern=r"^addon_pt_"),
                CallbackQueryHandler(cb_addon_save, pattern="^addon_save$"),
                MessageHandler(Filters.text & ~Filters.command, handle_addon_price),
            ],
        },
        fallbacks=[CallbackQueryHandler(cb_addon_cancel, pattern="^addon_cancel$")],
    )

    # Single entry: /start shows main menu, everything else via inline buttons
    dp.add_handler(CommandHandler("start", cmd_start))

    dp.add_handler(proposal_conv)
    dp.add_handler(stats_conv)
    dp.add_handler(addon_conv)

    # Rate card interactive flow — category → tier → lang → format
    dp.add_handler(CallbackQueryHandler(cb_rc_cat_menu,       pattern="^rc_cat_menu$"))
    dp.add_handler(CallbackQueryHandler(cb_rc_cat_influencer, pattern="^rc_cat_influencer$"))
    dp.add_handler(CallbackQueryHandler(cb_rc_cat_affiliate,  pattern="^rc_cat_affiliate$"))
    dp.add_handler(CallbackQueryHandler(cb_rc_tier_menu,      pattern="^rc_tier_menu$"))
    dp.add_handler(CallbackQueryHandler(cb_rc_tier,           pattern=r"^rc_tier_(?!menu)"))
    dp.add_handler(CallbackQueryHandler(cb_rc_lang,           pattern=r"^rc_lang_"))
    dp.add_handler(CallbackQueryHandler(cb_rc_format,         pattern=r"^rc_fmt_"))
    dp.add_handler(CallbackQueryHandler(cb_rc_aff_lang,       pattern=r"^rc_aff_lang_"))
    dp.add_handler(CallbackQueryHandler(cb_rc_aff_format,     pattern=r"^rc_aff_fmt_"))
    dp.add_handler(CallbackQueryHandler(cb_rc_aff_pdf,        pattern="^rc_aff_pdf$"))
    dp.add_handler(CallbackQueryHandler(cb_rc_pdf,            pattern="^rc_pdf$"))

    # Add-on management callbacks (non-conversation)
    dp.add_handler(CallbackQueryHandler(cb_addon_menu,    pattern="^addon_menu$"))
    dp.add_handler(CallbackQueryHandler(cb_addon_toggle,  pattern=r"^addon_toggle_\d+$"))
    dp.add_handler(CallbackQueryHandler(cb_addon_del,     pattern=r"^addon_del_\d+$"))

    # Other callback handlers
    dp.add_handler(CallbackQueryHandler(cb_stats_menu,   pattern="^stats_menu$"))
    dp.add_handler(CallbackQueryHandler(cb_history,     pattern="^history$"))
    dp.add_handler(CallbackQueryHandler(cb_export_xlsx, pattern="^export_xlsx$"))
    dp.add_handler(CallbackQueryHandler(cb_menu,        pattern="^menu$"))
    dp.add_handler(CallbackQueryHandler(cb_prop_accept, pattern=r"^prop_accept_\d+$"))
    dp.add_handler(CallbackQueryHandler(cb_prop_reject, pattern=r"^prop_reject_\d+$"))
    dp.add_handler(CallbackQueryHandler(cb_prop_pdf,    pattern=r"^prop_pdf_\d+$"))

    log.info("Rate card handlers registered.")
