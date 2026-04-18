from flask import Flask, jsonify, request
from flask_cors import CORS
import datetime
import requests as http_requests
import xml.etree.ElementTree as ET

from compatibility_engine import compare_schemas
from extract_JSON_schema import infer_schema
from extract_XML_schema import extract_schema_from_xml
from mapping_engine import build_mapping
from schema_transformer import build_transformer

app = Flask(__name__)
CORS(app)

try:
    import db
except Exception:
    db = None

def _db_is_available():
    if db is None:
        return False
    try:
        return db.init_db()
    except Exception:
        return False

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

def _dict_to_xml_string(data, root_tag="record"):
    root = ET.Element(root_tag)

    def add_node(parent, value):
        if isinstance(value, dict):
            for key, child in value.items():
                child_el = ET.SubElement(parent, str(key))
                add_node(child_el, child)
        elif isinstance(value, list):
            for item in value:
                item_el = ET.SubElement(parent, "item")
                add_node(item_el, item)
        elif value is None:
            parent.text = ""
        else:
            parent.text = str(value)

    add_node(root, data)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "database": _db_is_available()})

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
    payload = request.get_json(silent=True) or {}
    source_schema = payload.get('source_schema')
    target_schema = payload.get('target_schema')
    source_data = payload.get('data')
    output_format = (payload.get('format') or 'json').lower()

    if not source_schema or not target_schema:
        return jsonify({'error': 'source_schema and target_schema are required'}), 400
    if source_data is None:
        return jsonify({'error': 'data is required'}), 400
    if output_format not in ('json', 'xml'):
        return jsonify({'error': 'format must be json or xml'}), 400

    source_api_id = payload.get('source_api_id')
    target_api_id = payload.get('target_api_id')
    source_schema_id = payload.get('source_schema_id')
    target_schema_id = payload.get('target_schema_id')

    try:
        result = compare_schemas(source_schema, target_schema, 'Source', 'Target')
        mapping = build_mapping(result)
        fn = build_transformer(mapping)

        mapping_status = mapping.status
        warnings = getattr(mapping, 'warnings', [])
        transformed_json = fn(source_data)
        rendered_output = _dict_to_xml_string(transformed_json, root_tag='record') if output_format == 'xml' else None

        response_payload = {
            'result': rendered_output if output_format == 'xml' else transformed_json,
            'format': output_format,
            'mapping_status': mapping_status,
            'warnings': warnings,
        }

        if _db_is_available():
            try:
                stored = db.store_transform_run(
                    source_api_id=source_api_id,
                    target_api_id=target_api_id,
                    source_schema_id=source_schema_id,
                    target_schema_id=target_schema_id,
                    input_data=source_data,
                    output_data=transformed_json,
                    output_text=rendered_output,
                    output_format=output_format,
                    mapping_status=mapping_status,
                    warnings=warnings,
                    success=True,
                )
                response_payload['stored_transform_id'] = stored['id']
            except Exception as storage_error:
                response_payload['storage_warning'] = str(storage_error)

        return jsonify(response_payload)

    except Exception as error:
        if _db_is_available():
            try:
                stored = db.store_transform_run(
                    source_api_id=source_api_id,
                    target_api_id=target_api_id,
                    source_schema_id=source_schema_id,
                    target_schema_id=target_schema_id,
                    input_data=source_data,
                    output_data=None,
                    output_text=None,
                    output_format=output_format,
                    mapping_status=None,
                    warnings=[],
                    success=False,
                    error_message=str(error),
                )
                return jsonify({'error': str(error), 'stored_transform_id': stored['id']}), 400
            except Exception:
                pass
        return jsonify({'error': str(error)}), 400

@app.route("/api/transforms", methods=["GET"])
def list_transform_runs():
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    limit = request.args.get("limit", default=50, type=int)
    runs = db.list_transform_runs(limit=limit)
    return jsonify([_clean(r) for r in runs])

@app.route("/api/transforms/<int:run_id>", methods=["GET"])
def get_transform_run(run_id):
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    run = db.get_transform_run(run_id)
    if not run:
        return jsonify({"error": "Transform run not found"}), 404
    return jsonify(_clean(run))

@app.route("/api/apis", methods=["GET"])
def list_apis():
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    apis = db.list_apis()
    return jsonify([_clean(a) for a in apis])

@app.route("/api/apis", methods=["POST"])
def create_api():
    if not _db_is_available():
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
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    api_row = db.get_api(api_id)
    if not api_row:
        return jsonify({"error": "API not found"}), 404
    return jsonify(_clean(api_row))

@app.route("/api/apis/<int:api_id>", methods=["DELETE"])
def delete_api(api_id):
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    if db.delete_api(api_id):
        return jsonify({"deleted": True})
    return jsonify({"error": "API not found"}), 404

@app.route("/api/apis/<int:api_id>/schemas", methods=["GET"])
def get_api_schemas(api_id):
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    schemas = db.get_schemas_for_api(api_id)
    return jsonify([_clean(s) for s in schemas])

@app.route("/api/apis/<int:api_id>/schemas", methods=["POST"])
def add_api_schema(api_id):
    if not _db_is_available():
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
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    schema_row = db.get_schema(schema_id)
    if not schema_row:
        return jsonify({"error": "Schema not found"}), 404
    return jsonify(_clean(schema_row))

@app.route("/api/schemas/<int:schema_id>/fields", methods=["GET"])
def get_schema_fields(schema_id):
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    fields = db.get_fields_for_schema(schema_id)
    return jsonify([_clean(f) for f in fields])

@app.route("/api/compatibility/compare", methods=["POST"])
def compare_and_store():
    if not _db_is_available():
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
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    api_id = request.args.get("api_id", type=int)
    results = db.list_compatibility_results(api_id)
    return jsonify([_clean(r) for r in results])

@app.route("/api/compatibility/results/<int:source_schema_id>/<int:target_schema_id>", methods=["GET"])
def get_compat_result(source_schema_id, target_schema_id):
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    result = db.get_compatibility_result(source_schema_id, target_schema_id)
    if not result:
        return jsonify({"error": "No result found"}), 404
    return jsonify(_clean(result))

@app.route("/api/compatibility/matrix", methods=["GET"])
def db_matrix():
    if not _db_is_available():
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
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    rules = db.get_mapping_rules(source_api_id, target_api_id)
    return jsonify([_clean(r) for r in rules])

@app.route("/api/mappings/<int:source_api_id>/<int:target_api_id>", methods=["POST"])
def set_mappings(source_api_id, target_api_id):
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    payload = request.get_json(silent=True) or {}
    rules = payload.get("rules", [])
    if not rules:
        return jsonify({"error": "rules is required"}), 400
    stored = db.store_mapping_rules_bulk(source_api_id, target_api_id, rules)
    return jsonify([_clean(r) for r in stored]), 201

@app.route("/api/mappings/<int:source_api_id>/<int:target_api_id>", methods=["DELETE"])
def delete_mappings(source_api_id, target_api_id):
    if not _db_is_available():
        return jsonify({"error": "Database not available"}), 503
    count = db.delete_mapping_rules(source_api_id, target_api_id)
    return jsonify({"deleted": count})

if __name__ == "__main__":
    app.run(debug=True, port=5050)