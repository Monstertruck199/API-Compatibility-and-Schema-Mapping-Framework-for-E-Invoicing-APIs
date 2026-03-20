import requests
import json
import sys
import os

def save_schema(schema, status, headers):
    try:
        os.mkdir("schema_data")
    except:
        pass

    schema_number = 1
    schema_path = f"schema_data/JSON1"

    while os.path.exists(schema_path):
        schema_number += 1
        schema_path = f"schema_data/JSON{schema_number}"

    with open(schema_path, "w") as file:
        file.write(json.dumps(schema))

    schema_metadata_path = schema_path + "_metadata"

    with open(schema_metadata_path, "w") as file:
        file.write(f"Status: {status}\nHeaders: {headers}")    

    print(f"Schema saved at {schema_path}")
    print(f"Schema metadata saved at {schema_metadata_path}")


def analyze_api(url):
    try:
        response = requests.get(url)

        status = response.status_code
        headers = response.headers

        try:
            data = response.json()
            schema = infer_schema(data)
            save_schema(schema, status, headers)
        except Exception as e:
            print("Response is not JSON:")
            print(e)

    except requests.exceptions.RequestException as e:
        print("Invalid URL:")
        print(e)
        
def infer_schema(obj):
    if isinstance(obj, dict):
        return {
            "type": "object",
            "properties": {k: infer_schema(v) for k, v in obj.items()}
        }
    elif isinstance(obj, list):
        if obj:
            return {
                "type": "array",
                "items": infer_schema(obj[0])
            }
        else:
            return {"type": "array"}
    elif isinstance(obj, str):
        return {"type": "string"}
    elif isinstance(obj, int):
        return {"type": "integer"}
    elif isinstance(obj, float):
        return {"type": "number"}
    elif isinstance(obj, bool):
        return {"type": "boolean"}
    else:
        return {"type": "unknown"}
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} API_URL")
        quit()
    api_url = sys.argv[1]
    analyze_api(api_url)

