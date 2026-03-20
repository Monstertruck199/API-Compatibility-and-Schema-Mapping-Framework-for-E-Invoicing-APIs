from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

from extract_JSON_schema import infer_schema
from extract_XML_schema import extract_schema_from_xml

app = Flask(__name__)
CORS(app)  
@app.route("/api/analyze", methods=["GET"])
def analyze():
    url    = request.args.get("url")
    fmt    = request.args.get("format", "json")

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    try:
        response = requests.get(url, timeout=10)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request failed: {str(e)}"}), 400

    status = response.status_code

    try:
        if fmt == "xml":
            schema = extract_schema_from_xml(response.text)
        else:
            data   = response.json()
            schema = infer_schema(data)
    except Exception as e:
        return jsonify({"error": f"Could not parse response as {fmt}: {str(e)}"}), 422

    return jsonify({"schema": schema, "status": status})


if __name__ == "__main__":
    app.run(debug=True, port=5000)