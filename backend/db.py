import os
import json
import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME", "api_compatibility"),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASSWORD", "password"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False

def create_api(name, category, description=None, base_url=None, auth_method=None):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO apis (name, category, description, base_url, auth_method)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (name) DO UPDATE
                   SET category = EXCLUDED.category,
                       description = EXCLUDED.description,
                       base_url = EXCLUDED.base_url,
                       auth_method = EXCLUDED.auth_method,
                       updated_at = NOW()
                   RETURNING *""",
                (name, category, description, base_url, auth_method),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        conn.close()

def get_api(api_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM apis WHERE id = %s", (api_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def get_api_by_name(name):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM apis WHERE name = %s", (name,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def list_apis():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM apis ORDER BY name")
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def delete_api(api_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM apis WHERE id = %s RETURNING id", (api_id,))
            deleted = cur.fetchone()
            conn.commit()
            return deleted is not None
    finally:
        conn.close()

def store_schema(api_id, direction, fmt, raw_schema, normalized_schema=None):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS next_ver FROM schemas WHERE api_id = %s AND direction = %s",
                (api_id, direction),
            )
            next_ver = cur.fetchone()["next_ver"]

            cur.execute(
                """INSERT INTO schemas (api_id, direction, format, raw_schema, normalized_schema, version)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (api_id, direction, fmt, json.dumps(raw_schema), json.dumps(normalized_schema) if normalized_schema else None, next_ver),
            )
            row = cur.fetchone()
            schema_id = row["id"]

            _store_fields(cur, schema_id, raw_schema)

            conn.commit()
            return dict(row)
    finally:
        conn.close()

def _store_fields(cur, schema_id, schema, path="$", parent_path=None, depth=0):
    if not isinstance(schema, dict):
        return

    schema_type = schema.get("type", "unknown")

    if schema_type == "object":
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        for name, child in props.items():
            child_path = f"{path}.{name}" if path != "$" else name
            child_type = child.get("type", "unknown") if isinstance(child, dict) else "unknown"
            cur.execute(
                """INSERT INTO schema_fields (schema_id, field_path, field_name, field_type, is_required, nesting_depth, parent_path)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (schema_id, child_path, name, child_type, name in required, depth, parent_path),
            )
            if isinstance(child, dict):
                _store_fields(cur, schema_id, child, child_path, path, depth + 1)
    elif schema_type == "array":
        items = schema.get("items", {})
        if isinstance(items, dict):
            _store_fields(cur, schema_id, items, f"{path}[]", path, depth + 1)

def get_schema(schema_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM schemas WHERE id = %s", (schema_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def get_schemas_for_api(api_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM schemas WHERE api_id = %s ORDER BY direction, version DESC", (api_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_latest_schema(api_id, direction):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM schemas WHERE api_id = %s AND direction = %s ORDER BY version DESC LIMIT 1",
                (api_id, direction),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def get_fields_for_schema(schema_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM schema_fields WHERE schema_id = %s ORDER BY field_path", (schema_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def store_compatibility_result(source_api_id, target_api_id, source_schema_id, target_schema_id, result):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO compatibility_results
                   (source_api_id, target_api_id, source_schema_id, target_schema_id, compatibility_level, summary, full_result)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (source_schema_id, target_schema_id) DO UPDATE
                   SET compatibility_level = EXCLUDED.compatibility_level,
                       summary = EXCLUDED.summary,
                       full_result = EXCLUDED.full_result,
                       created_at = NOW()
                   RETURNING *""",
                (
                    source_api_id,
                    target_api_id,
                    source_schema_id,
                    target_schema_id,
                    result["compatibility"],
                    json.dumps(result["summary"]),
                    json.dumps(result),
                ),
            )
            row = cur.fetchone()
            result_id = row["id"]

            cur.execute("DELETE FROM compatibility_issues WHERE result_id = %s", (result_id,))

            for issue in result.get("issues", []):
                cur.execute(
                    """INSERT INTO compatibility_issues (result_id, code, kind, severity, source_path, target_path, message, suggestion)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        result_id,
                        issue["code"],
                        issue["kind"],
                        issue["severity"],
                        issue.get("source_path"),
                        issue.get("target_path"),
                        issue["message"],
                        issue.get("suggestion"),
                    ),
                )

            conn.commit()
            return dict(row)
    finally:
        conn.close()

def get_compatibility_result(source_schema_id, target_schema_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM compatibility_results WHERE source_schema_id = %s AND target_schema_id = %s",
                (source_schema_id, target_schema_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            cur.execute("SELECT * FROM compatibility_issues WHERE result_id = %s ORDER BY id", (result["id"],))
            result["issues"] = [dict(r) for r in cur.fetchall()]
            return result
    finally:
        conn.close()

def list_compatibility_results(api_id=None):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if api_id:
                cur.execute(
                    """SELECT cr.*, sa.name as source_name, ta.name as target_name
                       FROM compatibility_results cr
                       JOIN apis sa ON cr.source_api_id = sa.id
                       JOIN apis ta ON cr.target_api_id = ta.id
                       WHERE cr.source_api_id = %s OR cr.target_api_id = %s
                       ORDER BY cr.created_at DESC""",
                    (api_id, api_id),
                )
            else:
                cur.execute(
                    """SELECT cr.*, sa.name as source_name, ta.name as target_name
                       FROM compatibility_results cr
                       JOIN apis sa ON cr.source_api_id = sa.id
                       JOIN apis ta ON cr.target_api_id = ta.id
                       ORDER BY cr.created_at DESC"""
                )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def store_mapping_rule(source_api_id, target_api_id, source_field, target_field, transform_type="rename", source_type=None, target_type=None, confidence="high", note=None):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO mapping_rules (source_api_id, target_api_id, source_field, target_field, transform_type, source_type, target_type, confidence, note)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (source_api_id, target_api_id, source_field, target_field, transform_type, source_type, target_type, confidence, note),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        conn.close()

def store_mapping_rules_bulk(source_api_id, target_api_id, rules):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "DELETE FROM mapping_rules WHERE source_api_id = %s AND target_api_id = %s",
                (source_api_id, target_api_id),
            )
            results = []
            for rule in rules:
                cur.execute(
                    """INSERT INTO mapping_rules (source_api_id, target_api_id, source_field, target_field, transform_type, source_type, target_type, confidence, note)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING *""",
                    (
                        source_api_id,
                        target_api_id,
                        rule["source_field"],
                        rule["target_field"],
                        rule.get("transform_type", "rename"),
                        rule.get("source_type"),
                        rule.get("target_type"),
                        rule.get("confidence", "high"),
                        rule.get("note"),
                    ),
                )
                results.append(dict(cur.fetchone()))
            conn.commit()
            return results
    finally:
        conn.close()

def get_mapping_rules(source_api_id, target_api_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM mapping_rules WHERE source_api_id = %s AND target_api_id = %s ORDER BY id",
                (source_api_id, target_api_id),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def delete_mapping_rules(source_api_id, target_api_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM mapping_rules WHERE source_api_id = %s AND target_api_id = %s",
                (source_api_id, target_api_id),
            )
            count = cur.rowcount
            conn.commit()
            return count
    finally:
        conn.close()

def get_compatibility_matrix(api_ids=None):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if api_ids:
                placeholders = ",".join(["%s"] * len(api_ids))
                cur.execute(f"SELECT * FROM apis WHERE id IN ({placeholders}) ORDER BY name", tuple(api_ids))
            else:
                cur.execute("SELECT * FROM apis ORDER BY name")
            apis = [dict(r) for r in cur.fetchall()]

            cur.execute(
                """SELECT cr.source_api_id, cr.target_api_id, cr.compatibility_level, cr.summary
                   FROM compatibility_results cr"""
            )
            results = {}
            for r in cur.fetchall():
                r = dict(r)
                results[(r["source_api_id"], r["target_api_id"])] = r

            matrix = []
            for source in apis:
                row = []
                for target in apis:
                    if source["id"] == target["id"]:
                        row.append({
                            "source": source["name"],
                            "target": target["name"],
                            "compatibility": "same_schema",
                            "summary": {"compatibility_label": "Same schema"},
                        })
                    else:
                        cached = results.get((source["id"], target["id"]))
                        if cached:
                            row.append({
                                "source": source["name"],
                                "target": target["name"],
                                "compatibility": cached["compatibility_level"],
                                "summary": cached["summary"],
                            })
                        else:
                            row.append({
                                "source": source["name"],
                                "target": target["name"],
                                "compatibility": "not_assessed",
                                "summary": {"compatibility_label": "Not assessed"},
                            })
                matrix.append(row)

            return {"apis": [dict(a) for a in apis], "matrix": matrix}
    finally:
        conn.close()

def _serialize_row(row):
    if row is None:
        return None
    import datetime
    result = {}
    for key, value in row.items():
        if isinstance(value, datetime.datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result