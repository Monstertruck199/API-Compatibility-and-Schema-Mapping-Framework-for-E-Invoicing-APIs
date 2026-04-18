from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import requests as http_requests
import datetime

from compatibility_engine import compare_schemas
from extract_JSON_schema import infer_schema
from extract_XML_schema import extract_schema_from_xml
from mapping_engine import build_mapping
from schema_transformer import build_transformer, transform_to_xml

app = Flask(__name__)
CORS(app)

db_available = False
try:
    import db
    db_available = db.init_db()
except Exception:
    db_available = False

def _serialize(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    return obj

def _clean(row):
    if row is None:
        return None
    return {k: _serialize(v) for k, v in row.items()}

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "database": db_available})

@app.route("/api/analyze", methods=["GET"])
def analyze():
    url = request.args.get("url")
    fmt = request.args.get("format", "json").lower()

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    try:
        response = http_requests.get(url, timeout=15)
        response.raise_for_status()
    except http_requests.exceptions.RequestException as error:
        return jsonify({"error": f"Request failed: {error}"}), 400

    try:
        if fmt == "xml":
            schema = extract_schema_from_xml(response.text)
        else:
            schema = infer_schema(response.json())
    except Exception as error:
        return jsonify({"error": f"Could not parse response as {fmt}: {error}"}), 422

    return jsonify({
        "schema": schema,
        "status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
    })

@app.route("/api/compare", methods=["POST"])
def compare():
    payload = request.get_json(silent=True) or {}
    source_schema = payload.get("source_schema")
    target_schema = payload.get("target_schema")
    source_name = payload.get("source_name", "Source")
    target_name = payload.get("target_name", "Target")

    if not source_schema or not target_schema:
        return jsonify({"error": "source_schema and target_schema are required"}), 400

    result = compare_schemas(
        source_schema=source_schema,
        target_schema=target_schema,
        source_name=source_name,
        target_name=target_name,
    )
    return jsonify(result)

@app.route("/api/matrix", methods=["POST"])
def matrix():
    payload = request.get_json(silent=True) or {}
    schemas = payload.get("schemas", [])
    if not schemas:
        return jsonify({"error": "schemas is required"}), 400

    results = []
    for source in schemas:
        row = []
        for target in schemas:
            if source["name"] == target["name"]:
                row.append({
                    "source": source["name"],
                    "target": target["name"],
                    "compatibility": "same_schema",
                    "summary": {"compatibility_label": "Same schema"},
                })
            else:
                row.append(compare_schemas(source["schema"], target["schema"], source["name"], target["name"]))
        results.append(row)

    return jsonify({"matrix": results})

@app.route('/api/transform', methods=['POST'])
def transform():
    data = request.get_json()
    source_schema = data.get('source_schema')
    target_schema = data.get('target_schema')
    source_data = data.get('data')
    output_format = data.get('format', 'json')

    try:
        result = compare_schemas(source_schema, target_schema, 'Source', 'Target')
        mapping = build_mapping(result)
        fn = build_transformer(mapping)

        mapping_status = mapping.status
        warnings = getattr(mapping, 'warnings', [])

        if output_format == 'xml':
            xml = transform_to_xml(fn, source_data, root_tag='record')
            return jsonify({
                'result': xml,
                'format': 'xml',
                'mapping_status': mapping_status,
                'warnings': warnings,
            })

        return jsonify({
            'result': fn(source_data),
            'format': 'json',
            'mapping_status': mapping_status,
            'warnings': warnings,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route("/api/apis", methods=["GET"])
def list_apis():
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    apis = db.list_apis()
    return jsonify([_clean(a) for a in apis])

@app.route("/api/apis", methods=["POST"])
def create_api():
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    category = payload.get("category")
    if not name or not category:
        return jsonify({"error": "name and category are required"}), 400
    if category not in ("transformation", "validation", "communication"):
        return jsonify({"error": "category must be transformation, validation, or communication"}), 400
    api_row = db.create_api(
        name=name,
        category=category,
        description=payload.get("description"),
        base_url=payload.get("base_url"),
        auth_method=payload.get("auth_method"),
    )
    return jsonify(_clean(api_row)), 201

@app.route("/api/apis/<int:api_id>", methods=["GET"])
def get_api(api_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    api_row = db.get_api(api_id)
    if not api_row:
        return jsonify({"error": "API not found"}), 404
    return jsonify(_clean(api_row))

@app.route("/api/apis/<int:api_id>", methods=["DELETE"])
def delete_api(api_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    if db.delete_api(api_id):
        return jsonify({"deleted": True})
    return jsonify({"error": "API not found"}), 404

@app.route("/api/apis/<int:api_id>/schemas", methods=["GET"])
def get_api_schemas(api_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    schemas = db.get_schemas_for_api(api_id)
    return jsonify([_clean(s) for s in schemas])

@app.route("/api/apis/<int:api_id>/schemas", methods=["POST"])
def add_api_schema(api_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    api_row = db.get_api(api_id)
    if not api_row:
        return jsonify({"error": "API not found"}), 404

    payload = request.get_json(silent=True) or {}
    direction = payload.get("direction")
    fmt = payload.get("format", "json")
    raw_schema = payload.get("schema")

    if not direction or direction not in ("input", "output"):
        return jsonify({"error": "direction must be input or output"}), 400
    if not raw_schema:
        return jsonify({"error": "schema is required"}), 400

    from compatibility_engine import normalize_schema
    normalized = normalize_schema(raw_schema)

    schema_row = db.store_schema(api_id, direction, fmt, raw_schema, normalized)
    return jsonify(_clean(schema_row)), 201

@app.route("/api/schemas/<int:schema_id>", methods=["GET"])
def get_schema(schema_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    schema_row = db.get_schema(schema_id)
    if not schema_row:
        return jsonify({"error": "Schema not found"}), 404
    return jsonify(_clean(schema_row))

@app.route("/api/schemas/<int:schema_id>/fields", methods=["GET"])
def get_schema_fields(schema_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    fields = db.get_fields_for_schema(schema_id)
    return jsonify([_clean(f) for f in fields])

@app.route("/api/compatibility/compare", methods=["POST"])
def compare_and_store():
    if not db_available:
        return jsonify({"error": "Database not available"}), 503

    payload = request.get_json(silent=True) or {}
    source_api_id = payload.get("source_api_id")
    target_api_id = payload.get("target_api_id")

    if not source_api_id or not target_api_id:
        return jsonify({"error": "source_api_id and target_api_id are required"}), 400

    source_schema_row = db.get_latest_schema(source_api_id, "output")
    target_schema_row = db.get_latest_schema(target_api_id, "input")

    if not source_schema_row:
        return jsonify({"error": f"No output schema found for source API {source_api_id}"}), 404
    if not target_schema_row:
        return jsonify({"error": f"No input schema found for target API {target_api_id}"}), 404

    source_api = db.get_api(source_api_id)
    target_api = db.get_api(target_api_id)

    result = compare_schemas(
        source_schema=source_schema_row["raw_schema"],
        target_schema=target_schema_row["raw_schema"],
        source_name=source_api["name"],
        target_name=target_api["name"],
    )

    stored = db.store_compatibility_result(
        source_api_id=source_api_id,
        target_api_id=target_api_id,
        source_schema_id=source_schema_row["id"],
        target_schema_id=target_schema_row["id"],
        result=result,
    )

    mapping = build_mapping(result)
    mapping_rules = []
    for fm in mapping.fields:
        if fm.transform in ("drop", "missing", "constant"):
            continue
        mapping_rules.append({
            "source_field": fm.source_path or "",
            "target_field": fm.target_path,
            "transform_type": fm.transform,
            "source_type": fm.source_type,
            "target_type": fm.target_type,
            "confidence": fm.confidence,
            "note": fm.note,
        })

    if mapping_rules:
        db.store_mapping_rules_bulk(source_api_id, target_api_id, mapping_rules)

    result["stored_result_id"] = stored["id"]
    result["mapping_status"] = mapping.status
    return jsonify(result)

@app.route("/api/compatibility/results", methods=["GET"])
def list_compat_results():
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    api_id = request.args.get("api_id", type=int)
    results = db.list_compatibility_results(api_id)
    return jsonify([_clean(r) for r in results])

@app.route("/api/compatibility/results/<int:source_schema_id>/<int:target_schema_id>", methods=["GET"])
def get_compat_result(source_schema_id, target_schema_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    result = db.get_compatibility_result(source_schema_id, target_schema_id)
    if not result:
        return jsonify({"error": "No result found"}), 404
    return jsonify(_clean(result))

@app.route("/api/compatibility/matrix", methods=["GET"])
def db_matrix():
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    api_ids_param = request.args.get("api_ids")
    api_ids = None
    if api_ids_param:
        api_ids = [int(x) for x in api_ids_param.split(",")]
    result = db.get_compatibility_matrix(api_ids)
    result["apis"] = [_clean(a) for a in result["apis"]]
    return jsonify(result)

@app.route("/api/mappings/<int:source_api_id>/<int:target_api_id>", methods=["GET"])
def get_mappings(source_api_id, target_api_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    rules = db.get_mapping_rules(source_api_id, target_api_id)
    return jsonify([_clean(r) for r in rules])

@app.route("/api/mappings/<int:source_api_id>/<int:target_api_id>", methods=["POST"])
def set_mappings(source_api_id, target_api_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    payload = request.get_json(silent=True) or {}
    rules = payload.get("rules", [])
    if not rules:
        return jsonify({"error": "rules is required"}), 400
    stored = db.store_mapping_rules_bulk(source_api_id, target_api_id, rules)
    return jsonify([_clean(r) for r in stored]), 201

@app.route("/api/mappings/<int:source_api_id>/<int:target_api_id>", methods=["DELETE"])
def delete_mappings(source_api_id, target_api_id):
    if not db_available:
        return jsonify({"error": "Database not available"}), 503
    count = db.delete_mapping_rules(source_api_id, target_api_id)
    return jsonify({"deleted": count})

if __name__ == "__main__":
    app.run(debug=True, port=5050)