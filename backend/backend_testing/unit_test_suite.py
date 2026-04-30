"""
unit_test_suite.py
-------------
Unit tests for compatibility_engine, mapping_engine, schema_transformer,
extract_JSON_schema, and extract_XML_schema.

Run with:
    pytest unit_test_suite.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from compatibility_engine import (
    DIRECT,
    INCOMPATIBLE,
    MAPPING,
    build_index,
    classify_issues,
    compare_schemas,
    normalize_name,
    normalize_schema,
    primitive_relation,
    tokenize_name,
)
from extract_JSON_schema import infer_schema
from extract_XML_schema import extract_schema_from_xml, infer_type
from mapping_engine import build_mapping
from schema_transformer import build_transformer, generate_transform_code

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_object(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": required if required is not None else list(properties.keys()),
    }


def make_field(type_):
    return {"type": type_}


# ===========================================================================
# normalize_name / tokenize_name
# ===========================================================================

class TestNormalizeName(unittest.TestCase):

    def test_lowercase_and_strip_special(self):
        self.assertEqual(normalize_name("UserID"), "userid")

    def test_trailing_s_stripped(self):
        self.assertEqual(normalize_name("orders"), "order")

    def test_short_word_keeps_trailing_s(self):
        # words of length <= 3 after cleaning should not be stripped
        result = normalize_name("us")
        self.assertEqual(result, "us")

    def test_empty_string(self):
        self.assertEqual(normalize_name(""), "")

    def test_numbers_preserved(self):
        self.assertEqual(normalize_name("item2"), "item2")


class TestTokenizeName(unittest.TestCase):

    def test_camel_case_split(self):
        tokens = tokenize_name("orderId")
        self.assertIn("id", tokens)

    def test_snake_case_split(self):
        tokens = tokenize_name("order_id")
        self.assertIn("id", tokens)

    def test_single_word(self):
        tokens = tokenize_name("name")
        self.assertIn("name", tokens)


# ===========================================================================
# normalize_schema
# ===========================================================================

class TestNormalizeSchema(unittest.TestCase):

    def test_none_returns_unknown(self):
        result = normalize_schema(None)
        self.assertEqual(result["type"], "unknown")

    def test_primitive_passthrough(self):
        result = normalize_schema({"type": "string"})
        self.assertEqual(result["type"], "string")

    def test_object_adds_required(self):
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
        }
        result = normalize_schema(schema)
        self.assertIn("a", result["required"])
        self.assertIn("b", result["required"])

    def test_array_normalizes_items(self):
        schema = {"type": "array", "items": {"type": "integer"}}
        result = normalize_schema(schema)
        self.assertEqual(result["type"], "array")
        self.assertEqual(result["items"]["type"], "integer")

    def test_xml_root_wrapper_unwrapped(self):
        schema = {
            "root": "record",
            "schema": {"type": "object", "properties": {"id": {"type": "integer"}}},
        }
        result = normalize_schema(schema)
        self.assertEqual(result.get("xml_root"), "record")
        self.assertEqual(result["type"], "object")

    def test_attributes_prefixed_with_at(self):
        schema = {
            "type": "object",
            "attributes": {"lang": {"type": "string"}},
            "properties": {},
        }
        result = normalize_schema(schema)
        self.assertIn("@lang", result["properties"])


# ===========================================================================
# primitive_relation
# ===========================================================================

class TestPrimitiveRelation(unittest.TestCase):

    def test_same_type_is_direct(self):
        self.assertEqual(primitive_relation({"type": "string"}, {"type": "string"}), "direct")

    def test_integer_to_number_is_direct(self):
        self.assertEqual(primitive_relation({"type": "integer"}, {"type": "number"}), "direct")

    def test_string_to_integer_is_mapping(self):
        self.assertEqual(primitive_relation({"type": "string"}, {"type": "integer"}), "mapping")

    def test_integer_to_boolean_is_mapping(self):
        self.assertEqual(primitive_relation({"type": "integer"}, {"type": "boolean"}), "mapping")

    def test_string_to_object_is_incompatible(self):
        self.assertEqual(primitive_relation({"type": "string"}, {"type": "object"}), "incompatible")

    def test_null_to_string_is_mapping(self):
        self.assertEqual(primitive_relation({"type": "null"}, {"type": "string"}), "mapping")


# ===========================================================================
# compare_schemas - compatibility labels
# ===========================================================================

class TestCompareSchemas(unittest.TestCase):

    # --- direct compatibility ---

    def test_identical_flat_objects(self):
        schema = make_object({"id": make_field("integer"), "name": make_field("string")})
        result = compare_schemas(schema, schema, "A", "B")
        self.assertEqual(result["compatibility"], DIRECT)

    def test_identical_primitives(self):
        schema = make_field("string")
        result = compare_schemas(schema, schema, "A", "B")
        self.assertEqual(result["compatibility"], DIRECT)

    def test_integer_source_number_target(self):
        source = make_field("integer")
        target = make_field("number")
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], DIRECT)

    def test_extra_source_fields_still_direct(self):
        source = make_object({
            "id": make_field("integer"),
            "name": make_field("string"),
            "extra": make_field("boolean"),
        })
        target = make_object({
            "id": make_field("integer"),
            "name": make_field("string"),
        })
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], DIRECT)

    # --- compatible with mapping ---

    def test_renamed_field_requires_mapping(self):
        source = make_object({"userId": make_field("integer")})
        target = make_object({"user_id": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], MAPPING)

    def test_type_cast_required(self):
        source = make_object({"count": make_field("string")})
        target = make_object({"count": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], MAPPING)

    def test_optional_field_missing_is_mapping_or_direct(self):
        source = make_object({"id": make_field("integer")}, required=["id"])
        target = make_object(
            {"id": make_field("integer"), "label": make_field("string")},
            required=["id"],
        )
        result = compare_schemas(source, target, "A", "B")
        self.assertIn(result["compatibility"], [DIRECT, MAPPING])

    def test_singleton_wrapped_to_array(self):
        source = make_field("string")
        target = {"type": "array", "items": make_field("string")}
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], MAPPING)

    def test_array_to_object_requires_mapping(self):
        source = {"type": "array", "items": make_object({"id": make_field("integer")})}
        target = make_object({"id": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], MAPPING)

    # --- incompatible ---

    def test_string_vs_object_is_incompatible(self):
        source = make_field("string")
        target = make_object({"id": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], INCOMPATIBLE)

    def test_missing_required_field_is_incompatible(self):
        source = make_object({"name": make_field("string")})
        target = make_object({"id": make_field("integer"), "name": make_field("string")}, required=["id", "name"])
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], INCOMPATIBLE)

    def test_disjoint_enum_values_incompatible(self):
        source = make_field("string")
        source["enum"] = ["a", "b"]
        target = make_field("string")
        target["enum"] = ["x", "y"]
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], INCOMPATIBLE)

    def test_overlapping_enum_requires_mapping(self):
        source = make_field("string")
        source["enum"] = ["a", "b", "c"]
        target = make_field("string")
        target["enum"] = ["a", "b"]
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], MAPPING)

    def test_nested_type_mismatch_is_incompatible(self):
        source = make_object({"payload": make_field("boolean")})
        target = make_object({"payload": make_object({"id": make_field("integer")})})
        result = compare_schemas(source, target, "A", "B")
        self.assertEqual(result["compatibility"], INCOMPATIBLE)


# ===========================================================================
# compare_schemas - issue codes
# ===========================================================================

class TestIssueCodes(unittest.TestCase):

    def _issue_codes(self, result):
        return {issue["code"] for issue in result["issues"]}

    def test_missing_required_field_code(self):
        source = make_object({"name": make_field("string")})
        target = make_object({"id": make_field("integer"), "name": make_field("string")}, required=["id", "name"])
        result = compare_schemas(source, target, "A", "B")
        self.assertIn("missing_required_field", self._issue_codes(result))

    def test_missing_optional_field_code(self):
        source = make_object({"id": make_field("integer")}, required=["id"])
        target = make_object(
            {"id": make_field("integer"), "tag": make_field("string")},
            required=["id"],
        )
        result = compare_schemas(source, target, "A", "B")
        self.assertIn("missing_optional_field", self._issue_codes(result))

    def test_type_mismatch_code(self):
        source = make_field("string")
        target = make_field("boolean")
        result = compare_schemas(source, target, "A", "B")
        # string -> boolean is a castable pair, expect type_conversion_required
        self.assertIn("type_conversion_required", self._issue_codes(result))

    def test_extra_source_field_code(self):
        source = make_object({"id": make_field("integer"), "surplus": make_field("string")})
        target = make_object({"id": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        self.assertIn("extra_source_field", self._issue_codes(result))

    def test_field_mapping_required_code(self):
        source = make_object({"userId": make_field("integer")})
        target = make_object({"user_id": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        self.assertIn("field_mapping_required", self._issue_codes(result))

    def test_enum_mismatch_code(self):
        source = make_field("string")
        source["enum"] = ["foo"]
        target = make_field("string")
        target["enum"] = ["bar"]
        result = compare_schemas(source, target, "A", "B")
        self.assertIn("enum_mismatch", self._issue_codes(result))

    def test_singleton_array_mapping_code(self):
        source = make_field("integer")
        target = {"type": "array", "items": make_field("integer")}
        result = compare_schemas(source, target, "A", "B")
        self.assertIn("singleton_array_mapping", self._issue_codes(result))


# ===========================================================================
# build_index
# ===========================================================================

class TestBuildIndex(unittest.TestCase):

    def test_flat_object_produces_entries(self):
        schema = normalize_schema(make_object({
            "id": make_field("integer"),
            "name": make_field("string"),
        }))
        index = build_index(schema)
        paths = {e.path for e in index}
        self.assertIn("id", paths)
        self.assertIn("name", paths)

    def test_nested_object_paths(self):
        schema = normalize_schema(make_object({
            "user": make_object({"id": make_field("integer")}),
        }))
        index = build_index(schema)
        paths = {e.path for e in index}
        self.assertIn("user.id", paths)

    def test_array_items_path(self):
        schema = normalize_schema({
            "type": "array",
            "items": make_object({"id": make_field("integer")}),
        })
        index = build_index(schema)
        paths = {e.path for e in index}
        self.assertTrue(any("id" in p for p in paths))


# ===========================================================================
# classify_issues
# ===========================================================================

class TestClassifyIssues(unittest.TestCase):

    def test_no_issues_is_direct(self):
        self.assertEqual(classify_issues([]), DIRECT)

    def test_only_mapping_issues(self):
        issues = [{"kind": "mapping"}, {"kind": "info"}]
        self.assertEqual(classify_issues(issues), MAPPING)

    def test_any_blocking_is_incompatible(self):
        issues = [{"kind": "mapping"}, {"kind": "blocking"}]
        self.assertEqual(classify_issues(issues), INCOMPATIBLE)

    def test_only_info_is_direct(self):
        issues = [{"kind": "info"}]
        self.assertEqual(classify_issues(issues), DIRECT)


# ===========================================================================
# infer_schema (JSON)
# ===========================================================================

class TestInferSchema(unittest.TestCase):

    def test_dict_produces_object(self):
        result = infer_schema({"id": 1, "name": "test"})
        self.assertEqual(result["type"], "object")
        self.assertIn("id", result["properties"])
        self.assertIn("name", result["properties"])

    def test_list_produces_array(self):
        result = infer_schema([{"id": 1}])
        self.assertEqual(result["type"], "array")
        self.assertEqual(result["items"]["type"], "object")

    def test_empty_list_produces_unknown_items(self):
        result = infer_schema([])
        self.assertEqual(result["type"], "array")
        self.assertEqual(result["items"]["type"], "unknown")

    def test_bool_before_int(self):
        result = infer_schema(True)
        self.assertEqual(result["type"], "boolean")

    def test_integer(self):
        self.assertEqual(infer_schema(42)["type"], "integer")

    def test_float(self):
        self.assertEqual(infer_schema(3.14)["type"], "number")

    def test_string(self):
        self.assertEqual(infer_schema("hello")["type"], "string")

    def test_none(self):
        self.assertEqual(infer_schema(None)["type"], "null")

    def test_nested_dict(self):
        result = infer_schema({"user": {"id": 1}})
        self.assertEqual(result["properties"]["user"]["type"], "object")


# ===========================================================================
# infer_type (XML)
# ===========================================================================

class TestInferTypeXML(unittest.TestCase):

    def test_integer_string(self):
        self.assertEqual(infer_type("42"), "integer")

    def test_float_string(self):
        self.assertEqual(infer_type("3.14"), "number")

    def test_boolean_true(self):
        self.assertEqual(infer_type("true"), "boolean")

    def test_boolean_false(self):
        self.assertEqual(infer_type("False"), "boolean")

    def test_plain_string(self):
        self.assertEqual(infer_type("hello"), "string")

    def test_empty_string(self):
        self.assertEqual(infer_type(""), "string")

    def test_none_value(self):
        self.assertEqual(infer_type(None), "string")


# ===========================================================================
# extract_schema_from_xml
# ===========================================================================

class TestExtractSchemaFromXML(unittest.TestCase):

    def test_simple_element(self):
        xml = "<root><id>1</id><name>Alice</name></root>"
        result = extract_schema_from_xml(xml)
        self.assertEqual(result["root"], "root")
        schema = result["schema"]
        self.assertIn("id", schema["properties"])
        self.assertIn("name", schema["properties"])

    def test_repeated_children_become_array(self):
        xml = "<root><item>a</item><item>b</item></root>"
        result = extract_schema_from_xml(xml)
        schema = result["schema"]
        self.assertEqual(schema["properties"]["item"]["type"], "array")

    def test_leaf_text_type_inferred(self):
        xml = "<root><count>5</count></root>"
        result = extract_schema_from_xml(xml)
        count_schema = result["schema"]["properties"]["count"]
        self.assertEqual(count_schema["type"], "integer")

    def test_attributes_captured(self):
        xml = '<root lang="en"><title>Hello</title></root>'
        result = extract_schema_from_xml(xml)
        schema = result["schema"]
        self.assertIn("@lang", schema.get("properties", {}))

    def test_nested_structure(self):
        xml = "<root><user><id>1</id></user></root>"
        result = extract_schema_from_xml(xml)
        user_schema = result["schema"]["properties"]["user"]
        self.assertEqual(user_schema["type"], "object")
        self.assertIn("id", user_schema["properties"])


# ===========================================================================
# build_mapping
# ===========================================================================

class TestBuildMapping(unittest.TestCase):

    def test_direct_match_produces_direct_fields(self):
        schema = make_object({"id": make_field("integer"), "name": make_field("string")})
        result = compare_schemas(schema, schema, "A", "B")
        mapping = build_mapping(result)
        transforms = {f.transform for f in mapping.fields}
        self.assertIn("direct", transforms)

    def test_renamed_field_produces_rename_or_cast(self):
        source = make_object({"userId": make_field("integer")})
        target = make_object({"user_id": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        mapping = build_mapping(result)
        transforms = {f.transform for f in mapping.fields}
        self.assertTrue(transforms & {"rename", "cast"})

    def test_status_full_when_direct(self):
        schema = make_object({"id": make_field("integer")})
        result = compare_schemas(schema, schema, "A", "B")
        mapping = build_mapping(result)
        self.assertEqual(mapping.status, "full")

    def test_status_partial_when_mapping(self):
        source = make_object({"userId": make_field("integer")})
        target = make_object({"user_id": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        mapping = build_mapping(result)
        self.assertEqual(mapping.status, "partial")

    def test_status_incompatible_when_blocking(self):
        source = make_field("string")
        target = make_object({"id": make_field("integer")})
        result = compare_schemas(source, target, "A", "B")
        mapping = build_mapping(result)
        self.assertEqual(mapping.status, "incompatible")

    def test_missing_required_field_produces_missing_transform(self):
        source = make_object({"name": make_field("string")})
        target = make_object(
            {"id": make_field("integer"), "name": make_field("string")},
            required=["id", "name"],
        )
        result = compare_schemas(source, target, "A", "B")
        mapping = build_mapping(result)
        transforms = {f.transform for f in mapping.fields}
        self.assertIn("missing", transforms)

    def test_to_dict_structure(self):
        schema = make_object({"id": make_field("integer")})
        result = compare_schemas(schema, schema, "A", "B")
        mapping = build_mapping(result)
        d = mapping.to_dict()
        self.assertIn("fields", d)
        self.assertIn("status", d)
        self.assertIn("source", d)
        self.assertIn("target", d)


# ===========================================================================
# build_transformer / generate_transform_code
# ===========================================================================

class TestBuildTransformer(unittest.TestCase):

    def test_direct_transform_passthrough(self):
        schema = make_object({"id": make_field("integer"), "name": make_field("string")})
        result = compare_schemas(schema, schema, "A", "B")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn({"id": 1, "name": "Alice"})
        self.assertEqual(output["id"], 1)
        self.assertEqual(output["name"], "Alice")

    def test_rename_transform(self):
        source_schema = make_object({"userId": make_field("integer")})
        target_schema = make_object({"user_id": make_field("integer")})
        result = compare_schemas(source_schema, target_schema, "A", "B")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn({"userId": 99})
        self.assertEqual(output.get("user_id"), 99)

    def test_cast_string_to_integer(self):
        source_schema = make_object({"count": make_field("string")})
        target_schema = make_object({"count": make_field("integer")})
        result = compare_schemas(source_schema, target_schema, "A", "B")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn({"count": "42"})
        self.assertEqual(output.get("count"), 42)

    def test_wrap_to_array(self):
        source_schema = make_field("string")
        target_schema = {"type": "array", "items": make_field("string")}
        result = compare_schemas(source_schema, target_schema, "A", "B")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn("hello")
        self.assertIsInstance(output, dict)

    def test_generate_transform_code_contains_function_def(self):
        schema = make_object({"id": make_field("integer")})
        result = compare_schemas(schema, schema, "A", "B")
        mapping = build_mapping(result)
        code = generate_transform_code(mapping)
        self.assertIn("def transform_", code)
        self.assertIn("return target", code)

    def test_nested_object_transform(self):
        schema = make_object({
            "user": make_object({
                "id": make_field("integer"),
                "name": make_field("string"),
            })
        })
        result = compare_schemas(schema, schema, "A", "B")
        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        source_doc = {"user": {"id": 5, "name": "Bob"}}
        output = fn(source_doc)
        self.assertEqual(output.get("user", {}).get("id"), 5)


# ===========================================================================
# Cross-module: JSON schema -> compare -> mapping -> transform round-trip
# ===========================================================================

class TestEndToEndRoundTrip(unittest.TestCase):

    def test_inferred_schema_compare_and_transform(self):
        source_doc = {"id": 1, "label": "alpha"}
        target_doc = {"id": 1, "label": "alpha"}

        source_schema = infer_schema(source_doc)
        target_schema = infer_schema(target_doc)

        result = compare_schemas(source_schema, target_schema, "Source", "Target")
        self.assertEqual(result["compatibility"], DIRECT)

        mapping = build_mapping(result)
        fn = build_transformer(mapping)
        output = fn(source_doc)
        self.assertEqual(output["id"], 1)
        self.assertEqual(output["label"], "alpha")

    def test_xml_schema_compare(self):
        xml = "<record><id>10</id><title>Test</title></record>"
        xml_schema = extract_schema_from_xml(xml)

        json_schema = infer_schema({"id": 10, "title": "Test"})

        result = compare_schemas(xml_schema, json_schema, "XML", "JSON")
        self.assertIn(result["compatibility"], [DIRECT, MAPPING])

    def test_summary_counts_match_issues(self):
        source = make_object({"a": make_field("string"), "b": make_field("integer")})
        target = make_object({"a": make_field("string"), "b": make_field("integer"), "c": make_field("boolean")}, required=["a", "b", "c"])
        result = compare_schemas(source, target, "S", "T")
        summary = result["summary"]
        total = (
            summary["blocking_issues"]
            + summary["mapping_issues"]
            + summary["informational_issues"]
        )
        self.assertEqual(total, summary["issue_count"])

if __name__ == "__main__":
    unittest.main()