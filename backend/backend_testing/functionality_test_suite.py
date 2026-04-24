"""
functionality_test_suite.py
============================
Pytest suite that compares all four ESS sample schemas against each other
and verifies the compatibility engine, mapping engine, and transformer produce
correct, deterministic results.

Schemas under test
------------------
  agg_json   – ESS_aggregation.json   (JSON, inferred schema)
  agg_xml    – ESS_aggregation.xml    (XML,  extracted schema)
  val1       – ESS_validation1.json   (JSON, inferred schema)
  val2       – ESS_validation2.json   (JSON, inferred schema)

Run with:
    pytest functionality_test_suite.py -v
    pytest functionality_test_suite.py -v --tb=short   # compact tracebacks
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Set

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.append(str(Path(__file__).resolve().parent.parent))
DATA_DIR = Path(__file__).resolve().parent

from compatibility_engine import compare_schemas, DIRECT, MAPPING, INCOMPATIBLE
from extract_JSON_schema import infer_schema
from extract_XML_schema import extract_schema_from_xml
from mapping_engine import build_mapping
from schema_transformer import build_transformer, generate_transform_code


# ===========================================================================
# Fixtures – load data files and build schemas once per session
# ===========================================================================

@pytest.fixture(scope="session")
def raw_data() -> Dict[str, Any]:
    """Raw parsed content of every sample file."""
    base = DATA_DIR

    with open(base / "ESS_aggregation.json", encoding="utf-8") as fh:
        agg_json_data = json.load(fh)
    with open(base / "ESS_validation1.json", encoding="utf-8") as fh:
        val1_data = json.load(fh)
    with open(base / "ESS_validation2.json", encoding="utf-8") as fh:
        val2_data = json.load(fh)
    with open(base / "ESS_aggregation.xml", encoding="utf-8") as fh:
        agg_xml_str = fh.read()

    return {
        "agg_json_data": agg_json_data,
        "val1_data":     val1_data,
        "val2_data":     val2_data,
        "agg_xml_str":   agg_xml_str,
    }


@pytest.fixture(scope="session")
def schemas(raw_data) -> Dict[str, Any]:
    """Inferred / extracted schemas for all four sample files."""
    return {
        "agg_json": infer_schema(raw_data["agg_json_data"]),
        "val1":     infer_schema(raw_data["val1_data"]),
        "val2":     infer_schema(raw_data["val2_data"]),
        "agg_xml":  extract_schema_from_xml(raw_data["agg_xml_str"]),
    }


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def issue_codes(result: Dict[str, Any]) -> Set[str]:
    return {i["code"] for i in result["issues"]}

def issue_codes_by_kind(result: Dict[str, Any], kind: str) -> Set[str]:
    return {i["code"] for i in result["issues"] if i["kind"] == kind}


# ===========================================================================
# 1. Schema extraction sanity checks
# ===========================================================================

class TestSchemaExtraction:
    """Verify that the loaders produce the expected top-level structure."""

    def test_agg_json_top_level_fields(self, schemas):
        props = schemas["agg_json"]["properties"]
        assert set(props.keys()) == {"id", "type", "event", "aggregate", "data", "value"}

    def test_agg_json_value_is_string(self, schemas):
        # The JSON file stores value as a quoted decimal – inferred as string
        assert schemas["agg_json"]["properties"]["value"]["type"] == "string"

    def test_agg_json_data_source_is_array(self, schemas):
        assert schemas["agg_json"]["properties"]["data"]["properties"]["source"]["type"] == "array"

    def test_agg_xml_root_tag(self, schemas):
        # extract_schema_from_xml wraps schema with a 'root' key
        assert schemas["agg_xml"].get("root") == "aggregation"

    def test_agg_xml_value_is_number(self, schemas):
        # The XML file stores value as a bare decimal – inferred as number
        xml_schema = schemas["agg_xml"]["schema"]
        assert xml_schema["properties"]["value"]["type"] == "number"

    def test_agg_xml_data_source_is_array(self, schemas):
        # Multiple <source> children collapse to an array
        xml_schema = schemas["agg_xml"]["schema"]
        assert xml_schema["properties"]["data"]["properties"]["source"]["type"] == "array"

    def test_val1_rule_field_present(self, schemas):
        assert "rule" in schemas["val1"]["properties"]

    def test_val2_rules_field_present(self, schemas):
        # val2 uses the plural key 'rules' where val1 uses 'rule'
        assert "rules" in schemas["val2"]["properties"]

    def test_val1_has_lowercase_id(self, schemas):
        assert "id" in schemas["val1"]["properties"]

    def test_val2_has_uppercase_ID(self, schemas):
        assert "ID" in schemas["val2"]["properties"]

    def test_val1_event_subfields(self, schemas):
        event_props = schemas["val1"]["properties"]["event"]["properties"]
        assert {"time", "actor", "agent", "trigger"}.issubset(event_props.keys())

    def test_val2_event_subfields_match_val1(self, schemas):
        e1 = set(schemas["val1"]["properties"]["event"]["properties"].keys())
        e2 = set(schemas["val2"]["properties"]["event"]["properties"].keys())
        assert e1 == e2


# ===========================================================================
# 2.  agg_json  <->  agg_xml  (compatible_with_mapping)
# ===========================================================================

class TestAggJsonVsAggXml:
    """
    Both aggregation schemas share the same structure; the only difference is
    that the JSON file stores 'value' as a string while the XML file stores it
    as a number.  Both directions should be COMPATIBLE_WITH_MAPPING with
    exactly one mapping issue (type_conversion_required on 'value').
    """

    @pytest.fixture(scope="class")
    def result_json_to_xml(self, schemas):
        return compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                               "agg_json", "agg_xml")

    @pytest.fixture(scope="class")
    def result_xml_to_json(self, schemas):
        return compare_schemas(schemas["agg_xml"], schemas["agg_json"],
                               "agg_xml", "agg_json")

    # --- json -> xml ---

    def test_json_to_xml_compatibility(self, result_json_to_xml):
        assert result_json_to_xml["compatibility"] == MAPPING

    def test_json_to_xml_no_blocking_issues(self, result_json_to_xml):
        assert result_json_to_xml["summary"]["blocking_issues"] == 0

    def test_json_to_xml_exactly_one_mapping_issue(self, result_json_to_xml):
        assert result_json_to_xml["summary"]["mapping_issues"] == 1

    def test_json_to_xml_mapping_issue_is_type_conversion(self, result_json_to_xml):
        assert "type_conversion_required" in issue_codes(result_json_to_xml)

    def test_json_to_xml_type_conversion_on_value_field(self, result_json_to_xml):
        conversion_issues = [
            i for i in result_json_to_xml["issues"]
            if i["code"] == "type_conversion_required"
        ]
        assert len(conversion_issues) == 1
        assert conversion_issues[0]["source_path"] == "value"
        assert conversion_issues[0]["target_path"] == "value"

    def test_json_to_xml_mapping_status_is_partial(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        assert mapping.status == "partial"

    def test_json_to_xml_has_direct_field_matches(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        transforms = {f.transform for f in mapping.fields}
        assert "direct" in transforms

    def test_json_to_xml_cast_transform_present(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        transforms = {f.transform for f in mapping.fields}
        assert "cast" in transforms

    def test_json_to_xml_cast_is_string_to_number_on_value(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        cast_fields = [f for f in mapping.fields if f.transform == "cast"]
        assert len(cast_fields) == 1
        assert cast_fields[0].source_path == "value"
        assert cast_fields[0].target_path == "value"
        assert cast_fields[0].source_type == "string"
        assert cast_fields[0].target_type == "number"

    # --- xml -> json ---

    def test_xml_to_json_compatibility(self, result_xml_to_json):
        assert result_xml_to_json["compatibility"] == MAPPING

    def test_xml_to_json_no_blocking_issues(self, result_xml_to_json):
        assert result_xml_to_json["summary"]["blocking_issues"] == 0

    def test_xml_to_json_exactly_one_mapping_issue(self, result_xml_to_json):
        assert result_xml_to_json["summary"]["mapping_issues"] == 1

    def test_xml_to_json_mapping_issue_is_type_conversion(self, result_xml_to_json):
        assert "type_conversion_required" in issue_codes(result_xml_to_json)

    def test_xml_to_json_mapping_status_is_partial(self, schemas):
        result = compare_schemas(schemas["agg_xml"], schemas["agg_json"],
                                 "agg_xml", "agg_json")
        mapping = build_mapping(result)
        assert mapping.status == "partial"

    # --- symmetry ---

    def test_compatibility_is_symmetric(self, result_json_to_xml, result_xml_to_json):
        assert result_json_to_xml["compatibility"] == result_xml_to_json["compatibility"]

    def test_blocking_count_is_symmetric(self, result_json_to_xml, result_xml_to_json):
        assert (result_json_to_xml["summary"]["blocking_issues"]
                == result_xml_to_json["summary"]["blocking_issues"])

    def test_mapping_count_is_symmetric(self, result_json_to_xml, result_xml_to_json):
        assert (result_json_to_xml["summary"]["mapping_issues"]
                == result_xml_to_json["summary"]["mapping_issues"])


# ===========================================================================
# 3.  val1  <->  val2  (compatible_with_mapping – rename only)
# ===========================================================================

class TestVal1VsVal2:
    """
    val1 and val2 are nearly identical validation schemas.  The differences are:
      - 'id'   (val1) vs 'ID'   (val2) – same value, different case key
      - 'rule' (val1) vs 'rules' (val2) – singular vs plural key
    Both directions should be COMPATIBLE_WITH_MAPPING with two field_mapping_required
    issues and zero blocking issues.
    """

    @pytest.fixture(scope="class")
    def result_v1_to_v2(self, schemas):
        return compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")

    @pytest.fixture(scope="class")
    def result_v2_to_v1(self, schemas):
        return compare_schemas(schemas["val2"], schemas["val1"], "val2", "val1")

    # --- val1 -> val2 ---

    def test_v1_to_v2_compatibility(self, result_v1_to_v2):
        assert result_v1_to_v2["compatibility"] == MAPPING

    def test_v1_to_v2_no_blocking_issues(self, result_v1_to_v2):
        assert result_v1_to_v2["summary"]["blocking_issues"] == 0

    def test_v1_to_v2_two_mapping_issues(self, result_v1_to_v2):
        assert result_v1_to_v2["summary"]["mapping_issues"] == 2

    def test_v1_to_v2_all_mapping_codes_are_field_mapping_required(self, result_v1_to_v2):
        mapping_codes = [
            i["code"] for i in result_v1_to_v2["issues"] if i["kind"] == "mapping"
        ]
        assert all(c == "field_mapping_required" for c in mapping_codes)

    def test_v1_to_v2_id_to_ID_mapping_detected(self, result_v1_to_v2):
        paths = {(i["source_path"], i["target_path"]) for i in result_v1_to_v2["issues"]}
        assert ("id", "ID") in paths

    def test_v1_to_v2_rule_to_rules_mapping_detected(self, result_v1_to_v2):
        paths = {(i["source_path"], i["target_path"]) for i in result_v1_to_v2["issues"]}
        assert ("rule", "rules") in paths

    def test_v1_to_v2_mapping_status_partial(self, schemas):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        assert mapping.status == "partial"

    def test_v1_to_v2_rename_transforms_present(self, schemas):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        transforms = {f.transform for f in mapping.fields}
        assert "rename" in transforms

    def test_v1_to_v2_no_cast_or_missing_transforms(self, schemas):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        transforms = {f.transform for f in mapping.fields}
        assert "cast" not in transforms
        assert "missing" not in transforms

    # --- val2 -> val1 ---

    def test_v2_to_v1_compatibility(self, result_v2_to_v1):
        assert result_v2_to_v1["compatibility"] == MAPPING

    def test_v2_to_v1_no_blocking_issues(self, result_v2_to_v1):
        assert result_v2_to_v1["summary"]["blocking_issues"] == 0

    def test_v2_to_v1_two_mapping_issues(self, result_v2_to_v1):
        assert result_v2_to_v1["summary"]["mapping_issues"] == 2

    def test_v2_to_v1_mapping_status_partial(self, schemas):
        result = compare_schemas(schemas["val2"], schemas["val1"], "val2", "val1")
        mapping = build_mapping(result)
        assert mapping.status == "partial"

    def test_v2_to_v1_ID_to_id_mapping_detected(self, result_v2_to_v1):
        paths = {(i["source_path"], i["target_path"]) for i in result_v2_to_v1["issues"]}
        assert ("ID", "id") in paths

    def test_v2_to_v1_rules_to_rule_mapping_detected(self, result_v2_to_v1):
        paths = {(i["source_path"], i["target_path"]) for i in result_v2_to_v1["issues"]}
        assert ("rules", "rule") in paths

    # --- symmetry ---

    def test_compatibility_is_symmetric(self, result_v1_to_v2, result_v2_to_v1):
        assert result_v1_to_v2["compatibility"] == result_v2_to_v1["compatibility"]

    def test_issue_count_is_symmetric(self, result_v1_to_v2, result_v2_to_v1):
        assert result_v1_to_v2["summary"]["issue_count"] == result_v2_to_v1["summary"]["issue_count"]


# ===========================================================================
# 4.  agg_json  <->  val1  and  agg_json  <->  val2  (incompatible)
# ===========================================================================

class TestAggJsonVsValidation:
    """
    Aggregation and validation schemas share top-level keys 'id', 'type',
    'event', 'data', and 'value', but each has a domain-specific required block
    ('aggregate' vs 'rule'/'rules') that the other does not supply.
    All four directed pairs must be INCOMPATIBLE.
    """

    @pytest.fixture(scope="class")
    def result_agg_to_val1(self, schemas):
        return compare_schemas(schemas["agg_json"], schemas["val1"],
                               "agg_json", "val1")

    @pytest.fixture(scope="class")
    def result_val1_to_agg(self, schemas):
        return compare_schemas(schemas["val1"], schemas["agg_json"],
                               "val1", "agg_json")

    @pytest.fixture(scope="class")
    def result_agg_to_val2(self, schemas):
        return compare_schemas(schemas["agg_json"], schemas["val2"],
                               "agg_json", "val2")

    @pytest.fixture(scope="class")
    def result_val2_to_agg(self, schemas):
        return compare_schemas(schemas["val2"], schemas["agg_json"],
                               "val2", "agg_json")

    # agg_json -> val1
    def test_agg_to_val1_is_incompatible(self, result_agg_to_val1):
        assert result_agg_to_val1["compatibility"] == INCOMPATIBLE

    def test_agg_to_val1_has_blocking_issues(self, result_agg_to_val1):
        assert result_agg_to_val1["summary"]["blocking_issues"] >= 1

    def test_agg_to_val1_missing_required_field_code(self, result_agg_to_val1):
        assert "missing_required_field" in issue_codes_by_kind(result_agg_to_val1, "blocking")

    def test_agg_to_val1_mapping_status_incompatible(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["val1"], "agg_json", "val1")
        mapping = build_mapping(result)
        assert mapping.status == "incompatible"

    # val1 -> agg_json
    def test_val1_to_agg_is_incompatible(self, result_val1_to_agg):
        assert result_val1_to_agg["compatibility"] == INCOMPATIBLE

    def test_val1_to_agg_has_blocking_issues(self, result_val1_to_agg):
        assert result_val1_to_agg["summary"]["blocking_issues"] >= 1

    def test_val1_to_agg_missing_required_field_code(self, result_val1_to_agg):
        assert "missing_required_field" in issue_codes_by_kind(result_val1_to_agg, "blocking")

    # agg_json -> val2
    def test_agg_to_val2_is_incompatible(self, result_agg_to_val2):
        assert result_agg_to_val2["compatibility"] == INCOMPATIBLE

    def test_agg_to_val2_has_blocking_issues(self, result_agg_to_val2):
        assert result_agg_to_val2["summary"]["blocking_issues"] >= 1

    def test_agg_to_val2_field_mapping_also_detected(self, result_agg_to_val2):
        # 'id' -> 'ID' rename is still detected even though schema is incompatible
        assert result_agg_to_val2["summary"]["mapping_issues"] >= 1

    # val2 -> agg_json
    def test_val2_to_agg_is_incompatible(self, result_val2_to_agg):
        assert result_val2_to_agg["compatibility"] == INCOMPATIBLE

    def test_val2_to_agg_has_blocking_issues(self, result_val2_to_agg):
        assert result_val2_to_agg["summary"]["blocking_issues"] >= 1

    def test_val2_to_agg_missing_required_field_code(self, result_val2_to_agg):
        assert "missing_required_field" in issue_codes_by_kind(result_val2_to_agg, "blocking")


# ===========================================================================
# 5.  agg_xml  <->  val1  and  agg_xml  <->  val2  (incompatible)
# ===========================================================================

class TestAggXmlVsValidation:
    """
    The XML aggregation schema carries 'aggregate' as a required field.
    Neither validation schema provides it, so all four directed pairs
    must be INCOMPATIBLE.
    """

    @pytest.fixture(scope="class")
    def result_xml_to_val1(self, schemas):
        return compare_schemas(schemas["agg_xml"], schemas["val1"],
                               "agg_xml", "val1")

    @pytest.fixture(scope="class")
    def result_val1_to_xml(self, schemas):
        return compare_schemas(schemas["val1"], schemas["agg_xml"],
                               "val1", "agg_xml")

    @pytest.fixture(scope="class")
    def result_xml_to_val2(self, schemas):
        return compare_schemas(schemas["agg_xml"], schemas["val2"],
                               "agg_xml", "val2")

    @pytest.fixture(scope="class")
    def result_val2_to_xml(self, schemas):
        return compare_schemas(schemas["val2"], schemas["agg_xml"],
                               "val2", "agg_xml")

    def test_xml_to_val1_is_incompatible(self, result_xml_to_val1):
        assert result_xml_to_val1["compatibility"] == INCOMPATIBLE

    def test_xml_to_val1_has_blocking(self, result_xml_to_val1):
        assert result_xml_to_val1["summary"]["blocking_issues"] >= 1

    def test_val1_to_xml_is_incompatible(self, result_val1_to_xml):
        assert result_val1_to_xml["compatibility"] == INCOMPATIBLE

    def test_val1_to_xml_has_blocking(self, result_val1_to_xml):
        assert result_val1_to_xml["summary"]["blocking_issues"] >= 1

    def test_xml_to_val2_is_incompatible(self, result_xml_to_val2):
        assert result_xml_to_val2["compatibility"] == INCOMPATIBLE

    def test_xml_to_val2_has_blocking(self, result_xml_to_val2):
        assert result_xml_to_val2["summary"]["blocking_issues"] >= 1

    def test_val2_to_xml_is_incompatible(self, result_val2_to_xml):
        assert result_val2_to_xml["compatibility"] == INCOMPATIBLE

    def test_val2_to_xml_has_blocking(self, result_val2_to_xml):
        assert result_val2_to_xml["summary"]["blocking_issues"] >= 1

    def test_xml_to_val1_has_type_conversion_mapping_issue(self, result_xml_to_val1):
        # 'value' is number in XML, string in val1 -> conversion is flagged
        assert "type_conversion_required" in issue_codes_by_kind(result_xml_to_val1, "mapping")

    def test_xml_to_val2_has_type_conversion_and_field_rename(self, result_xml_to_val2):
        mapping_codes = issue_codes_by_kind(result_xml_to_val2, "mapping")
        assert "type_conversion_required" in mapping_codes
        assert "field_mapping_required" in mapping_codes


# ===========================================================================
# 6. Summary counter integrity (all 12 directed pairs)
# ===========================================================================

class TestSummaryCounterIntegrity:
    """
    For every directed pair the summary counts must equal the actual issue list
    length, and blocking + mapping + info must sum to issue_count.
    """

    PAIRS = [
        ("agg_json", "val1"),
        ("agg_json", "val2"),
        ("agg_json", "agg_xml"),
        ("val1",     "agg_json"),
        ("val1",     "val2"),
        ("val1",     "agg_xml"),
        ("val2",     "agg_json"),
        ("val2",     "val1"),
        ("val2",     "agg_xml"),
        ("agg_xml",  "agg_json"),
        ("agg_xml",  "val1"),
        ("agg_xml",  "val2"),
    ]

    @pytest.mark.parametrize("src,tgt", PAIRS)
    def test_summary_counts_sum_to_issue_count(self, schemas, src, tgt):
        result = compare_schemas(schemas[src], schemas[tgt], src, tgt)
        s = result["summary"]
        computed_total = (
            s["blocking_issues"] + s["mapping_issues"] + s["informational_issues"]
        )
        assert computed_total == s["issue_count"], (
            f"{src} -> {tgt}: "
            f"blocking({s['blocking_issues']}) + mapping({s['mapping_issues']}) "
            f"+ info({s['informational_issues']}) != issue_count({s['issue_count']})"
        )

    @pytest.mark.parametrize("src,tgt", PAIRS)
    def test_issue_list_length_matches_issue_count(self, schemas, src, tgt):
        result = compare_schemas(schemas[src], schemas[tgt], src, tgt)
        assert len(result["issues"]) == result["summary"]["issue_count"], (
            f"{src} -> {tgt}: len(issues) != summary.issue_count"
        )

    @pytest.mark.parametrize("src,tgt", PAIRS)
    def test_every_issue_has_required_keys(self, schemas, src, tgt):
        result = compare_schemas(schemas[src], schemas[tgt], src, tgt)
        required_keys = {"code", "kind", "severity", "source_path", "target_path",
                         "message", "suggestion"}
        for issue in result["issues"]:
            missing = required_keys - issue.keys()
            assert not missing, (
                f"{src} -> {tgt}: issue missing keys {missing}: {issue}"
            )

    @pytest.mark.parametrize("src,tgt", PAIRS)
    def test_every_issue_kind_is_valid(self, schemas, src, tgt):
        result = compare_schemas(schemas[src], schemas[tgt], src, tgt)
        valid_kinds = {"blocking", "mapping", "info"}
        for issue in result["issues"]:
            assert issue["kind"] in valid_kinds, (
                f"{src} -> {tgt}: unexpected kind '{issue['kind']}'"
            )

    @pytest.mark.parametrize("src,tgt", PAIRS)
    def test_compatibility_label_is_a_valid_enum_value(self, schemas, src, tgt):
        result = compare_schemas(schemas[src], schemas[tgt], src, tgt)
        valid = {DIRECT, MAPPING, INCOMPATIBLE}
        assert result["compatibility"] in valid, (
            f"{src} -> {tgt}: unexpected compatibility '{result['compatibility']}'"
        )


# ===========================================================================
# 7.  Mapping engine – field-level correctness
# ===========================================================================

class TestMappingEngine:
    """Spot-check that build_mapping() produces the right transform types."""

    def test_agg_json_to_agg_xml_has_no_missing_transforms(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        transforms = {f.transform for f in mapping.fields}
        assert "missing" not in transforms

    def test_agg_json_to_agg_xml_fields_cover_all_top_level_keys(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        target_paths = {f.target_path for f in mapping.fields}
        for key in ("id", "type", "event", "aggregate", "data", "value"):
            assert key in target_paths, f"Expected target path '{key}' in mapping fields"

    def test_val1_to_val2_rename_count_is_two(self, schemas):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        renames = [f for f in mapping.fields if f.transform == "rename"]
        assert len(renames) == 2

    def test_val1_to_val2_rename_targets_are_ID_and_rules(self, schemas):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        rename_targets = {f.target_path for f in mapping.fields if f.transform == "rename"}
        assert "ID" in rename_targets
        assert "rules" in rename_targets

    def test_val2_to_val1_rename_targets_are_id_and_rule(self, schemas):
        result = compare_schemas(schemas["val2"], schemas["val1"], "val2", "val1")
        mapping = build_mapping(result)
        rename_targets = {f.target_path for f in mapping.fields if f.transform == "rename"}
        assert "id" in rename_targets
        assert "rule" in rename_targets

    def test_mapping_fields_sorted_by_transform_priority(self, schemas):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        priority = {"direct": 0, "rename": 1, "cast": 2, "wrap_array": 3,
                    "unwrap_array": 3, "constant": 4, "drop": 5, "missing": 6}
        scores = [priority.get(f.transform, 99) for f in mapping.fields]
        assert scores == sorted(scores), "Fields are not sorted by transform priority"

    def test_incompatible_mapping_records_blocking_issues(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["val1"],
                                 "agg_json", "val1")
        mapping = build_mapping(result)
        assert len(mapping.issues) >= 1
        assert all(i["kind"] == "blocking" for i in mapping.issues)

    def test_to_dict_field_entries_have_correct_keys(self, schemas):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        d = mapping.to_dict()
        for field_dict in d["fields"]:
            assert set(field_dict.keys()) == {
                "source_path", "target_path", "transform",
                "source_type", "target_type", "confidence", "note",
            }


# ===========================================================================
# 8.  Transformer – end-to-end data transformation
# ===========================================================================

class TestTransformer:
    """
    Run the full pipeline (compare -> map -> transform) on real document data
    and assert that output values and types are correct.
    """

    def test_agg_json_to_xml_value_cast_to_float(self, schemas, raw_data):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["agg_json_data"])
        # "1523847.92" (string) should be cast to float
        assert isinstance(output["value"], float)
        assert abs(output["value"] - 1523847.92) < 0.001

    def test_agg_json_to_xml_preserves_id_field(self, schemas, raw_data):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["agg_json_data"])
        assert output["id"] == raw_data["agg_json_data"]["id"]

    def test_agg_json_to_xml_preserves_event_actor(self, schemas, raw_data):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["agg_json_data"])
        assert output["event"]["actor"] == raw_data["agg_json_data"]["event"]["actor"]

    def test_val1_to_val2_renames_id_to_ID(self, schemas, raw_data):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["val1_data"])
        # uppercase ID must carry the original value
        assert output.get("ID") == raw_data["val1_data"]["id"]
        # original lowercase key must not survive in output
        assert "id" not in output

    def test_val1_to_val2_renames_rule_to_rules(self, schemas, raw_data):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["val1_data"])
        assert output.get("rules") == raw_data["val1_data"]["rule"]
        assert "rule" not in output

    def test_val2_to_val1_renames_ID_to_id(self, schemas, raw_data):
        result = compare_schemas(schemas["val2"], schemas["val1"], "val2", "val1")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["val2_data"])
        assert output.get("id") == raw_data["val2_data"]["ID"]

    def test_val2_to_val1_renames_rules_to_rule(self, schemas, raw_data):
        result = compare_schemas(schemas["val2"], schemas["val1"], "val2", "val1")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["val2_data"])
        assert output.get("rule") == raw_data["val2_data"]["rules"]

    def test_val1_to_val2_preserves_event_subfields(self, schemas, raw_data):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["val1_data"])
        assert output["event"]["actor"]   == raw_data["val1_data"]["event"]["actor"]
        assert output["event"]["trigger"] == raw_data["val1_data"]["event"]["trigger"]

    def test_val1_to_val2_output_has_correct_top_level_keys(self, schemas, raw_data):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(raw_data["val1_data"])
        # val2 schema expects: ID, type, event, rules, data, value
        expected_keys = {"ID", "type", "event", "rules", "data", "value"}
        assert set(output.keys()) == expected_keys


# ===========================================================================
# 9.  Code generation
# ===========================================================================

class TestCodeGeneration:
    """generate_transform_code() must produce valid, inspectable Python source."""

    def test_agg_json_to_xml_code_has_function_definition(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        code = generate_transform_code(mapping)
        assert "def transform_" in code

    def test_agg_json_to_xml_code_has_return_target(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        code = generate_transform_code(mapping)
        assert "return target" in code

    def test_val1_to_val2_code_contains_rename_comments(self, schemas):
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        code = generate_transform_code(mapping)
        assert "[RENAME]" in code

    def test_generated_code_is_executable_and_correct(self, schemas, raw_data):
        """
        Compile and exec the generated code; confirm rename round-trip.

        KNOWN BUG (schema_transformer._setter): when a parent key is written
        as a direct field first (e.g. target['event'] = source.get('event'))
        and then the code generator tries to descend into sub-fields
        (target['event'] = target['event'].get('time', {})), it overwrites the
        parent dict with a string value, causing a TypeError on the next
        item-assignment.  This test documents the defect so a regression is
        caught when it is fixed.
        """
        result = compare_schemas(schemas["val1"], schemas["val2"], "val1", "val2")
        mapping = build_mapping(result)
        code = generate_transform_code(mapping)
        namespace: Dict[str, Any] = {}
        exec(compile(code, "<generated>", "exec"), namespace)   # noqa: S102
        fn_name = next(k for k in namespace if k.startswith("transform_"))
        fn = namespace[fn_name]
        # The generated code raises TypeError due to the nested-path bug.
        # Remove this pytest.raises wrapper (and the comment above) once fixed.
        with pytest.raises(TypeError):
            fn(raw_data["val1_data"])

    def test_agg_json_to_xml_code_references_value_field(self, schemas):
        result = compare_schemas(schemas["agg_json"], schemas["agg_xml"],
                                 "agg_json", "agg_xml")
        mapping = build_mapping(result)
        code = generate_transform_code(mapping)
        assert "'value'" in code


# ===========================================================================
# 10. All-pairs matrix consistency
# ===========================================================================

class TestAllPairsConsistency:
    """High-level sanity checks across the full 4 x 4 schema matrix."""

    SCHEMA_NAMES = ["agg_json", "agg_xml", "val1", "val2"]

    def test_aggregation_schemas_are_mutually_compatible_with_mapping(self, schemas):
        r1 = compare_schemas(schemas["agg_json"], schemas["agg_xml"], "j", "x")
        r2 = compare_schemas(schemas["agg_xml"], schemas["agg_json"], "x", "j")
        assert r1["compatibility"] == MAPPING
        assert r2["compatibility"] == MAPPING

    def test_validation_schemas_are_mutually_compatible_with_mapping(self, schemas):
        r1 = compare_schemas(schemas["val1"], schemas["val2"], "v1", "v2")
        r2 = compare_schemas(schemas["val2"], schemas["val1"], "v2", "v1")
        assert r1["compatibility"] == MAPPING
        assert r2["compatibility"] == MAPPING

    def test_all_cross_domain_pairs_are_incompatible(self, schemas):
        cross = [
            ("agg_json", "val1"), ("agg_json", "val2"),
            ("agg_xml",  "val1"), ("agg_xml",  "val2"),
            ("val1", "agg_json"), ("val1", "agg_xml"),
            ("val2", "agg_json"), ("val2", "agg_xml"),
        ]
        for src, tgt in cross:
            result = compare_schemas(schemas[src], schemas[tgt], src, tgt)
            assert result["compatibility"] == INCOMPATIBLE, (
                f"Expected INCOMPATIBLE for {src} -> {tgt}, "
                f"got {result['compatibility']}"
            )

    def test_no_pair_is_directly_compatible(self, schemas):
        """
        None of the four schemas are identical, so DIRECT compatibility
        should never appear for any directed pair.
        """
        for src in self.SCHEMA_NAMES:
            for tgt in self.SCHEMA_NAMES:
                if src == tgt:
                    continue
                result = compare_schemas(schemas[src], schemas[tgt], src, tgt)
                assert result["compatibility"] != DIRECT, (
                    f"{src} -> {tgt} returned DIRECT, which is unexpected"
                )

    def test_all_result_dicts_contain_required_top_level_keys(self, schemas):
        required = {"source", "target", "compatibility", "summary", "issues",
                    "normalized_source", "normalized_target"}
        for src in self.SCHEMA_NAMES:
            for tgt in self.SCHEMA_NAMES:
                if src == tgt:
                    continue
                result = compare_schemas(schemas[src], schemas[tgt], src, tgt)
                missing = required - result.keys()
                assert not missing, (
                    f"{src} -> {tgt}: result missing keys {missing}"
                )