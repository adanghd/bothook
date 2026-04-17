"""
Flask web dashboard for Rate Card Manager.
Local only (127.0.0.1), no authentication needed.
"""
import json
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, send_file, url_for

import config
from ratecard.core import database as db
from ratecard.core.models import (
    ADDON_LABELS,
    ADDON_PRICE_PCT,
    AFFILIATE_CATEGORIES,
    AFFILIATE_PLATFORM_LABELS,
    CONTENT_TYPE_LABELS,
    PAYMENT_SCHEME_FEES,
    PAYMENT_SCHEME_LABELS,
    PLATFORM_LABELS,
    PRICING_MODEL_LABELS,
    TIER_BONUSES,
    AddOnType,
    AffiliatePlatform,
    AffiliateStats,
    AffiliateTerms,
    CreatorProfile,
    CustomAddOn,
    PaymentScheme,
    Platform,
    PlatformStats,
    PricingModel,
    Proposal,
    ProposalStatus,
)
from ratecard.core.packages import build_all_packages
from ratecard.core.pricing import calculate_affiliate_rate, format_idr, load_defaults
from ratecard.outputs.pdf_generator import generate_proposal, generate_rate_card


def create_app() -> Flask:
    templates_dir = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(templates_dir))
    app.secret_key = "ratecard-local-secret"

    db.init_db(config.DB_PATH)

    def _defaults():
        return load_defaults(config.PLATFORM_DEFAULTS_PATH)

    # ── Context processors ────────────────────────────────
    @app.context_processor
    def inject_globals():
        return {
            "format_idr": format_idr,
            "PLATFORM_LABELS": PLATFORM_LABELS,
            "CONTENT_TYPE_LABELS": CONTENT_TYPE_LABELS,
            "AFFILIATE_PLATFORM_LABELS": AFFILIATE_PLATFORM_LABELS,
            "AFFILIATE_CATEGORIES": AFFILIATE_CATEGORIES,
            "PRICING_MODEL_LABELS": PRICING_MODEL_LABELS,
            "PAYMENT_SCHEME_LABELS": PAYMENT_SCHEME_LABELS,
            "PAYMENT_SCHEME_FEES": PAYMENT_SCHEME_FEES,
            "ADDON_LABELS": ADDON_LABELS,
            "ADDON_PRICE_PCT": ADDON_PRICE_PCT,
            "TIER_BONUSES": TIER_BONUSES,
        }

    # ── Dashboard ─────────────────────────────────────────
    @app.route("/")
    def dashboard():
        profile = db.get_profile()
        proposals = db.list_proposals(limit=5)
        defaults = _defaults()
        packages = []
        affiliate_suggestions = {}
        if profile:
            if any(s.avg_monthly_impressions > 0 for s in profile.platform_stats):
                packages = build_all_packages(profile, defaults)
            for aff_stats in profile.affiliate_stats:
                if aff_stats.enabled and aff_stats.avg_monthly_gmv > 0:
                    affiliate_suggestions[aff_stats.platform.value] = calculate_affiliate_rate(
                        aff_stats.platform.value,
                        aff_stats.avg_monthly_gmv,
                        aff_stats.avg_conversion_rate,
                        aff_stats.avg_commission_pct,
                    )
        return render_template(
            "dashboard.html",
            profile=profile,
            proposals=proposals,
            packages=packages,
            affiliate_suggestions=affiliate_suggestions,
            active="dashboard",
        )

    # ── Profile ───────────────────────────────────────────
    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        current = db.get_profile() or CreatorProfile()

        if request.method == "POST":
            form = request.form
            current.name = form.get("name", "").strip()
            current.niche = form.get("niche", "").strip()
            current.location = form.get("location", "").strip()
            current.contact_email = form.get("contact_email", "").strip()
            current.brand_color_hex = form.get("brand_color_hex", "#E91E8C").strip()

            db.save_profile(current)

            # Save platform stats
            for platform in Platform:
                followers_key = f"followers_{platform.value}"
                if followers_key in form:
                    try:
                        stats = PlatformStats(
                            platform=platform,
                            followers=int(form.get(f"followers_{platform.value}", 0) or 0),
                            avg_views=int(form.get(f"avg_views_{platform.value}", 0) or 0),
                            engagement_rate=float(form.get(f"er_{platform.value}", 0) or 0) / 100,
                            avg_monthly_impressions=int(form.get(f"impressions_{platform.value}", 0) or 0),
                        )
                        db.upsert_platform_stats(stats)
                    except (ValueError, TypeError):
                        pass

            # Save affiliate categories (cross-platform)
            current.affiliate_categories = form.getlist("affiliate_categories")
            db.save_profile(current)

            # Save affiliate stats per platform
            for aff_platform in AffiliatePlatform:
                gmv_key = f"aff_gmv_{aff_platform.value}"
                if gmv_key in form:
                    try:
                        aff_stats = AffiliateStats(
                            platform=aff_platform,
                            avg_monthly_gmv=int(form.get(f"aff_gmv_{aff_platform.value}", 0) or 0),
                            avg_conversion_rate=float(form.get(f"aff_conv_{aff_platform.value}", 0) or 0) / 100,
                            avg_commission_pct=float(form.get(f"aff_comm_{aff_platform.value}", 0) or 0) / 100,
                            enabled=form.get(f"aff_enabled_{aff_platform.value}") == "on",
                        )
                        db.upsert_affiliate_stats(aff_stats)
                    except (ValueError, TypeError):
                        pass

            return redirect(url_for("dashboard"))

        return render_template(
            "profile.html",
            profile=current,
            platforms=list(Platform),
            affiliate_platforms=list(AffiliatePlatform),
            active="profile",
        )

    # ── Rate Card ─────────────────────────────────────────
    @app.route("/ratecard")
    def ratecard():
        profile = db.get_profile()
        if not profile:
            return redirect(url_for("profile"))
        defaults = _defaults()
        packages = build_all_packages(profile, defaults)

        affiliate_suggestions = {}
        for aff_stats in profile.affiliate_stats:
            if aff_stats.enabled and aff_stats.avg_monthly_gmv > 0:
                affiliate_suggestions[aff_stats.platform.value] = calculate_affiliate_rate(
                    aff_stats.platform.value,
                    aff_stats.avg_monthly_gmv,
                    aff_stats.avg_conversion_rate,
                    aff_stats.avg_commission_pct,
                )

        custom_addons = db.list_custom_addons()
        return render_template(
            "ratecard.html",
            profile=profile,
            packages=packages,
            affiliate_suggestions=affiliate_suggestions,
            custom_addons=custom_addons,
            addon_types=list(AddOnType),
            active="ratecard",
        )

    @app.route("/ratecard/pdf")
    def ratecard_pdf():
        profile = db.get_profile()
        if not profile:
            abort(404)
        defaults = _defaults()
        packages = build_all_packages(profile, defaults)
        out_path = config.PROPOSALS_DIR / "rate_card.pdf"
        generate_rate_card(profile, packages, out_path, config.RATE_CARD_TEMPLATE_PATH)
        return send_file(out_path, as_attachment=True, download_name="rate_card.pdf")

    # ── Proposals ─────────────────────────────────────────
    @app.route("/proposals")
    def proposals():
        all_proposals = db.list_proposals(limit=50)
        return render_template(
            "proposals.html",
            proposals=all_proposals,
            active="proposals",
        )

    @app.route("/proposal/new", methods=["GET", "POST"])
    def proposal_new():
        profile = db.get_profile()
        if not profile:
            return redirect(url_for("profile"))

        defaults = _defaults()

        if request.method == "POST":
            form = request.form
            client_name = form.get("client_name", "").strip()
            client_company = form.get("client_company", "").strip()
            client_email = form.get("client_email", "").strip()
            campaign_name = form.get("campaign_name", "").strip()
            tier_value = form.get("tier", "Bronze")
            selected_platforms = form.getlist("platforms")
            client_discount = float(form.get("client_discount", 0) or 0) / 100
            notes = form.get("notes", "").strip()

            pricing_model_raw = form.get("pricing_model", "flat")
            try:
                pricing_model = PricingModel(pricing_model_raw)
            except ValueError:
                pricing_model = PricingModel.FLAT

            payment_scheme_raw = form.get("payment_scheme", "dp_50")
            try:
                payment_scheme = PaymentScheme(payment_scheme_raw)
            except ValueError:
                payment_scheme = PaymentScheme.DP_50

            from ratecard.core.models import TierName
            from ratecard.core.packages import build_package
            platforms = [Platform(p) for p in selected_platforms if p]

            # Parse add-ons
            selected_addons_raw = form.getlist("addons")
            extra_addons = []
            for val in selected_addons_raw:
                try:
                    extra_addons.append(AddOnType(val))
                except ValueError:
                    pass
            extra_rev = int(form.get("extra_revision_rounds", 0) or 0)

            packages_out = []
            total_price = 0.0

            # Build endorsement package (unless pure commission)
            if pricing_model != PricingModel.COMMISSION:
                pkg = build_package(
                    profile=profile,
                    tier=TierName(tier_value),
                    platforms=platforms or None,
                    defaults=defaults,
                    client_discount_pct=client_discount,
                    extra_addons=extra_addons,
                    extra_revision_rounds=extra_rev,
                )
                packages_out.append(pkg)
                total_price += pkg.final_price

            # Build affiliate terms (for commission / hybrid)
            affiliate_terms = None
            if pricing_model in (PricingModel.COMMISSION, PricingModel.HYBRID):
                aff_platform_raw = form.get("aff_deal_platform", "tiktok_shop")
                commission_pct = float(form.get("commission_pct", 10) or 10) / 100
                base_fee = float(form.get("aff_base_fee", 0) or 0)
                duration_days = int(form.get("aff_duration_days", 30) or 30)
                min_campaign = float(form.get("aff_min_campaign", 0) or 0)
                categories_chosen = form.getlist("aff_deal_categories")

                aff_stats = profile.get_affiliate_stats(AffiliatePlatform(aff_platform_raw)) if aff_platform_raw else None
                projected_gmv = min_campaign if min_campaign > 0 else (aff_stats.avg_monthly_gmv if aff_stats else 0)
                projected_earning = projected_gmv * commission_pct + base_fee

                affiliate_terms = AffiliateTerms(
                    commission_pct=commission_pct,
                    base_fee=base_fee,
                    min_campaign_value=min_campaign,
                    categories=categories_chosen,
                    duration_days=duration_days,
                    projected_gmv=projected_gmv,
                    projected_earning=projected_earning,
                )
                # Total price for hybrid = base fee + projected commission
                # For commission only: total = projected commission
                if pricing_model == PricingModel.COMMISSION:
                    total_price = projected_earning
                else:  # HYBRID
                    total_price += base_fee  # projected_earning is additional

            proposal = Proposal(
                client_name=client_name,
                client_company=client_company,
                client_email=client_email,
                campaign_name=campaign_name,
                packages=packages_out,
                total_price=total_price,
                discount_pct=client_discount,
                status=ProposalStatus.DRAFT,
                pricing_model=pricing_model,
                payment_scheme=payment_scheme,
                affiliate_terms=affiliate_terms,
                notes=notes,
            )
            proposal_id = db.create_proposal(proposal)
            return redirect(url_for("proposal_detail", proposal_id=proposal_id))

        from ratecard.core.models import TierName
        packages_preview = build_all_packages(profile, defaults)

        # Pre-compute affiliate rate suggestions per platform
        affiliate_suggestions = {}
        for aff_stats in profile.affiliate_stats:
            if aff_stats.enabled and aff_stats.avg_monthly_gmv > 0:
                affiliate_suggestions[aff_stats.platform.value] = calculate_affiliate_rate(
                    aff_stats.platform.value,
                    aff_stats.avg_monthly_gmv,
                    aff_stats.avg_conversion_rate,
                    aff_stats.avg_commission_pct,
                )

        return render_template(
            "proposal_form.html",
            profile=profile,
            proposal=None,
            platforms=list(Platform),
            affiliate_platforms=list(AffiliatePlatform),
            affiliate_suggestions=affiliate_suggestions,
            tiers=list(TierName),
            packages_preview=packages_preview,
            pricing_models=list(PricingModel),
            payment_schemes=list(PaymentScheme),
            addon_types=list(AddOnType),
            active="proposals",
            is_edit=False,
        )

    @app.route("/proposal/<int:proposal_id>")
    def proposal_detail(proposal_id):
        proposal = db.get_proposal(proposal_id)
        if not proposal:
            abort(404)
        profile = db.get_profile()
        return render_template(
            "proposal_detail.html",
            proposal=proposal,
            profile=profile,
            active="proposals",
        )

    @app.route("/proposal/<int:proposal_id>/pdf")
    def proposal_pdf(proposal_id):
        proposal = db.get_proposal(proposal_id)
        if not proposal:
            abort(404)
        profile = db.get_profile()
        pdf_path = config.PROPOSALS_DIR / f"proposal_{proposal_id}.pdf"
        generate_proposal(proposal, profile, pdf_path, config.RATE_CARD_TEMPLATE_PATH)
        return send_file(pdf_path, as_attachment=True,
                         download_name=f"proposal_{proposal_id}.pdf")

    @app.route("/proposal/<int:proposal_id>/edit", methods=["GET", "POST"])
    def proposal_edit(proposal_id):
        proposal = db.get_proposal(proposal_id)
        if not proposal:
            abort(404)
        profile = db.get_profile()
        if not profile:
            return redirect(url_for("profile"))

        defaults = _defaults()

        if request.method == "POST":
            form = request.form
            proposal.client_name = form.get("client_name", "").strip()
            proposal.client_company = form.get("client_company", "").strip()
            proposal.client_email = form.get("client_email", "").strip()
            proposal.campaign_name = form.get("campaign_name", "").strip()
            proposal.notes = form.get("notes", "").strip()

            pricing_model_raw = form.get("pricing_model", "flat")
            try:
                proposal.pricing_model = PricingModel(pricing_model_raw)
            except ValueError:
                proposal.pricing_model = PricingModel.FLAT

            payment_scheme_raw = form.get("payment_scheme", "dp_50")
            try:
                proposal.payment_scheme = PaymentScheme(payment_scheme_raw)
            except ValueError:
                proposal.payment_scheme = PaymentScheme.DP_50

            client_discount = float(form.get("client_discount", 0) or 0) / 100
            proposal.discount_pct = client_discount

            proposal.packages = []
            proposal.total_price = 0.0

            if proposal.pricing_model != PricingModel.COMMISSION:
                tier_value = form.get("tier", "Silver")
                selected_platforms = form.getlist("platforms")
                from ratecard.core.models import TierName
                from ratecard.core.packages import build_package
                platforms = [Platform(p) for p in selected_platforms if p]

                selected_addons_raw = form.getlist("addons")
                extra_addons = []
                for val in selected_addons_raw:
                    try:
                        extra_addons.append(AddOnType(val))
                    except ValueError:
                        pass
                extra_rev = int(form.get("extra_revision_rounds", 0) or 0)

                pkg = build_package(
                    profile=profile,
                    tier=TierName(tier_value),
                    platforms=platforms or None,
                    defaults=defaults,
                    client_discount_pct=client_discount,
                    extra_addons=extra_addons,
                    extra_revision_rounds=extra_rev,
                )
                proposal.packages.append(pkg)
                proposal.total_price += pkg.final_price

            proposal.affiliate_terms = None
            if proposal.pricing_model in (PricingModel.COMMISSION, PricingModel.HYBRID):
                aff_platform_raw = form.get("aff_deal_platform", "tiktok_shop")
                commission_pct = float(form.get("commission_pct", 10) or 10) / 100
                base_fee = float(form.get("aff_base_fee", 0) or 0)
                duration_days = int(form.get("aff_duration_days", 30) or 30)
                min_campaign = float(form.get("aff_min_campaign", 0) or 0)
                categories_chosen = form.getlist("aff_deal_categories")

                aff_stats = profile.get_affiliate_stats(AffiliatePlatform(aff_platform_raw)) if aff_platform_raw else None
                projected_gmv = min_campaign if min_campaign > 0 else (aff_stats.avg_monthly_gmv if aff_stats else 0)
                projected_earning = projected_gmv * commission_pct + base_fee

                proposal.affiliate_terms = AffiliateTerms(
                    commission_pct=commission_pct,
                    base_fee=base_fee,
                    min_campaign_value=min_campaign,
                    categories=categories_chosen,
                    duration_days=duration_days,
                    projected_gmv=projected_gmv,
                    projected_earning=projected_earning,
                )
                if proposal.pricing_model == PricingModel.COMMISSION:
                    proposal.total_price = projected_earning
                else:
                    proposal.total_price += base_fee

            db.update_proposal(proposal)
            return redirect(url_for("proposal_detail", proposal_id=proposal_id))

        from ratecard.core.models import TierName
        packages_preview = build_all_packages(profile, defaults)

        affiliate_suggestions = {}
        for aff_stats in profile.affiliate_stats:
            if aff_stats.enabled and aff_stats.avg_monthly_gmv > 0:
                affiliate_suggestions[aff_stats.platform.value] = calculate_affiliate_rate(
                    aff_stats.platform.value,
                    aff_stats.avg_monthly_gmv,
                    aff_stats.avg_conversion_rate,
                    aff_stats.avg_commission_pct,
                )

        return render_template(
            "proposal_form.html",
            profile=profile,
            proposal=proposal,
            platforms=list(Platform),
            affiliate_platforms=list(AffiliatePlatform),
            affiliate_suggestions=affiliate_suggestions,
            tiers=list(TierName),
            packages_preview=packages_preview,
            pricing_models=list(PricingModel),
            payment_schemes=list(PaymentScheme),
            addon_types=list(AddOnType),
            active="proposals",
            is_edit=True,
        )

    @app.route("/proposal/<int:proposal_id>/duplicate", methods=["POST"])
    def proposal_duplicate(proposal_id):
        original = db.get_proposal(proposal_id)
        if not original:
            abort(404)
        copy = Proposal(
            client_name=original.client_name,
            client_company=original.client_company,
            client_email=original.client_email,
            campaign_name=f"{original.campaign_name} (copy)",
            packages=original.packages,
            total_price=original.total_price,
            discount_pct=original.discount_pct,
            status=ProposalStatus.DRAFT,
            pricing_model=original.pricing_model,
            payment_scheme=original.payment_scheme,
            affiliate_terms=original.affiliate_terms,
            notes=original.notes,
        )
        new_id = db.create_proposal(copy)
        return redirect(url_for("proposal_detail", proposal_id=new_id))

    @app.route("/proposal/<int:proposal_id>/status/<status>", methods=["POST"])
    def proposal_status(proposal_id, status):
        proposal = db.get_proposal(proposal_id)
        if not proposal:
            abort(404)
        try:
            proposal.status = ProposalStatus(status)
        except ValueError:
            abort(400)
        db.update_proposal(proposal)
        return redirect(url_for("proposal_detail", proposal_id=proposal_id))

    # ── Custom Add-ons ────────────────────────────────────
    @app.route("/addon/create", methods=["POST"])
    def addon_create():
        form = request.form
        addon = CustomAddOn(
            name=form.get("name", "").strip(),
            description=form.get("description", "").strip(),
            price_type=form.get("price_type", "percentage"),
            price_value=float(form.get("price_value", 0) or 0),
            category=form.get("category", "influencer"),
        )
        db.create_custom_addon(addon)
        redirect_url = form.get("redirect", "/ratecard")
        return redirect(redirect_url)

    @app.route("/addon/delete/<int:addon_id>", methods=["POST"])
    def addon_delete(addon_id):
        db.delete_custom_addon(addon_id)
        redirect_url = request.form.get("redirect", "/ratecard")
        return redirect(redirect_url)

    # ── XLSX Export ───────────────────────────────────────
    @app.route("/export/xlsx")
    def export_xlsx():
        from ratecard.outputs.xlsx_exporter import export_xlsx as do_export
        profile = db.get_profile()
        if not profile:
            abort(404)
        defaults = _defaults()
        packages = build_all_packages(profile, defaults)
        proposals = db.list_proposals(limit=500)
        out_path = config.DATA_DIR / "rate_card.xlsx"
        do_export(profile, packages, proposals, out_path)
        return send_file(out_path, as_attachment=True, download_name="rate_card.xlsx")

    return app
