from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

from compatibility_engine import compare_schemas
from extract_JSON_schema import infer_schema
from extract_XML_schema import extract_schema_from_xml


app = Flask(__name__)
CORS(app)


@app.route("/api/analyze", methods=["GET"])
def analyze():
    url = request.args.get("url")
    fmt = request.args.get("format", "json").lower()

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)