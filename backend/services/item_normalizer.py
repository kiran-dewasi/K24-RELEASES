"""
Item Normalizer & Mapper
========================
Resolves raw OCR item names (e.g. "JD Jeera 1kg", "MDH Kaur Masala 50g")
to existing Tally catalog items, or decides to create new ones.

Usage:
    from backend.services.item_normalizer import normalize_and_map_item, CompanySettings

    result = normalize_and_map_item(
        raw_item_name="JD Jeera 1kg",
        quantity=1.0,
        unit="kg",
        existing_items=db.query(StockItem).all(),
        company_settings=CompanySettings(
            allow_brand_level_items=False,
            strict_single_item_per_commodity=True,
        )
    )

Dependencies:
    - rapidfuzz  (pip install rapidfuzz)   <- preferred, fast C ext
    - Falls back to difflib (stdlib) if rapidfuzz not installed
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Fuzzy matching: prefer rapidfuzz, fall back to difflib
# ──────────────────────────────────────────────
try:
    from rapidfuzz import fuzz as _fuzz
    from rapidfuzz import process as _rfprocess

    def _token_set_ratio(a: str, b: str) -> float:
        return _fuzz.token_set_ratio(a, b) / 100.0

    def _partial_ratio(a: str, b: str) -> float:
        return _fuzz.partial_ratio(a, b) / 100.0

    def _ratio(a: str, b: str) -> float:
        return _fuzz.ratio(a, b) / 100.0

    _HAS_RAPIDFUZZ = True

except ImportError:  # pragma: no cover
    import difflib

    def _token_set_ratio(a: str, b: str) -> float:
        """Approximate token-set ratio using difflib."""
        ta = set(a.lower().split())
        tb = set(b.lower().split())
        intersection = " ".join(sorted(ta & tb))
        # Compare intersection + A, intersection + B, and A+B
        sa = " ".join(sorted(ta))
        sb = " ".join(sorted(tb))
        scores = [
            difflib.SequenceMatcher(None, intersection, sa).ratio(),
            difflib.SequenceMatcher(None, intersection, sb).ratio(),
            difflib.SequenceMatcher(None, sa, sb).ratio(),
        ]
        return max(scores)

    def _partial_ratio(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a, b).ratio()

    def _ratio(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a, b).ratio()

    _HAS_RAPIDFUZZ = False
    logger.warning("rapidfuzz not found; falling back to difflib. Install with: pip install rapidfuzz")


# ──────────────────────────────────────────────
# Domain knowledge dictionaries
# ──────────────────────────────────────────────

# Well-known Indian grocery/commodity brand names to strip from item names.
# Add more as needed.
_KNOWN_BRANDS: set[str] = {
    # Masalas / Spices
    "mdh", "everest", "catch", "sunrise", "badshah", "rajah",
    # Dal / Grains
    "daawat", "india gate", "fortune", "kohinoor", "lal qilla",
    # Salt / Sugar
    "tata", "patanjali", "annapurna",
    # Oil
    "saffola", "dhara", "sundrop", "gemini", "refined",
    # Atta / Wheat
    "aashirvaad", "pillsbury",
    # Loose / Generic qualifiers that should be stripped
    "loose", "fresh", "raw", "organic", "local",
    # Regional brand/dialect tokens
    "jd", "jd's", "shree", "shri", "sri",
    # Common packs
    "premium", "special", "super", "gold",
}

# Commodity base words — these are the real item names, never strip these.
_COMMODITY_WORDS: set[str] = {
    "jeera", "cumin", "dhaniya", "coriander", "haldi", "turmeric",
    "mirch", "chilli", "lal", "kali", "garam", "masala", "namak",
    "salt", "dal", "chana", "moong", "arhar", "tur", "urad", "rajma",
    "atta", "wheat", "maida", "suji", "rava", "besan", "rice", "chawal",
    "basmati", "poha", "murmura", "sugar","shakkar", "cheeni", "jaggery",
    "gud", "oil", "tel", "sarso", "mustard", "sunflower", "groundnut",
    "soybean", "coconut", "ghee", "butter", "paneer", "milk", "doodh",
    "tea", "chai", "coffee",
    # Vegetables
    "aloo", "potato", "onion", "pyaz", "tamater", "tomato", "adrak",
    "ginger", "lahsun", "garlic", "palak", "spinach", "gobhi",
    # Dry fruits
    "kaju", "cashew", "badam", "almond", "kishmish", "raisin",
    # Spice seeds
    "ajwain", "methi", "fenugreek", "saunf", "fennel", "kesar",
    "saffron", "clove", "laung", "elaichi", "cardamom", "dalchini",
    "cinnamon", "tejpatta", "bayleaf",
}

# Unit synonym groups: items in the same group are compatible with each other.
# We allow auto-mapping if the OCR unit and item's unit are in the same group.
_UNIT_GROUPS: List[set[str]] = [
    # Weight
    {"kg", "kgs", "kilogram", "kilograms", "g", "gm", "gms", "gram", "grams",
     "mg", "milligram", "quintal", "qtl"},
    # Volume
    {"l", "ltr", "liter", "litre", "liters", "litres", "ml", "millilitre",
     "milliliter", "kl"},
    # Count
    {"pcs", "pc", "nos", "no", "piece", "pieces", "unit", "units",
     "box", "boxes", "pack", "pkt", "packet", "packets", "bag", "bags",
     "set", "sets", "doz", "dozen", "carton"},
    # Length
    {"m", "mtr", "meter", "metre", "cm", "mm", "ft", "feet", "inch"},
]

# Size / pack patterns to strip from item names
_SIZE_PATTERN = re.compile(
    r"""
    \b
    (?:
        \d+(?:\.\d+)?   # number (with optional decimal)
        \s*             # optional space
        (?:kg|kgs|gm|grams?|g|mg|ltr?|liters?|litres?|ml|pcs|nos|pkt|pack|box|bags?|nos?|mtr?|cm|ft|m)
    |
        \d+(?:\.\d+)?   # bare number sometimes represents size
        \s*(?:x\s*\d+)? # e.g. "5x10"
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Punctuation to strip (keep hyphens inside words)
_PUNCT_PATTERN = re.compile(r"[^\w\s\-]")


# ──────────────────────────────────────────────
# Data Transfer Types
# ──────────────────────────────────────────────

@dataclass
class ItemCatalogEntry:
    """Lightweight view of a StockItem for normalizer use."""
    id: Any                         # DB primary key (int or str)
    name: str
    units: str
    normalized_name: str = ""       # Pre-computed; filled by normalizer if missing
    hsn_code: Optional[str] = None
    stock_group: Optional[str] = None
    is_canonical: bool = False      # Optional flag for "master" item

    def __post_init__(self):
        if not self.normalized_name:
            self.normalized_name = _normalize_text(self.name)


@dataclass
class CompanySettings:
    """Control flags that govern the normalizer's behaviour."""
    allow_brand_level_items: bool = False
    strict_single_item_per_commodity: bool = True
    high_confidence_threshold: float = 0.85   # >= this → USE_EXISTING
    low_confidence_threshold: float = 0.55    # <  this → definitely no match
    max_suggestions: int = 3


@dataclass
class SimilarItemSuggestion:
    """A single candidate returned in the suggestions list."""
    item_id: Any
    name: str
    score: float
    units: str
    match_type: str   # "base_name" | "full_name" | "alias"


@dataclass
class NormalizedMappingResult:
    """Full decision result from normalize_and_map_item()."""
    action: str                                # USE_EXISTING | CREATE_NEW | NEEDS_REVIEW
    chosen_item_id: Optional[Any]              # existing catalog ID, or None
    normalized_base_name: str                  # e.g. "jeera"
    brand_candidate: Optional[str]             # e.g. "mdh"
    size_info: Optional[str]                   # e.g. "500g"
    unit: str                                  # cleaned unit
    confidence: float                          # 0.0 – 1.0
    reasoning: str
    suggestions: List[SimilarItemSuggestion] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = _PUNCT_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_unit(raw_unit: str) -> str:
    """Canonicalize unit string: 'KGS' → 'kg', 'Pcs' → 'pcs'."""
    return raw_unit.lower().strip().rstrip("s") if raw_unit else ""


def _units_compatible(a: str, b: str) -> bool:
    """Return True if two units belong to the same unit group."""
    na = _normalize_unit(a)
    nb = _normalize_unit(b)
    if na == nb:
        return True
    for group in _UNIT_GROUPS:
        norms = {g.rstrip("s") for g in group}
        if na in norms and nb in norms:
            return True
    return False


def _extract_size_info(tokens: List[str]) -> Tuple[List[str], Optional[str]]:
    """
    Remove size/pack tokens from token list.
    Returns (cleaned_tokens, size_string_or_None).
    """
    size_parts: List[str] = []
    remaining: List[str] = []
    full_text = " ".join(tokens)
    sizes = _SIZE_PATTERN.findall(full_text)
    if sizes:
        # Remove matches from tokens
        cleaned = _SIZE_PATTERN.sub("", full_text).strip()
        remaining = [t for t in cleaned.split() if t]
        return remaining, " ".join(sizes).strip()
    return tokens, None


def _split_brand_and_base(tokens: List[str]) -> Tuple[List[str], Optional[str]]:
    """
    Separate known brand tokens from commodity tokens.
    Returns (commodity_tokens, brand_candidate_or_None).
    """
    brand_tokens: List[str] = []
    commodity_tokens: List[str] = []

    for tok in tokens:
        if tok in _KNOWN_BRANDS and tok not in _COMMODITY_WORDS:
            brand_tokens.append(tok)
        else:
            commodity_tokens.append(tok)

    # Heuristic: if the first token doesn't appear in commodities, flag it as brand
    # even if not in our known list (handles unknown brands like "xyz jeera")
    if not brand_tokens and len(tokens) >= 2:
        head = tokens[0]
        rest_are_commodities = any(t in _COMMODITY_WORDS for t in tokens[1:])
        if head not in _COMMODITY_WORDS and rest_are_commodities:
            brand_tokens.append(head)
            commodity_tokens = tokens[1:]

    brand_str = " ".join(brand_tokens) if brand_tokens else None
    return commodity_tokens, brand_str


def _compute_similarity(query: str, candidate: str) -> float:
    """
    Combined similarity: max of token_set_ratio and partial_ratio.
    Gives a final score in [0, 1].
    """
    tsr = _token_set_ratio(query, candidate)
    pr  = _partial_ratio(query, candidate)
    r   = _ratio(query, candidate)
    return max(tsr, pr * 0.9, r * 0.85)


def find_similar_items(
    normalized_query: str,
    existing_items: List[ItemCatalogEntry],
    top_k: int = 5,
) -> List[Tuple[ItemCatalogEntry, float, str]]:
    """
    Find the top-k most similar catalog items to the query string.

    Returns:
        List of (ItemCatalogEntry, score, match_type) sorted by score desc.
    """
    results: List[Tuple[float, ItemCatalogEntry, str]] = []

    for item in existing_items:
        # 1. Base normalized name
        base_score = _compute_similarity(normalized_query, item.normalized_name)
        # 2. Exact subword check
        if normalized_query in item.normalized_name:
            base_score = max(base_score, 0.92)
        if item.normalized_name in normalized_query and len(item.normalized_name) > 3:
            base_score = max(base_score, 0.90)

        results.append((base_score, item, "base_name"))

    results.sort(key=lambda x: x[0], reverse=True)
    return [(item, score, mtype) for score, item, mtype in results[:top_k]]


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def normalize_and_map_item(
    raw_item_name: str,
    quantity: float,
    unit: str,
    existing_items: List[ItemCatalogEntry],
    company_settings: CompanySettings,
) -> NormalizedMappingResult:
    """
    Normalize a raw OCR item name and decide which catalog item to use.

    Args:
        raw_item_name:     The raw string from OCR, e.g. "JD Jeera 50kg"
        quantity:          Numeric quantity (used only for logging/output)
        unit:              Raw unit string, e.g. "kg", "pcs"
        existing_items:    Full catalog as List[ItemCatalogEntry]
        company_settings:  Behaviour configuration

    Returns:
        NormalizedMappingResult with action, chosen_item_id, and rich metadata.
    """

    # ── STEP 1: Pre-normalization ──────────────────────────────────────────

    normalized_full = _normalize_text(raw_item_name)
    tokens = normalized_full.split()

    # Extract size/pack info ("500g", "1kg", "2 ltr")
    tokens, size_info = _extract_size_info(tokens)

    # Clean unit
    clean_unit = _normalize_unit(unit) if unit else ""
    # If unit was embedded in size_info only (e.g. "1kg" → already extracted), keep it
    if not clean_unit and size_info:
        unit_in_size = re.search(
            r"(kg|gm|g|ltr?|liters?|ml|pcs|nos|pkt|pack|mtr?)", size_info, re.I
        )
        if unit_in_size:
            clean_unit = _normalize_unit(unit_in_size.group(1))

    # Separate brand from commodity tokens
    commodity_tokens, brand_candidate = _split_brand_and_base(tokens)

    # Derive base name
    normalized_base_name = " ".join(commodity_tokens).strip() or normalized_full
    if not normalized_base_name:
        normalized_base_name = normalized_full

    logger.debug(
        "[ItemNorm] raw=%r | full=%r | base=%r | brand=%r | size=%r | unit=%r",
        raw_item_name, normalized_full, normalized_base_name,
        brand_candidate, size_info, clean_unit,
    )

    # ── STEP 2: Find candidates ────────────────────────────────────────────

    candidates = find_similar_items(
        normalized_base_name,
        existing_items,
        top_k=company_settings.max_suggestions + 2,
    )

    # Also try full normalized name if base gave poor results
    if not candidates or candidates[0][1] < company_settings.low_confidence_threshold:
        full_candidates = find_similar_items(
            normalized_full,
            existing_items,
            top_k=company_settings.max_suggestions + 2,
        )
        # Merge: prefer base candidates, augment with unique full-name hits
        seen_ids = {c[0].id for c in candidates}
        for fc in full_candidates:
            if fc[0].id not in seen_ids:
                candidates.append(fc)
                seen_ids.add(fc[0].id)
        # Re-sort
        candidates.sort(key=lambda x: x[1], reverse=True)

    # ── STEP 3: Decision logic ─────────────────────────────────────────────

    HI = company_settings.high_confidence_threshold
    LO = company_settings.low_confidence_threshold

    # Build suggestions list for output
    top_suggestions: List[SimilarItemSuggestion] = [
        SimilarItemSuggestion(
            item_id=item.id,
            name=item.name,
            score=round(score, 4),
            units=item.units,
            match_type=mtype,
        )
        for item, score, mtype in candidates[: company_settings.max_suggestions]
    ]

    if not candidates:
        # ── No candidates at all ──
        return _decision_no_match(
            normalized_base_name, brand_candidate, size_info,
            clean_unit, company_settings, top_suggestions,
        )

    best_item, best_score, best_mtype = candidates[0]

    # ── High confidence match ──
    if best_score >= HI:
        if _units_compatible(clean_unit, best_item.units):
            return NormalizedMappingResult(
                action="USE_EXISTING",
                chosen_item_id=best_item.id,
                normalized_base_name=normalized_base_name,
                brand_candidate=brand_candidate,
                size_info=size_info,
                unit=clean_unit or best_item.units,
                confidence=round(best_score, 4),
                reasoning=(
                    f"High confidence match ({best_score:.0%}) to existing item "
                    f"'{best_item.name}' via {best_mtype}. "
                    + (f"Brand '{brand_candidate}' noted in narration." if brand_candidate else "")
                ),
                suggestions=top_suggestions,
            )
        else:
            # Good name match but incompatible units → review
            return NormalizedMappingResult(
                action="NEEDS_REVIEW",
                chosen_item_id=best_item.id,   # suggest, not force
                normalized_base_name=normalized_base_name,
                brand_candidate=brand_candidate,
                size_info=size_info,
                unit=clean_unit,
                confidence=round(best_score * 0.7, 4),   # penalise
                reasoning=(
                    f"Name match ({best_score:.0%}) to '{best_item.name}', but unit "
                    f"'{clean_unit}' is incompatible with catalog unit '{best_item.units}'. "
                    "Manual review required."
                ),
                suggestions=top_suggestions,
            )

    # ── Medium confidence zone: multiple close candidates? ──
    close_candidates = [c for c in candidates if c[1] >= LO]

    if len(close_candidates) >= 2 and not company_settings.strict_single_item_per_commodity:
        # Ambiguous → ask user
        return NormalizedMappingResult(
            action="NEEDS_REVIEW",
            chosen_item_id=None,
            normalized_base_name=normalized_base_name,
            brand_candidate=brand_candidate,
            size_info=size_info,
            unit=clean_unit,
            confidence=round(best_score, 4),
            reasoning=(
                f"Multiple candidates with similar scores (top: {best_score:.0%}). "
                "User should confirm which item to use."
            ),
            suggestions=top_suggestions,
        )

    if len(close_candidates) >= 1 and company_settings.strict_single_item_per_commodity:
        # Strict mode: auto-pick best even in medium zone
        best_medium, score_medium, mtype_medium = close_candidates[0]
        unit_ok = _units_compatible(clean_unit, best_medium.units)
        if unit_ok:
            return NormalizedMappingResult(
                action="USE_EXISTING",
                chosen_item_id=best_medium.id,
                normalized_base_name=normalized_base_name,
                brand_candidate=brand_candidate,
                size_info=size_info,
                unit=clean_unit or best_medium.units,
                confidence=round(score_medium, 4),
                reasoning=(
                    f"Strict mode: best match ({score_medium:.0%}) to '{best_medium.name}' "
                    f"via {mtype_medium}. Unit compatible. Auto-mapped."
                ),
                suggestions=top_suggestions,
            )

    # ── No good match ──
    return _decision_no_match(
        normalized_base_name, brand_candidate, size_info,
        clean_unit, company_settings, top_suggestions,
        best_score_hint=best_score if candidates else 0.0,
    )


def _decision_no_match(
    normalized_base_name: str,
    brand_candidate: Optional[str],
    size_info: Optional[str],
    unit: str,
    settings: CompanySettings,
    suggestions: List[SimilarItemSuggestion],
    best_score_hint: float = 0.0,
) -> NormalizedMappingResult:
    """Helper that decides CREATE_NEW vs NEEDS_REVIEW when no catalog match found."""
    if settings.allow_brand_level_items:
        return NormalizedMappingResult(
            action="CREATE_NEW",
            chosen_item_id=None,
            normalized_base_name=normalized_base_name,
            brand_candidate=brand_candidate,
            size_info=size_info,
            unit=unit,
            confidence=0.0,
            reasoning=(
                "Brand-level item creation allowed; no close base item match found "
                f"(best candidate score: {best_score_hint:.0%})."
            ),
            suggestions=suggestions,
        )
    else:
        return NormalizedMappingResult(
            action="NEEDS_REVIEW",
            chosen_item_id=None,
            normalized_base_name=normalized_base_name,
            brand_candidate=brand_candidate,
            size_info=size_info,
            unit=unit,
            confidence=0.0,
            reasoning=(
                f"No close base item found (best score: {best_score_hint:.0%}). "
                "Brand-level items are not allowed — manual review required."
            ),
            suggestions=suggestions,
        )


# ──────────────────────────────────────────────
# Convenience: build ItemCatalogEntry list from DB
# ──────────────────────────────────────────────

def build_catalog_from_db(db_session) -> List[ItemCatalogEntry]:
    """
    Query StockItem table and return normalizer-ready catalog.
    Call once per import session and reuse the list.

    Usage:
        catalog = build_catalog_from_db(db)
        result  = normalize_and_map_item("MDH Jeera", 1, "kg", catalog, settings)
    """
    from database import StockItem  # local import to avoid circular

    items = db_session.query(StockItem).filter(StockItem.is_active == True).all()
    return [
        ItemCatalogEntry(
            id=item.id,
            name=item.name or "",
            units=item.units or "Nos",
            hsn_code=item.hsn_code,
            stock_group=item.stock_group,
        )
        for item in items
    ]


# ──────────────────────────────────────────────
# Batch Processing Helper
# ──────────────────────────────────────────────

def normalize_line_items(
    raw_items: List[Dict[str, Any]],
    db_session,
    settings: Optional[CompanySettings] = None,
) -> List[Dict[str, Any]]:
    """
    Normalize a full list of OCR-extracted line items in one call.

    Args:
        raw_items:   Each dict must have at least 'name', 'quantity', 'unit'.
                     It may also have 'rate', 'amount', 'hsn_code'.
        db_session:  SQLAlchemy session.
        settings:    CompanySettings; uses sensible defaults if None.

    Returns:
        Same list of dicts, each augmented with a 'normalization' key containing
        the NormalizedMappingResult serialized as a dict.
    """
    if settings is None:
        settings = CompanySettings()

    catalog = build_catalog_from_db(db_session)
    results = []

    for raw in raw_items:
        name = raw.get("name", "")
        qty  = float(raw.get("quantity", 1))
        unit = raw.get("unit", "")

        try:
            mapping = normalize_and_map_item(name, qty, unit, catalog, settings)
        except Exception as exc:  # never let one bad item crash the batch
            logger.exception("[ItemNorm] Failed for item %r: %s", name, exc)
            mapping = NormalizedMappingResult(
                action="NEEDS_REVIEW",
                chosen_item_id=None,
                normalized_base_name=_normalize_text(name),
                brand_candidate=None,
                size_info=None,
                unit=unit,
                confidence=0.0,
                reasoning=f"Internal error during normalization: {exc}",
            )

        augmented = dict(raw)
        augmented["normalization"] = {
            "action":               mapping.action,
            "chosen_item_id":       mapping.chosen_item_id,
            "normalized_base_name": mapping.normalized_base_name,
            "brand_candidate":      mapping.brand_candidate,
            "size_info":            mapping.size_info,
            "unit":                 mapping.unit,
            "confidence":           mapping.confidence,
            "reasoning":            mapping.reasoning,
            "suggestions": [
                {
                    "item_id":    s.item_id,
                    "name":       s.name,
                    "score":      s.score,
                    "units":      s.units,
                    "match_type": s.match_type,
                }
                for s in mapping.suggestions
            ],
        }
        results.append(augmented)

    return results
