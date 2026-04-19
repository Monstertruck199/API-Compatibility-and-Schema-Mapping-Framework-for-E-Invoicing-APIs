"""
test_db.py
----------
Unit tests for the database layer (db.py).

Requires a running Postgres instance matching DB_CONFIG, or override via
environment variables:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

Run with:
    pytest test_db.py -v
"""

import unittest
import psycopg2
import psycopg2.extras

from db import (
    get_connection,
    create_api,
    get_api,
    get_api_by_name,
    list_apis,
    delete_api,
    store_schema,
    get_schema,
    get_schemas_for_api,
    get_latest_schema,
    get_fields_for_schema,
    store_compatibility_result,
    get_compatibility_result,
    list_compatibility_results,
    store_mapping_rule,
    store_mapping_rules_bulk,
    get_mapping_rules,
    delete_mapping_rules,
    get_compatibility_matrix,
    store_transform_run,
    list_transform_runs,
    get_transform_run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_raw_schema(fields=None):
    """Return a minimal JSON schema object with the given field names (all strings)."""
    fields = fields or {"id": "integer", "name": "string"}
    return {
        "type": "object",
        "properties": {k: {"type": v} for k, v in fields.items()},
        "required": list(fields.keys()),
    }


def make_compat_result(compatibility="directly_compatible", issues=None):
    """Return a minimal compatibility result dict as produced by compare_schemas."""
    issues = issues or []
    return {
        "compatibility": compatibility,
        "summary": {
            "compatibility_label": compatibility,
            "blocking_issues": sum(1 for i in issues if i.get("kind") == "blocking"),
            "mapping_issues": sum(1 for i in issues if i.get("kind") == "mapping"),
            "informational_issues": sum(1 for i in issues if i.get("kind") == "info"),
            "issue_count": len(issues),
        },
        "issues": issues,
    }


def make_issue(code="missing_required_field", kind="blocking", severity="error",
               message="A required field is missing.", source_path=None,
               target_path=None, suggestion=None):
    return {
        "code": code,
        "kind": kind,
        "severity": severity,
        "source_path": source_path,
        "target_path": target_path,
        "message": message,
        "suggestion": suggestion,
    }


# ---------------------------------------------------------------------------
# Base class: creates and tears down test data per test
# ---------------------------------------------------------------------------

class DBTestCase(unittest.TestCase):
    """
    Base class that opens one connection for setUp/tearDown cleanup.
    Each test creates its own data via the public db functions; tearDown
    removes any apis rows created during the test (cascades handle the rest).
    """

    def setUp(self):
        self.conn = get_connection()
        self._created_api_ids = []

    def tearDown(self):
        if self._created_api_ids:
            with self.conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(self._created_api_ids))
                cur.execute(
                    f"DELETE FROM apis WHERE id IN ({placeholders})",
                    self._created_api_ids,
                )
            self.conn.commit()
        self.conn.close()

    # -- convenience factory so tests can track what they create --

    def create_api(self, name, category="transformation", **kwargs):
        api = create_api(name, category, **kwargs)
        self._created_api_ids.append(api["id"])
        return api

    def create_api_with_schema(self, name, fields=None, direction="input", fmt="json"):
        api = self.create_api(name)
        schema = store_schema(api["id"], direction, fmt, make_raw_schema(fields))
        return api, schema


# ===========================================================================
# create_api / get_api / get_api_by_name
# ===========================================================================

class TestCreateApi(DBTestCase):

    def test_returns_dict_with_id(self):
        api = self.create_api("TestAPI_create")
        self.assertIn("id", api)
        self.assertIsInstance(api["id"], int)

    def test_name_and_category_stored(self):
        api = self.create_api("TestAPI_fields", category="validation")
        self.assertEqual(api["name"], "TestAPI_fields")
        self.assertEqual(api["category"], "validation")

    def test_optional_fields_stored(self):
        api = self.create_api(
            "TestAPI_optional",
            description="A test API",
            base_url="https://example.com",
            auth_method="bearer",
        )
        self.assertEqual(api["description"], "A test API")
        self.assertEqual(api["base_url"], "https://example.com")
        self.assertEqual(api["auth_method"], "bearer")

    def test_optional_fields_default_to_none(self):
        api = self.create_api("TestAPI_defaults")
        self.assertIsNone(api["description"])
        self.assertIsNone(api["base_url"])
        self.assertIsNone(api["auth_method"])

    def test_upsert_on_duplicate_name(self):
        api1 = self.create_api("TestAPI_upsert", category="transformation")
        api2 = self.create_api("TestAPI_upsert", category="validation")
        self.assertEqual(api1["id"], api2["id"])
        self.assertEqual(api2["category"], "validation")

    def test_invalid_category_raises(self):
        with self.assertRaises(Exception):
            create_api("TestAPI_bad_cat", "nonexistent_category")


class TestGetApi(DBTestCase):

    def test_get_existing_api(self):
        created = self.create_api("TestAPI_get")
        fetched = get_api(created["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["id"], created["id"])
        self.assertEqual(fetched["name"], "TestAPI_get")

    def test_get_nonexistent_api_returns_none(self):
        result = get_api(999999999)
        self.assertIsNone(result)

    def test_get_api_by_name(self):
        created = self.create_api("TestAPI_byname")
        fetched = get_api_by_name("TestAPI_byname")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["id"], created["id"])

    def test_get_api_by_name_missing_returns_none(self):
        result = get_api_by_name("__no_such_api__")
        self.assertIsNone(result)


class TestListApis(DBTestCase):

    def test_list_includes_created_apis(self):
        self.create_api("TestAPI_list_A")
        self.create_api("TestAPI_list_B")
        apis = list_apis()
        names = {a["name"] for a in apis}
        self.assertIn("TestAPI_list_A", names)
        self.assertIn("TestAPI_list_B", names)

    def test_list_returns_list_of_dicts(self):
        self.create_api("TestAPI_list_type")
        apis = list_apis()
        self.assertIsInstance(apis, list)
        self.assertIsInstance(apis[0], dict)

    def test_list_ordered_by_name(self):
        self.create_api("ZZZ_TestAPI")
        self.create_api("AAA_TestAPI")
        apis = list_apis()
        names = [a["name"] for a in apis if a["name"] in ("ZZZ_TestAPI", "AAA_TestAPI")]
        self.assertEqual(names, sorted(names))


# ===========================================================================
# delete_api
# ===========================================================================

class TestDeleteApi(DBTestCase):

    def test_delete_existing_returns_true(self):
        api = self.create_api("TestAPI_del")
        # Remove from tracking so tearDown doesn't double-delete
        self._created_api_ids.remove(api["id"])
        result = delete_api(api["id"])
        self.assertTrue(result)

    def test_delete_nonexistent_returns_false(self):
        result = delete_api(999999999)
        self.assertFalse(result)

    def test_deleted_api_not_retrievable(self):
        api = self.create_api("TestAPI_del_check")
        self._created_api_ids.remove(api["id"])
        delete_api(api["id"])
        self.assertIsNone(get_api(api["id"]))

    def test_delete_cascades_to_schemas(self):
        api, schema = self.create_api_with_schema("TestAPI_cascade_schema")
        self._created_api_ids.remove(api["id"])
        delete_api(api["id"])
        self.assertIsNone(get_schema(schema["id"]))


# ===========================================================================
# store_schema / get_schema / get_schemas_for_api / get_latest_schema
# ===========================================================================

class TestStoreSchema(DBTestCase):

    def test_returns_dict_with_id(self):
        api = self.create_api("TestAPI_schema_store")
        schema = store_schema(api["id"], "input", "json", make_raw_schema())
        self.assertIn("id", schema)
        self.assertIsInstance(schema["id"], int)

    def test_direction_and_format_stored(self):
        api = self.create_api("TestAPI_schema_dir")
        schema = store_schema(api["id"], "output", "xml", make_raw_schema())
        fetched = get_schema(schema["id"])
        self.assertEqual(fetched["direction"], "output")
        self.assertEqual(fetched["format"], "xml")

    def test_version_increments_on_second_store(self):
        api = self.create_api("TestAPI_schema_ver")
        s1 = store_schema(api["id"], "input", "json", make_raw_schema())
        s2 = store_schema(api["id"], "input", "json", make_raw_schema({"x": "string"}))
        self.assertEqual(s1["version"], 1)
        self.assertEqual(s2["version"], 2)

    def test_input_and_output_versions_independent(self):
        api = self.create_api("TestAPI_schema_inout")
        store_schema(api["id"], "input", "json", make_raw_schema())
        store_schema(api["id"], "input", "json", make_raw_schema())
        out = store_schema(api["id"], "output", "json", make_raw_schema())
        self.assertEqual(out["version"], 1)

    def test_invalid_direction_raises(self):
        api = self.create_api("TestAPI_schema_bad_dir")
        with self.assertRaises(Exception):
            store_schema(api["id"], "sideways", "json", make_raw_schema())

    def test_invalid_format_raises(self):
        api = self.create_api("TestAPI_schema_bad_fmt")
        with self.assertRaises(Exception):
            store_schema(api["id"], "input", "csv", make_raw_schema())


class TestGetSchema(DBTestCase):

    def test_get_existing_schema(self):
        api, schema = self.create_api_with_schema("TestAPI_get_schema")
        fetched = get_schema(schema["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["id"], schema["id"])

    def test_get_nonexistent_schema_returns_none(self):
        self.assertIsNone(get_schema(999999999))

    def test_get_schemas_for_api_returns_all(self):
        api = self.create_api("TestAPI_schemas_for_api")
        store_schema(api["id"], "input", "json", make_raw_schema())
        store_schema(api["id"], "output", "json", make_raw_schema())
        schemas = get_schemas_for_api(api["id"])
        self.assertEqual(len(schemas), 2)

    def test_get_schemas_for_api_empty(self):
        api = self.create_api("TestAPI_schemas_empty")
        schemas = get_schemas_for_api(api["id"])
        self.assertEqual(schemas, [])

    def test_get_latest_schema_returns_highest_version(self):
        api = self.create_api("TestAPI_latest_schema")
        store_schema(api["id"], "input", "json", make_raw_schema())
        store_schema(api["id"], "input", "json", make_raw_schema({"x": "string"}))
        latest = get_latest_schema(api["id"], "input")
        self.assertEqual(latest["version"], 2)

    def test_get_latest_schema_missing_returns_none(self):
        api = self.create_api("TestAPI_latest_none")
        result = get_latest_schema(api["id"], "output")
        self.assertIsNone(result)


# ===========================================================================
# get_fields_for_schema / _store_fields (via store_schema)
# ===========================================================================

class TestSchemaFields(DBTestCase):

    def test_flat_object_fields_stored(self):
        api = self.create_api("TestAPI_fields_flat")
        schema = store_schema(api["id"], "input", "json", make_raw_schema({"id": "integer", "name": "string"}))
        fields = get_fields_for_schema(schema["id"])
        paths = {f["field_path"] for f in fields}
        self.assertIn("id", paths)
        self.assertIn("name", paths)

    def test_field_type_stored_correctly(self):
        api = self.create_api("TestAPI_fields_type")
        schema = store_schema(api["id"], "input", "json", make_raw_schema({"count": "integer"}))
        fields = get_fields_for_schema(schema["id"])
        count_field = next(f for f in fields if f["field_name"] == "count")
        self.assertEqual(count_field["field_type"], "integer")

    def test_required_flag_set(self):
        api = self.create_api("TestAPI_fields_required")
        raw = {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "tag": {"type": "string"}},
            "required": ["id"],
        }
        schema = store_schema(api["id"], "input", "json", raw)
        fields = {f["field_name"]: f for f in get_fields_for_schema(schema["id"])}
        self.assertTrue(fields["id"]["is_required"])
        self.assertFalse(fields["tag"]["is_required"])

    def test_nested_object_fields_stored_with_path(self):
        api = self.create_api("TestAPI_fields_nested")
        raw = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}},
                    "required": ["id"],
                }
            },
            "required": ["user"],
        }
        schema = store_schema(api["id"], "input", "json", raw)
        fields = get_fields_for_schema(schema["id"])
        paths = {f["field_path"] for f in fields}
        self.assertIn("user.id", paths)

    def test_nesting_depth_increments(self):
        api = self.create_api("TestAPI_fields_depth")
        raw = {
            "type": "object",
            "properties": {
                "outer": {
                    "type": "object",
                    "properties": {"inner": {"type": "string"}},
                }
            },
        }
        schema = store_schema(api["id"], "input", "json", raw)
        fields = {f["field_path"]: f for f in get_fields_for_schema(schema["id"])}
        self.assertEqual(fields["outer"]["nesting_depth"], 0)
        self.assertEqual(fields["outer.inner"]["nesting_depth"], 1)

    def test_fields_cascade_deleted_with_schema(self):
        api, schema = self.create_api_with_schema("TestAPI_fields_cascade")
        schema_id = schema["id"]
        self._created_api_ids.remove(api["id"])
        delete_api(api["id"])
        fields = get_fields_for_schema(schema_id)
        self.assertEqual(fields, [])

    def test_no_fields_for_unknown_schema(self):
        fields = get_fields_for_schema(999999999)
        self.assertEqual(fields, [])


# ===========================================================================
# store_compatibility_result / get_compatibility_result / list_compatibility_results
# ===========================================================================
 
class TestCompatibilityResult(DBTestCase):
 
    def _setup_two_apis_with_schemas(self, name_a="TestAPI_compat_A", name_b="TestAPI_compat_B"):
        api_a, schema_a = self.create_api_with_schema(name_a)
        api_b, schema_b = self.create_api_with_schema(name_b)
        return api_a, schema_a, api_b, schema_b
 
    def test_store_returns_dict_with_id(self):
        api_a, schema_a, api_b, schema_b = self._setup_two_apis_with_schemas(
            "TestAPI_compat_ret_A", "TestAPI_compat_ret_B"
        )
        result = store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("directly_compatible"),
        )
        self.assertIn("id", result)
        self.assertIsInstance(result["id"], int)
 
    def test_compatibility_level_stored(self):
        api_a, schema_a, api_b, schema_b = self._setup_two_apis_with_schemas(
            "TestAPI_compat_lvl_A", "TestAPI_compat_lvl_B"
        )
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("incompatible"),
        )
        fetched = get_compatibility_result(schema_a["id"], schema_b["id"])
        self.assertEqual(fetched["compatibility_level"], "incompatible")
 
    def test_issues_stored_and_retrieved(self):
        api_a, schema_a, api_b, schema_b = self._setup_two_apis_with_schemas(
            "TestAPI_compat_iss_A", "TestAPI_compat_iss_B"
        )
        issue = make_issue(code="missing_required_field", kind="blocking", severity="error",
                           message="Field id missing.")
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("incompatible", issues=[issue]),
        )
        fetched = get_compatibility_result(schema_a["id"], schema_b["id"])
        self.assertEqual(len(fetched["issues"]), 1)
        self.assertEqual(fetched["issues"][0]["code"], "missing_required_field")
 
    def test_upsert_replaces_previous_result(self):
        api_a, schema_a, api_b, schema_b = self._setup_two_apis_with_schemas(
            "TestAPI_compat_upsert_A", "TestAPI_compat_upsert_B"
        )
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("directly_compatible"),
        )
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("incompatible"),
        )
        fetched = get_compatibility_result(schema_a["id"], schema_b["id"])
        self.assertEqual(fetched["compatibility_level"], "incompatible")
 
    def test_upsert_replaces_old_issues(self):
        api_a, schema_a, api_b, schema_b = self._setup_two_apis_with_schemas(
            "TestAPI_compat_iss_upsert_A", "TestAPI_compat_iss_upsert_B"
        )
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("incompatible", issues=[make_issue()]),
        )
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("directly_compatible", issues=[]),
        )
        fetched = get_compatibility_result(schema_a["id"], schema_b["id"])
        self.assertEqual(fetched["issues"], [])
 
    def test_get_nonexistent_returns_none(self):
        result = get_compatibility_result(999999998, 999999999)
        self.assertIsNone(result)
 
    def test_list_all_includes_stored_result(self):
        api_a, schema_a, api_b, schema_b = self._setup_two_apis_with_schemas(
            "TestAPI_compat_list_A", "TestAPI_compat_list_B"
        )
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("compatible_with_mapping"),
        )
        results = list_compatibility_results()
        levels = {r["compatibility_level"] for r in results}
        self.assertIn("compatible_with_mapping", levels)
 
    def test_list_filtered_by_api_id(self):
        api_a, schema_a, api_b, schema_b = self._setup_two_apis_with_schemas(
            "TestAPI_compat_filt_A", "TestAPI_compat_filt_B"
        )
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("directly_compatible"),
        )
        results = list_compatibility_results(api_id=api_a["id"])
        api_ids_seen = {r["source_api_id"] for r in results} | {r["target_api_id"] for r in results}
        self.assertIn(api_a["id"], api_ids_seen)
 
    def test_invalid_compatibility_level_raises(self):
        api_a, schema_a, api_b, schema_b = self._setup_two_apis_with_schemas(
            "TestAPI_compat_inv_A", "TestAPI_compat_inv_B"
        )
        bad_result = make_compat_result("directly_compatible")
        bad_result["compatibility"] = "totally_fine"
        with self.assertRaises(Exception):
            store_compatibility_result(
                api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
                bad_result,
            )


# ===========================================================================
# store_mapping_rule / store_mapping_rules_bulk / get_mapping_rules / delete_mapping_rules
# ===========================================================================
 
class TestMappingRules(DBTestCase):
 
    def test_store_single_rule_returns_dict(self):
        api_a = self.create_api("TestAPI_map_single_A")
        api_b = self.create_api("TestAPI_map_single_B")
        rule = store_mapping_rule(api_a["id"], api_b["id"], "userId", "user_id")
        self.assertIn("id", rule)
        self.assertEqual(rule["source_field"], "userId")
        self.assertEqual(rule["target_field"], "user_id")
 
    def test_default_transform_type_is_rename(self):
        api_a = self.create_api("TestAPI_map_default_A")
        api_b = self.create_api("TestAPI_map_default_B")
        rule = store_mapping_rule(api_a["id"], api_b["id"], "src", "tgt")
        self.assertEqual(rule["transform_type"], "rename")
 
    def test_default_confidence_is_high(self):
        api_a = self.create_api("TestAPI_map_conf_A")
        api_b = self.create_api("TestAPI_map_conf_B")
        rule = store_mapping_rule(api_a["id"], api_b["id"], "src", "tgt")
        self.assertEqual(rule["confidence"], "high")
 
    def test_get_mapping_rules_returns_stored(self):
        api_a = self.create_api("TestAPI_map_get_A")
        api_b = self.create_api("TestAPI_map_get_B")
        store_mapping_rule(api_a["id"], api_b["id"], "a", "b")
        store_mapping_rule(api_a["id"], api_b["id"], "c", "d")
        rules = get_mapping_rules(api_a["id"], api_b["id"])
        self.assertEqual(len(rules), 2)
 
    def test_get_mapping_rules_empty(self):
        api_a = self.create_api("TestAPI_map_empty_A")
        api_b = self.create_api("TestAPI_map_empty_B")
        rules = get_mapping_rules(api_a["id"], api_b["id"])
        self.assertEqual(rules, [])
 
    def test_bulk_replaces_existing_rules(self):
        api_a = self.create_api("TestAPI_map_bulk_A")
        api_b = self.create_api("TestAPI_map_bulk_B")
        store_mapping_rule(api_a["id"], api_b["id"], "old_src", "old_tgt")
        new_rules = [{"source_field": "new_src", "target_field": "new_tgt"}]
        store_mapping_rules_bulk(api_a["id"], api_b["id"], new_rules)
        rules = get_mapping_rules(api_a["id"], api_b["id"])
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["source_field"], "new_src")
 
    def test_bulk_stores_all_rules(self):
        api_a = self.create_api("TestAPI_map_bulkall_A")
        api_b = self.create_api("TestAPI_map_bulkall_B")
        new_rules = [
            {"source_field": "a", "target_field": "x"},
            {"source_field": "b", "target_field": "y"},
            {"source_field": "c", "target_field": "z"},
        ]
        stored = store_mapping_rules_bulk(api_a["id"], api_b["id"], new_rules)
        self.assertEqual(len(stored), 3)
 
    def test_delete_mapping_rules_returns_count(self):
        api_a = self.create_api("TestAPI_map_del_A")
        api_b = self.create_api("TestAPI_map_del_B")
        store_mapping_rule(api_a["id"], api_b["id"], "a", "b")
        store_mapping_rule(api_a["id"], api_b["id"], "c", "d")
        count = delete_mapping_rules(api_a["id"], api_b["id"])
        self.assertEqual(count, 2)
 
    def test_delete_mapping_rules_clears_rules(self):
        api_a = self.create_api("TestAPI_map_delclr_A")
        api_b = self.create_api("TestAPI_map_delclr_B")
        store_mapping_rule(api_a["id"], api_b["id"], "a", "b")
        delete_mapping_rules(api_a["id"], api_b["id"])
        rules = get_mapping_rules(api_a["id"], api_b["id"])
        self.assertEqual(rules, [])
 
    def test_delete_mapping_rules_zero_when_none(self):
        api_a = self.create_api("TestAPI_map_delnone_A")
        api_b = self.create_api("TestAPI_map_delnone_B")
        count = delete_mapping_rules(api_a["id"], api_b["id"])
        self.assertEqual(count, 0)


# ===========================================================================
# get_compatibility_matrix
# ===========================================================================
 
class TestCompatibilityMatrix(DBTestCase):
 
    def test_matrix_contains_created_apis(self):
        api_a = self.create_api("TestAPI_matrix_A")
        api_b = self.create_api("TestAPI_matrix_B")
        result = get_compatibility_matrix(api_ids=[api_a["id"], api_b["id"]])
        names = {a["name"] for a in result["apis"]}
        self.assertIn("TestAPI_matrix_A", names)
        self.assertIn("TestAPI_matrix_B", names)
 
    def test_self_pair_is_same_schema(self):
        api_a = self.create_api("TestAPI_matrix_self")
        result = get_compatibility_matrix(api_ids=[api_a["id"]])
        cell = result["matrix"][0][0]
        self.assertEqual(cell["compatibility"], "same_schema")
 
    def test_unassessed_pair_labelled_not_assessed(self):
        api_a = self.create_api("TestAPI_matrix_unass_A")
        api_b = self.create_api("TestAPI_matrix_unass_B")
        result = get_compatibility_matrix(api_ids=[api_a["id"], api_b["id"]])
        off_diag = [cell for row in result["matrix"] for cell in row
                    if cell["source"] != cell["target"]]
        self.assertTrue(all(c["compatibility"] == "not_assessed" for c in off_diag))
 
    def test_assessed_pair_shows_in_matrix(self):
        api_a, schema_a = self.create_api_with_schema("TestAPI_matrix_ass_A")
        api_b, schema_b = self.create_api_with_schema("TestAPI_matrix_ass_B")
        store_compatibility_result(
            api_a["id"], api_b["id"], schema_a["id"], schema_b["id"],
            make_compat_result("directly_compatible"),
        )
        result = get_compatibility_matrix(api_ids=[api_a["id"], api_b["id"]])
        names_order = [a["name"] for a in result["apis"]]
        a_idx = names_order.index("TestAPI_matrix_ass_A")
        b_idx = names_order.index("TestAPI_matrix_ass_B")
        cell = result["matrix"][a_idx][b_idx]
        self.assertEqual(cell["compatibility"], "directly_compatible")
 
    def test_matrix_structure_has_apis_and_matrix_keys(self):
        result = get_compatibility_matrix(api_ids=[])
        self.assertIn("apis", result)
        self.assertIn("matrix", result)

if __name__ == "__main__":
    unittest.main()
