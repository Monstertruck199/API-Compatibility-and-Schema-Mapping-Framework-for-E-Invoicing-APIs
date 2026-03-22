import json
import os
import requests
import sys


def save_schema(schema, status, headers):
    os.makedirs("schema_data", exist_ok=True)

    schema_number = 1
    schema_path = f"schema_data/JSON{schema_number}"
    while os.path.exists(schema_path):
        schema_number += 1
        schema_path = f"schema_data/JSON{schema_number}"

    with open(schema_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(schema, indent=2))

    schema_metadata_path = schema_path + "_metadata"
    with open(schema_metadata_path, "w", encoding="utf-8") as file:
        file.write(f"Status: {status}\nHeaders: {dict(headers)}")

    print(f"Schema saved at {schema_path}")
    print(f"Schema metadata saved at {schema_metadata_path}")


def analyze_api(url):
    try:
        response = requests.get(url, timeout=15)
        status = response.status_code
        headers = response.headers
        data = response.json()
        schema = infer_schema(data)
        save_schema(schema, status, headers)
    except ValueError as error:
        print("Response is not JSON:")
        print(error)
    except requests.exceptions.RequestException as error:
        print("Invalid URL:")
        print(error)


def infer_schema(obj):
    if isinstance(obj, dict):
        properties = {key: infer_schema(value) for key, value in obj.items()}
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys()),
        }
    if isinstance(obj, list):
        if obj:
            return {
                "type": "array",
                "items": infer_schema(obj[0]),
            }
        return {
            "type": "array",
            "items": {"type": "unknown"},
        }
    if isinstance(obj, bool):
        return {"type": "boolean"}
    if isinstance(obj, int):
        return {"type": "integer"}
    if isinstance(obj, float):
        return {"type": "number"}
    if isinstance(obj, str):
        return {"type": "string"}
    if obj is None:
        return {"type": "null"}
    return {"type": "unknown"}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} API_URL")
        raise SystemExit(1)
    analyze_api(sys.argv[1])