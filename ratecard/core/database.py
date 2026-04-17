import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ratecard.core.models import (
    AddOnType,
    AffiliatePlatform,
    AffiliateStats,
    AffiliateTerms,
    ContentType,
    CreatorProfile,
    CustomAddOn,
    Package,
    PackageAddOn,
    PackageItem,
    PaymentScheme,
    Platform,
    PlatformStats,
    PricingModel,
    Proposal,
    ProposalStatus,
    TierName,
)

_DB_PATH: Optional[Path] = None


def init_db(db_path: Path):
    """Initialize database and create tables. Must be called before any other db function."""
    global _DB_PATH
    _DB_PATH = db_path
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS creator_profile (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                niche TEXT DEFAULT '',
                location TEXT DEFAULT '',
                contact_email TEXT DEFAULT '',
                logo_path TEXT,
                brand_color_hex TEXT DEFAULT '#E91E8C',
                currency TEXT DEFAULT 'IDR',
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS platform_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER REFERENCES creator_profile(id),
                platform TEXT NOT NULL,
                followers INTEGER DEFAULT 0,
                avg_views INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                avg_monthly_impressions INTEGER DEFAULT 0,
                last_updated TEXT,
                UNIQUE(profile_id, platform)
            );

            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT DEFAULT '',
                client_company TEXT DEFAULT '',
                client_email TEXT DEFAULT '',
                campaign_name TEXT DEFAULT '',
                packages_json TEXT DEFAULT '[]',
                total_price REAL DEFAULT 0.0,
                discount_pct REAL DEFAULT 0.0,
                status TEXT DEFAULT 'draft',
                pricing_model TEXT DEFAULT 'flat',
                affiliate_terms_json TEXT,
                created_at TEXT,
                sent_at TEXT,
                pdf_path TEXT,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS affiliate_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER REFERENCES creator_profile(id),
                platform TEXT NOT NULL,
                avg_monthly_gmv INTEGER DEFAULT 0,
                avg_conversion_rate REAL DEFAULT 0.0,
                avg_commission_pct REAL DEFAULT 0.0,
                enabled INTEGER DEFAULT 1,
                last_updated TEXT,
                UNIQUE(profile_id, platform)
            );

            CREATE TABLE IF NOT EXISTS custom_addons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                description TEXT DEFAULT '',
                price_type TEXT DEFAULT 'percentage',
                price_value REAL DEFAULT 0.0,
                category TEXT DEFAULT 'influencer',
                enabled INTEGER DEFAULT 1,
                created_at TEXT
            );
        """)

        # ── Migrations for existing databases ──
        _migrate_add_column(conn, "creator_profile", "affiliate_categories_json", "TEXT DEFAULT '[]'")
        _migrate_add_column(conn, "proposals", "pricing_model", "TEXT DEFAULT 'flat'")
        _migrate_add_column(conn, "proposals", "affiliate_terms_json", "TEXT")
        _migrate_add_column(conn, "proposals", "payment_scheme", "TEXT DEFAULT 'dp_50'")


def _migrate_add_column(conn, table: str, column: str, definition: str):
    """Add a column to a table if it doesn't already exist (SQLite-safe)."""
    existing = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


@contextmanager
def _connect():
    if _DB_PATH is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ──────────────────────────────
# Creator Profile
# ──────────────────────────────

def get_profile() -> Optional[CreatorProfile]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM creator_profile WHERE id = 1").fetchone()
        if row is None:
            return None

        stats_rows = conn.execute(
            "SELECT * FROM platform_stats WHERE profile_id = 1"
        ).fetchall()

        aff_rows = conn.execute(
            "SELECT * FROM affiliate_stats WHERE profile_id = 1"
        ).fetchall()

    stats = [
        PlatformStats(
            platform=Platform(r["platform"]),
            followers=r["followers"],
            avg_views=r["avg_views"],
            engagement_rate=r["engagement_rate"],
            avg_monthly_impressions=r["avg_monthly_impressions"],
            last_updated=datetime.fromisoformat(r["last_updated"]) if r["last_updated"] else datetime.now(),
        )
        for r in stats_rows
    ]

    aff_stats = [
        AffiliateStats(
            platform=AffiliatePlatform(r["platform"]),
            avg_monthly_gmv=r["avg_monthly_gmv"],
            avg_conversion_rate=r["avg_conversion_rate"],
            avg_commission_pct=r["avg_commission_pct"],
            enabled=bool(r["enabled"]),
            last_updated=datetime.fromisoformat(r["last_updated"]) if r["last_updated"] else datetime.now(),
        )
        for r in aff_rows
    ]

    raw_categories = row["affiliate_categories_json"] if "affiliate_categories_json" in row.keys() else None
    try:
        categories = json.loads(raw_categories) if raw_categories else []
    except (TypeError, json.JSONDecodeError):
        categories = []

    return CreatorProfile(
        id=row["id"],
        name=row["name"],
        niche=row["niche"] or "",
        location=row["location"] or "",
        contact_email=row["contact_email"] or "",
        logo_path=row["logo_path"],
        brand_color_hex=row["brand_color_hex"] or "#E91E8C",
        currency=row["currency"] or "IDR",
        platform_stats=stats,
        affiliate_stats=aff_stats,
        affiliate_categories=categories,
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
    )


def save_profile(profile: CreatorProfile):
    now = datetime.now().isoformat()
    categories_json = json.dumps(profile.affiliate_categories, ensure_ascii=False)
    with _connect() as conn:
        existing = conn.execute("SELECT id FROM creator_profile WHERE id = 1").fetchone()
        if existing:
            conn.execute("""
                UPDATE creator_profile SET
                    name=?, niche=?, location=?, contact_email=?,
                    logo_path=?, brand_color_hex=?, currency=?,
                    affiliate_categories_json=?, updated_at=?
                WHERE id = 1
            """, (
                profile.name, profile.niche, profile.location, profile.contact_email,
                profile.logo_path, profile.brand_color_hex, profile.currency,
                categories_json, now,
            ))
        else:
            conn.execute("""
                INSERT INTO creator_profile (id, name, niche, location, contact_email,
                    logo_path, brand_color_hex, currency, affiliate_categories_json,
                    created_at, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.name, profile.niche, profile.location, profile.contact_email,
                profile.logo_path, profile.brand_color_hex, profile.currency,
                categories_json, now, now,
            ))


def upsert_platform_stats(stats: PlatformStats, profile_id: int = 1):
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.execute("""
            INSERT INTO platform_stats
                (profile_id, platform, followers, avg_views, engagement_rate,
                 avg_monthly_impressions, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id, platform) DO UPDATE SET
                followers=excluded.followers,
                avg_views=excluded.avg_views,
                engagement_rate=excluded.engagement_rate,
                avg_monthly_impressions=excluded.avg_monthly_impressions,
                last_updated=excluded.last_updated
        """, (
            profile_id, stats.platform.value, stats.followers, stats.avg_views,
            stats.engagement_rate, stats.avg_monthly_impressions, now,
        ))


def upsert_affiliate_stats(stats: AffiliateStats, profile_id: int = 1):
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.execute("""
            INSERT INTO affiliate_stats
                (profile_id, platform, avg_monthly_gmv, avg_conversion_rate,
                 avg_commission_pct, enabled, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id, platform) DO UPDATE SET
                avg_monthly_gmv=excluded.avg_monthly_gmv,
                avg_conversion_rate=excluded.avg_conversion_rate,
                avg_commission_pct=excluded.avg_commission_pct,
                enabled=excluded.enabled,
                last_updated=excluded.last_updated
        """, (
            profile_id, stats.platform.value, stats.avg_monthly_gmv,
            stats.avg_conversion_rate, stats.avg_commission_pct,
            1 if stats.enabled else 0, now,
        ))


# ──────────────────────────────
# Proposals
# ──────────────────────────────

def _packages_to_json(packages: List[Package]) -> str:
    data = []
    for pkg in packages:
        items_data = [
            {
                "content_type": item.content_type.value,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "revision_rounds": item.revision_rounds,
                "usage_rights_days": item.usage_rights_days,
                "exclusivity_days": item.exclusivity_days,
            }
            for item in pkg.items
        ]
        addons_data = [
            {
                "addon_type": addon.addon_type.value,
                "price": addon.price,
                "quantity": addon.quantity,
                "included_in_tier": addon.included_in_tier,
            }
            for addon in pkg.addons
        ]
        data.append({
            "tier": pkg.tier.value,
            "name": pkg.name,
            "items": items_data,
            "addons": addons_data,
            "base_price": pkg.base_price,
            "bundle_discount_pct": pkg.bundle_discount_pct,
            "client_discount_pct": pkg.client_discount_pct,
            "final_price": pkg.final_price,
            "valid_days": pkg.valid_days,
            "notes": pkg.notes,
        })
    return json.dumps(data, ensure_ascii=False)


def _json_to_packages(raw: str) -> List[Package]:
    data = json.loads(raw)
    packages = []
    for d in data:
        items = [
            PackageItem(
                content_type=ContentType(i["content_type"]),
                quantity=i["quantity"],
                unit_price=i["unit_price"],
                revision_rounds=i["revision_rounds"],
                usage_rights_days=i["usage_rights_days"],
                exclusivity_days=i["exclusivity_days"],
            )
            for i in d.get("items", [])
        ]
        addons = []
        for a in d.get("addons", []):
            try:
                addons.append(PackageAddOn(
                    addon_type=AddOnType(a["addon_type"]),
                    price=a.get("price", 0),
                    quantity=a.get("quantity", 1),
                    included_in_tier=a.get("included_in_tier", False),
                ))
            except (ValueError, KeyError):
                pass
        packages.append(Package(
            tier=TierName(d["tier"]),
            name=d["name"],
            items=items,
            addons=addons,
            base_price=d["base_price"],
            bundle_discount_pct=d["bundle_discount_pct"],
            client_discount_pct=d["client_discount_pct"],
            final_price=d["final_price"],
            valid_days=d["valid_days"],
            notes=d.get("notes", ""),
        ))
    return packages


def _affiliate_terms_to_json(terms: Optional[AffiliateTerms]) -> Optional[str]:
    if terms is None:
        return None
    return json.dumps({
        "commission_pct": terms.commission_pct,
        "base_fee": terms.base_fee,
        "min_campaign_value": terms.min_campaign_value,
        "categories": terms.categories,
        "exclusivity_days": terms.exclusivity_days,
        "duration_days": terms.duration_days,
        "projected_gmv": terms.projected_gmv,
        "projected_earning": terms.projected_earning,
    }, ensure_ascii=False)


def _json_to_affiliate_terms(raw: Optional[str]) -> Optional[AffiliateTerms]:
    if not raw:
        return None
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return AffiliateTerms(
        commission_pct=d.get("commission_pct", 0.08),
        base_fee=d.get("base_fee", 0.0),
        min_campaign_value=d.get("min_campaign_value", 0.0),
        categories=d.get("categories", []),
        exclusivity_days=d.get("exclusivity_days", 0),
        duration_days=d.get("duration_days", 30),
        projected_gmv=d.get("projected_gmv", 0.0),
        projected_earning=d.get("projected_earning", 0.0),
    )


def create_proposal(proposal: Proposal) -> int:
    now = datetime.now().isoformat()
    with _connect() as conn:
        cursor = conn.execute("""
            INSERT INTO proposals
                (client_name, client_company, client_email, campaign_name,
                 packages_json, total_price, discount_pct, status,
                 pricing_model, affiliate_terms_json, payment_scheme,
                 created_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proposal.client_name, proposal.client_company, proposal.client_email,
            proposal.campaign_name, _packages_to_json(proposal.packages),
            proposal.total_price, proposal.discount_pct,
            proposal.status.value, proposal.pricing_model.value,
            _affiliate_terms_to_json(proposal.affiliate_terms),
            proposal.payment_scheme.value,
            now, proposal.notes,
        ))
        return cursor.lastrowid


def update_proposal(proposal: Proposal):
    with _connect() as conn:
        conn.execute("""
            UPDATE proposals SET
                client_name=?, client_company=?, client_email=?, campaign_name=?,
                packages_json=?, total_price=?, discount_pct=?, status=?,
                pricing_model=?, affiliate_terms_json=?, payment_scheme=?,
                sent_at=?, pdf_path=?, notes=?
            WHERE id=?
        """, (
            proposal.client_name, proposal.client_company, proposal.client_email,
            proposal.campaign_name, _packages_to_json(proposal.packages),
            proposal.total_price, proposal.discount_pct, proposal.status.value,
            proposal.pricing_model.value,
            _affiliate_terms_to_json(proposal.affiliate_terms),
            proposal.payment_scheme.value,
            proposal.sent_at.isoformat() if proposal.sent_at else None,
            proposal.pdf_path, proposal.notes, proposal.id,
        ))


def get_proposal(proposal_id: int) -> Optional[Proposal]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
    if row is None:
        return None
    return _row_to_proposal(row)


def list_proposals(limit: int = 20, status_filter: Optional[str] = None) -> List[Proposal]:
    with _connect() as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM proposals WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM proposals ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [_row_to_proposal(r) for r in rows]


# ──────────────────────────────
# Custom Add-ons
# ──────────────────────────────

def list_custom_addons(category: Optional[str] = None, enabled_only: bool = False) -> List[CustomAddOn]:
    with _connect() as conn:
        sql = "SELECT * FROM custom_addons"
        params = []
        clauses = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if enabled_only:
            clauses.append("enabled = 1")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()
    return [
        CustomAddOn(
            id=r["id"], name=r["name"], description=r["description"] or "",
            price_type=r["price_type"] or "percentage",
            price_value=r["price_value"] or 0.0,
            category=r["category"] or "influencer",
            enabled=bool(r["enabled"]),
            created_at=datetime.fromisoformat(r["created_at"]) if r["created_at"] else datetime.now(),
        )
        for r in rows
    ]


def create_custom_addon(addon: CustomAddOn) -> int:
    now = datetime.now().isoformat()
    with _connect() as conn:
        cursor = conn.execute("""
            INSERT INTO custom_addons (name, description, price_type, price_value, category, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (addon.name, addon.description, addon.price_type, addon.price_value,
              addon.category, 1 if addon.enabled else 0, now))
        return cursor.lastrowid


def update_custom_addon(addon: CustomAddOn):
    with _connect() as conn:
        conn.execute("""
            UPDATE custom_addons SET name=?, description=?, price_type=?, price_value=?, category=?, enabled=?
            WHERE id=?
        """, (addon.name, addon.description, addon.price_type, addon.price_value,
              addon.category, 1 if addon.enabled else 0, addon.id))


def delete_custom_addon(addon_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM custom_addons WHERE id=?", (addon_id,))


def _row_to_proposal(row) -> Proposal:
    cols = row.keys()
    pm_raw = row["pricing_model"] if "pricing_model" in cols else "flat"
    try:
        pricing_model = PricingModel(pm_raw or "flat")
    except ValueError:
        pricing_model = PricingModel.FLAT
    aff_raw = row["affiliate_terms_json"] if "affiliate_terms_json" in cols else None
    ps_raw = row["payment_scheme"] if "payment_scheme" in cols else "dp_50"
    try:
        payment_scheme = PaymentScheme(ps_raw or "dp_50")
    except ValueError:
        payment_scheme = PaymentScheme.DP_50
    return Proposal(
        id=row["id"],
        client_name=row["client_name"],
        client_company=row["client_company"],
        client_email=row["client_email"],
        campaign_name=row["campaign_name"],
        packages=_json_to_packages(row["packages_json"] or "[]"),
        total_price=row["total_price"],
        discount_pct=row["discount_pct"],
        status=ProposalStatus(row["status"]),
        pricing_model=pricing_model,
        payment_scheme=payment_scheme,
        affiliate_terms=_json_to_affiliate_terms(aff_raw),
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
        pdf_path=row["pdf_path"],
        notes=row["notes"] or "",
    )
