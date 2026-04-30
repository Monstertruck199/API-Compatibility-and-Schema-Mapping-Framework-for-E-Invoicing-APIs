import json
import os
import sys
import xml.etree.ElementTree as ET

import requests


def save_schema(schema, status, headers):
    os.makedirs("schema_data", exist_ok=True)

    schema_number = 1
    schema_path = f"schema_data/XML{schema_number}"
    while os.path.exists(schema_path):
        schema_number += 1
        schema_path = f"schema_data/XML{schema_number}"

    with open(schema_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(schema, indent=2))

    schema_metadata_path = schema_path + "_metadata"
    with open(schema_metadata_path, "w", encoding="utf-8") as file:
        file.write(f"Status: {status}\nHeaders: {dict(headers)}")

    print(f"Schema saved at {schema_path}")
    print(f"Schema metadata saved at {schema_metadata_path}")

def infer_type(value):
    if value is None or value.strip() == "":
        return "string"

    value = value.strip()
    try:
        int(value)
        return "integer"
    except ValueError:
        pass

    try:
        float(value)
        return "number"
    except ValueError:
        pass

    if value.lower() in {"true", "false"}:
        return "boolean"
    return "string"

def analyze_element(element):
    schema = {
        "type": "object",
        "attributes": {},
        "properties": {},
        "required": [],
    }

    for attr, value in element.attrib.items():
        key = f"@{attr}"
        schema["properties"][key] = {"type": infer_type(value)}
        schema["required"].append(key)

    children = list(element)
    if not children:
        if element.text and element.text.strip():
            return {"type": infer_type(element.text)}
        return {"type": "string"}

    grouped_children = {}
    for child in children:
        grouped_children.setdefault(child.tag, []).append(analyze_element(child))

    for tag, child_schemas in grouped_children.items():
        schema["required"].append(tag)
        if len(child_schemas) > 1:
            schema["properties"][tag] = {
                "type": "array",
                "items": child_schemas[0],
            }
        else:
            schema["properties"][tag] = child_schemas[0]

    schema["required"] = sorted(set(schema["required"]))
    return schema

def extract_schema_from_xml(xml_string):
    root = ET.fromstring(xml_string)
    return {
        "root": root.tag,
        "schema": analyze_element(root),
    }

def analyze_api(url):
    try:
        response = requests.get(url, timeout=15)
        status = response.status_code
        headers = response.headers
        schema = extract_schema_from_xml(response.text)
        save_schema(schema, status, headers)
    except ET.ParseError as error:
        print("Response is not XML")
        print(error)
    except requests.exceptions.RequestException as error:
        print("Invalid URL:")
        print(error)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} API_URL")
        raise SystemExit(1)
    analyze_api(sys.argv[1])