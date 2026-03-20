import requests
import xml.etree.ElementTree as ET
import sys
import json
import os

def save_schema(schema, status, headers):
    try:
        os.mkdir("schema_data")
    except:
        pass

    schema_number = 1
    schema_path = f"schema_data/XML1"

    while os.path.exists(schema_path):
        schema_number += 1
        schema_path = f"schema_data/XML{schema_number}"

    with open(schema_path, "w") as file:
        file.write(json.dumps(schema))

    schema_metadata_path = schema_path + "_metadata"

    with open(schema_metadata_path, "w") as file:
        file.write(f"Status: {status}\nHeaders: {headers}")    

    print(f"Schema saved at {schema_path}")
    print(f"Schema metadata saved at {schema_metadata_path}")

def infer_type(value):
    """Infer primitive type from text."""
    if value is None or value.strip() == "":
        return "string"

    value = value.strip()

    try:
        int(value)
        return "integer"
    except:
        pass

    try:
        float(value)
        return "number"
    except:
        pass

    if value.lower() in ["true", "false"]:
        return "boolean"

    return "string"


def analyze_element(element):
    schema = {
        "type": "object",
        "attributes": {},
        "properties": {}
    }

    # attributes
    for attr, val in element.attrib.items():
        schema["attributes"][attr] = infer_type(val)

    children = list(element)

    # text-only element
    if not children:
        if element.text and element.text.strip():
            schema["type"] = infer_type(element.text)
        return schema

    child_map = {}

    for child in children:
        child_schema = analyze_element(child)

        if child.tag not in child_map:
            child_map[child.tag] = []
        child_map[child.tag].append(child_schema)

    for tag, schemas in child_map.items():

        if len(schemas) > 1:
            schema["properties"][tag] = {
                "type": "array",
                "items": schemas[0]
            }
        else:
            schema["properties"][tag] = schemas[0]

    return schema

def extract_schema_from_xml(xml_string):
    root = ET.fromstring(xml_string)

    return {
        "root": root.tag,
        "schema": analyze_element(root)
    }

def analyze_api(url):
    try:
        response = requests.get(url)

        status = response.status_code
        headers = response.headers

        try:
            xml_data = response.text
            schema = extract_schema_from_xml(xml_data)
            save_schema(schema, status, headers)
        except Exception as e:
            print("Response is not XML")
            print(e)

    except requests.exceptions.RequestException as e:
        print("Invalid URL:")
        print(e)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} API_URL")
        quit()
    api_url = sys.argv[1]
    analyze_api(api_url)

