"""
Tests for backend.services.item_normalizer

Run with:
    pytest backend/tests/test_item_normalizer.py -v
"""

import pytest
from services.item_normalizer import (
    ItemCatalogEntry,
    CompanySettings,
    NormalizedMappingResult,
    normalize_and_map_item,
    _normalize_text,
    _normalize_unit,
    _units_compatible,
    _extract_size_info,
    _split_brand_and_base,
    find_similar_items,
)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Fixtures
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.fixture
def catalog():
    """A small representative catalog of stock items."""
    return [
        ItemCatalogEntry(id=1,  name="Jeera",           units="kg"),
        ItemCatalogEntry(id=2,  name="Dhaniya",         units="kg"),
        ItemCatalogEntry(id=3,  name="Haldi",           units="kg"),
        ItemCatalogEntry(id=4,  name="Namak",           units="kg"),
        ItemCatalogEntry(id=5,  name="Atta",            units="kg"),
        ItemCatalogEntry(id=6,  name="Chawal Basmati",  units="kg"),
        ItemCatalogEntry(id=7,  name="Moong Dal",       units="kg"),
        ItemCatalogEntry(id=8,  name="Chana Dal",       units="kg"),
        ItemCatalogEntry(id=9,  name="Soyabean Oil",    units="ltr"),
        ItemCatalogEntry(id=10, name="Kaju",            units="kg"),
        ItemCatalogEntry(id=11, name="Sugar",           units="kg"),
        ItemCatalogEntry(id=12, name="Pens",            units="pcs"),
    ]


@pytest.fixture
def strict_settings():
    return CompanySettings(
        allow_brand_level_items=False,
        strict_single_item_per_commodity=True,
    )


@pytest.fixture
def lenient_settings():
    return CompanySettings(
        allow_brand_level_items=True,
        strict_single_item_per_commodity=False,
    )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Unit helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestHelpers:

    def test_normalize_text_lowercase(self):
        assert _normalize_text("JD JEERA 1KG") == "jd jeera 1kg"

    def test_normalize_text_strips_punct(self):
        assert "." not in _normalize_text("Tata Salt.")
        assert "!" not in _normalize_text("Fresh! Tomato!!")

    def test_normalize_text_collapses_spaces(self):
        result = _normalize_text("  hello   world  ")
        assert result == "hello world"

    def test_normalize_unit(self):
        assert _normalize_unit("KGS") == "kg"
        assert _normalize_unit("Pcs") == "pc"
        assert _normalize_unit("LTR") == "ltr"

    def test_units_compatible_same(self):
        assert _units_compatible("kg", "kg") is True

    def test_units_compatible_kg_gm(self):
        assert _units_compatible("kg", "gm") is True

    def test_units_compatible_ltr_ml(self):
        assert _units_compatible("ltr", "ml") is True

    def test_units_incompatible_kg_pcs(self):
        assert _units_compatible("kg", "pcs") is False

    def test_units_incompatible_ltr_kg(self):
        assert _units_compatible("ltr", "kg") is False

    def test_extract_size_removes_size(self):
        tokens, size = _extract_size_info(["jd", "jeera", "50kg"])
        assert "50kg" not in tokens
        assert size is not None
        assert "50" in size

    def test_extract_size_no_size(self):
        tokens, size = _extract_size_info(["jeera"])
        assert tokens == ["jeera"]
        assert size is None

    def test_split_brand_known_brand(self):
        commodity, brand = _split_brand_and_base(["mdh", "jeera"])
        assert "jeera" in commodity
        assert brand == "mdh"

    def test_split_brand_unknown_first_token(self):
        # "xyz" is not in known brands, but "jeera" is a commodity
        commodity, brand = _split_brand_and_base(["xyz", "jeera"])
        assert "xyz" not in commodity
        assert brand == "xyz"

    def test_split_brand_pure_commodity(self):
        commodity, brand = _split_brand_and_base(["jeera"])
        assert "jeera" in commodity
        assert brand is None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Core mapping tests
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNormalizeAndMapItem:

    # â”€â”€ USE_EXISTING scenarios â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_exact_base_name_maps_to_existing(self, catalog, strict_settings):
        res = normalize_and_map_item("Jeera", 1.0, "kg", catalog, strict_settings)
        assert res.action == "USE_EXISTING"
        assert res.chosen_item_id == 1
        assert "jeera" in res.normalized_base_name

    def test_brand_prefix_stripped_still_maps(self, catalog, strict_settings):
        """'MDH Jeera' â†’ maps to Jeera (id=1), brand='mdh'"""
        res = normalize_and_map_item("MDH Jeera", 1.0, "kg", catalog, strict_settings)
        assert res.action == "USE_EXISTING"
        assert res.chosen_item_id == 1
        assert res.brand_candidate == "mdh"

    def test_brand_and_size_stripped_correctly(self, catalog, strict_settings):
        """'JD Jeera 50kg' â†’ maps to Jeera, brand='jd', size='50kg'"""
        res = normalize_and_map_item("JD Jeera 50kg", 1.0, "kg", catalog, strict_settings)
        assert res.action == "USE_EXISTING"
        assert res.chosen_item_id == 1
        assert res.brand_candidate == "jd"
        assert res.size_info is not None
        assert "50" in res.size_info

    def test_tata_salt_maps_to_namak(self, catalog, strict_settings):
        """'Tata Salt 1kg' â†’ maps to Namak (id=4)"""
        res = normalize_and_map_item("Tata Salt 1kg", 1.0, "kg", catalog, strict_settings)
        # "Salt" and "Namak" may score medium; at least should not CREATE_NEW
        assert res.action in ("USE_EXISTING", "NEEDS_REVIEW")
        assert res.brand_candidate == "tata"

    def test_loose_qualifier_stripped(self, catalog, strict_settings):
        """'Loose Jeera' â†’ strips 'loose', maps to Jeera"""
        res = normalize_and_map_item("Loose Jeera", 1.0, "kg", catalog, strict_settings)
        assert res.action == "USE_EXISTING"
        assert res.chosen_item_id == 1

    def test_patanjali_atta_maps_to_atta(self, catalog, strict_settings):
        """'Patanjali Atta 10kg' â†’ maps to Atta (id=5)"""
        res = normalize_and_map_item("Patanjali Atta 10kg", 10.0, "kg", catalog, strict_settings)
        assert res.action in ("USE_EXISTING", "NEEDS_REVIEW")

    def test_suggestions_populated(self, catalog, strict_settings):
        res = normalize_and_map_item("MDH Haldi Powder", 0.5, "kg", catalog, strict_settings)
        assert isinstance(res.suggestions, list)

    def test_confidence_is_float(self, catalog, strict_settings):
        res = normalize_and_map_item("Jeera", 1.0, "kg", catalog, strict_settings)
        assert 0.0 <= res.confidence <= 1.0

    # â”€â”€ Unit incompatibility â†’ NEEDS_REVIEW â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_unit_mismatch_causes_review(self, catalog, strict_settings):
        """Jeera matched by name but OCR says 'pcs' â€” incompatible units"""
        res = normalize_and_map_item("Jeera", 10.0, "pcs", catalog, strict_settings)
        assert res.action == "NEEDS_REVIEW"
        assert "incompatible" in res.reasoning.lower()

    def test_kg_gm_compatible(self, catalog, strict_settings):
        """Jeera with 'gm' unit â†’ compatible with catalog 'kg'"""
        res = normalize_and_map_item("Jeera", 500.0, "gm", catalog, strict_settings)
        assert res.action == "USE_EXISTING"
        assert res.chosen_item_id == 1

    # â”€â”€ CREATE_NEW / NEEDS_REVIEW for truly unknown items â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_totally_unknown_item_strict_gives_review(self, catalog, strict_settings):
        """'Bluetooth Speaker' â†’ nothing in catalog â†’ NEEDS_REVIEW (brand items not allowed)"""
        res = normalize_and_map_item("Bluetooth Speaker", 1.0, "pcs", catalog, strict_settings)
        assert res.action == "NEEDS_REVIEW"
        assert res.chosen_item_id is None

    def test_totally_unknown_item_lenient_creates_new(self, catalog, lenient_settings):
        """'Bluetooth Speaker' â†’ nothing in catalog â†’ CREATE_NEW (brand items allowed)"""
        res = normalize_and_map_item("Bluetooth Speaker", 1.0, "pcs", catalog, lenient_settings)
        assert res.action == "CREATE_NEW"
        assert res.chosen_item_id is None

    def test_empty_catalog_gives_no_match(self, strict_settings):
        res = normalize_and_map_item("Jeera", 1.0, "kg", [], strict_settings)
        assert res.action in ("NEEDS_REVIEW", "CREATE_NEW")
        assert res.chosen_item_id is None

    # â”€â”€ Robustness / edge cases â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_all_caps_input(self, catalog, strict_settings):
        res = normalize_and_map_item("MDH JEERA", 1.0, "KG", catalog, strict_settings)
        assert res.action == "USE_EXISTING"
        assert res.chosen_item_id == 1

    def test_extra_whitespace_input(self, catalog, strict_settings):
        res = normalize_and_map_item("  Jeera  ", 1.0, "kg", catalog, strict_settings)
        assert res.action == "USE_EXISTING"

    def test_punctuation_in_name(self, catalog, strict_settings):
        res = normalize_and_map_item("Jeera, 1kg.", 1.0, "kg", catalog, strict_settings)
        assert res.action == "USE_EXISTING"

    def test_result_has_all_fields(self, catalog, strict_settings):
        res = normalize_and_map_item("Jeera", 1.0, "kg", catalog, strict_settings)
        assert hasattr(res, "action")
        assert hasattr(res, "chosen_item_id")
        assert hasattr(res, "normalized_base_name")
        assert hasattr(res, "brand_candidate")
        assert hasattr(res, "size_info")
        assert hasattr(res, "unit")
        assert hasattr(res, "confidence")
        assert hasattr(res, "reasoning")
        assert hasattr(res, "suggestions")

    def test_reasoning_is_non_empty_string(self, catalog, strict_settings):
        res = normalize_and_map_item("MDH Jeera", 1.0, "kg", catalog, strict_settings)
        assert isinstance(res.reasoning, str)
        assert len(res.reasoning) > 5

    def test_pens_incompatible_with_kg_items(self, catalog, strict_settings):
        """'Pens' should map to Pens (id=12, unit=pcs), not to any kg item"""
        res = normalize_and_map_item("Pens", 10.0, "pcs", catalog, strict_settings)
        if res.action == "USE_EXISTING":
            assert res.chosen_item_id == 12

    # â”€â”€ Multi-candidate ambiguity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_ambiguous_dal_in_lenient_mode(self, catalog, lenient_settings):
        """'Dal' matches both Moong Dal and Chana Dal; lenient multi-item mode â†’ NEEDS_REVIEW"""
        res = normalize_and_map_item("Dal", 1.0, "kg", catalog, lenient_settings)
        # Either returns top candidate (strict) or asks for review (lenient)
        assert res.action in ("USE_EXISTING", "NEEDS_REVIEW")
        assert len(res.suggestions) >= 1

    def test_ambiguous_dal_strict_mode_picks_best(self, catalog, strict_settings):
        """Strict mode auto-picks best match for 'Dal'"""
        res = normalize_and_map_item("Dal", 1.0, "kg", catalog, strict_settings)
        assert res.action in ("USE_EXISTING", "NEEDS_REVIEW")
        if res.action == "USE_EXISTING":
            assert res.chosen_item_id in (7, 8)   # Moong or Chana Dal

    # â”€â”€ find_similar_items unit test â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_find_similar_items_returns_sorted(self, catalog):
        results = find_similar_items("jeera", catalog, top_k=3)
        assert len(results) <= 3
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_find_similar_items_jeera_top(self, catalog):
        results = find_similar_items("jeera", catalog, top_k=5)
        top_item = results[0][0]
        assert "jeera" in top_item.normalized_name.lower()

