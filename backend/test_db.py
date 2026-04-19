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


if __name__ == "__main__":
    unittest.main()