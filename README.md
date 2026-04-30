# API Compatibility and Schema Mapping Framework for E-Invoicing APIs

This project is a web-based framework for assessing compatibility between heterogeneous e-invoicing APIs and supporting schema mapping between them.

Modern e-invoicing workflows often use multiple APIs together, such as transformation APIs, validation APIs, and communication APIs. Even when these APIs use the same data format, such as JSON or XML, their schemas can still be different. This creates integration problems because the output of one API may not match the input expected by the next API.

Our system helps solve this by allowing users to:

- Extract and view API schemas
- Compare source and target schemas
- Classify API compatibility
- Generate compatibility reports
- Build a compatibility matrix
- Store APIs, schemas, compatibility results, mapping rules, and transform runs
- Apply schema mappings to transform data from one API format into another

---

## Team

**Course:** COMP3900 Computer Science Project  
**Project:** P4 - A compatibility assessment and schema-mapping framework for composing heterogeneous e-invoicing APIs  
**Team:** M18A-Apple  

---

## Main Features

### 1. Schema Viewer

Users can load, inspect, and view API schemas in a structured format. The system supports JSON and XML-based schema extraction and displays fields in a readable format.

### 2. Schema Comparison

Users can compare two schemas to identify:

- Missing fields
- Extra fields
- Type mismatches
- Required and optional field conflicts
- Structural differences

### 3. Compatibility Classification

The system classifies schema compatibility into clear compatibility levels, such as:

- Directly compatible
- Compatible with mapping
- Incompatible
- Same schema
- Not assessed

### 4. Schema Mapping and Transformation

The system can generate mapping rules between source and target schemas. It can then apply these mappings to transform input data into a structure accepted by the target schema.

### 5. Compatibility Matrix

The system provides a matrix view showing compatibility between stored APIs. This allows users to quickly understand which APIs can work together directly, which need mapping, and which are incompatible.

### 6. Database Storage

The system stores important project data in PostgreSQL, including:

- APIs
- Schemas
- Schema fields
- Compatibility results
- Mapping rules
- Transform runs

### 7. Database Viewer

The frontend includes a database page where users can view stored APIs, compatibility results, mappings, and transform runs.

---

## Technology Stack

### Frontend

- HTML
- CSS
- JavaScript
- Nginx for serving the frontend in Docker
- Jest for frontend tests

### Backend

- Python
- Flask
- Flask-CORS
- PostgreSQL
- psycopg2
- jsonschema
- Gunicorn

### DevOps

- Docker
- Docker Compose

---

## Project Structure

```txt
.
├── backend/
│   ├── app.py
│   ├── compatibility_engine.py
│   ├── data_validator.py
│   ├── db.py
│   ├── extract_JSON_schema.py
│   ├── extract_XML_schema.py
│   ├── mapping_engine.py
│   ├── schema_transformer.py
│   ├── test_db.py
│   ├── test_app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── database/
│   └── schema.sql
│
├── example_schemas/
│   └── example JSON/XML schemas
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── schema-viewer.js
│   ├── schema-comparison.js
│   ├── compatibility-result.js
│   ├── matrix.js
│   ├── database.js
│   ├── styles/
│   ├── nginx.conf
│   └── Dockerfile
│
├── frontend_tests/
│   └── Jest frontend tests
│
├── docker-compose.yml
├── package.json
├── package-lock.json
└── README.md
```

---

## Running the System with Docker

The recommended way to run the full system is with Docker Compose.

From the project root, run:

```bash
docker compose up --build
```

This starts three services:

| Service    | URL / Port              |
|------------|-------------------------|
| Frontend   | <http://localhost:3000> |
| Backend    | <http://localhost:5050> |
| PostgreSQL | localhost:5433          |

Open the frontend in your browser:

```txt
http://localhost:3000
```

To check that the backend is running, open:

```txt
http://localhost:5050/api/health
```

A successful backend health check should return a JSON response similar to:

```json
{
  "database": true,
  "status": "ok"
}
```

---

## Stopping the System

To stop the running containers:

```bash
docker compose down
```

To stop the system and reset the database volume:

```bash
docker compose down -v
```

Then rebuild the system:

```bash
docker compose up --build
```

---

## Environment Variables

No extra environment variables are required to run the system locally through Docker Compose.

The Docker Compose file already provides the database configuration:

```txt
DB_HOST=db
DB_PORT=5433
DB_NAME=api_compatibility
DB_USER=admin
DB_PASSWORD=password
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

These values are only for local development and testing.

Do not commit real API keys or production secrets to the repository.

The `.env.example` file is included only as a placeholder for external API credentials if future development connects the system to real e-invoicing API providers.

---

## Running Frontend Tests

From the project root, install the Node dependencies:

```bash
npm install
```

Then run:

```bash
npm test
```

The frontend tests cover JavaScript UI logic, including:

- Schema viewer rendering
- Schema comparison controls
- Compatibility result rendering
- Compatibility matrix rendering
- Database table display logic

---

## Running Backend Tests

First, make sure the database container is running:

```bash
docker compose up db -d
```

Then run the backend test suite:

```bash
cd backend
python3 -m unittest test_db.py test_app.py -v
```

The backend database tests cover:

- API creation and retrieval
- API deletion
- Schema storage and retrieval
- Schema field extraction
- Compatibility result storage
- Mapping rule storage
- Transform run storage
- Compatibility matrix generation
- Cascade delete behaviour

If all tests pass, the output should end with something similar to:

```txt
Ran 73 tests

OK
```

---

## Manual Testing Guide

After starting the system with:

```bash
docker compose up --build
```

open:

```txt
http://localhost:3000
```

Then perform the following checks.

### 1. Schema Viewer

1. Open the schema viewer page.
2. Load or paste a JSON or XML schema.
3. Confirm that the schema is displayed in a readable field structure.
4. Confirm that field names, types, and nested fields are shown correctly.

### 2. Schema Comparison

1. Select or load two schemas.
2. Run the comparison.
3. Confirm that the system reports schema differences.
4. Check that missing fields, extra fields, type conflicts, and structural differences are shown clearly.

### 3. Compatibility Result

1. Compare two API schemas.
2. Confirm that the result includes a compatibility classification.
3. Confirm that the result explains whether mapping is needed.

### 4. Compatibility Matrix

1. Add or load multiple APIs and schemas.
2. Open the compatibility matrix.
3. Confirm that API pairs are shown in matrix form.
4. Confirm that assessed pairs and unassessed pairs are labelled correctly.

### 5. Data Transformation

1. Select a source schema and a target schema.
2. Provide input data matching the source schema.
3. Run the transformation.
4. Confirm that the output follows the target schema structure.
5. Confirm that the transform run is stored in the database.

### 6. Database Page

1. Open the database page.
2. Confirm that stored APIs, compatibility results, mapping rules, and transform runs are visible.
3. Confirm that search, table display, and row expansion work correctly.

---

## Main Backend API Endpoints

| Method | Endpoint                                        | Purpose                                        |
|--------|-------------------------------------------------|------------------------------------------------|
| GET    | `/api/health`                                   | Check backend and database status              |
| GET    | `/api/analyze`                                  | Extract schema from a URL                      |
| POST   | `/api/compare`                                  | Compare two provided schemas                   |
| POST   | `/api/matrix`                                   | Build an in-memory compatibility matrix        |
| POST   | `/api/transform`                                | Transform data using generated mappings        |
| GET    | `/api/apis`                                     | List stored APIs                               |
| POST   | `/api/apis`                                     | Create a stored API                            |
| GET    | `/api/apis/<api_id>`                            | Get one stored API                             |
| DELETE | `/api/apis/<api_id>`                            | Delete a stored API                            |
| GET    | `/api/apis/<api_id>/schemas`                    | List schemas for an API                        |
| POST   | `/api/apis/<api_id>/schemas`                    | Store a schema for an API                      |
| GET    | `/api/schemas/<schema_id>`                      | Get one stored schema                          |
| GET    | `/api/schemas/<schema_id>/fields`               | Get extracted fields for a schema              |
| POST   | `/api/compatibility/compare`                    | Compare stored API schemas and save the result |
| GET    | `/api/compatibility/results`                    | List stored compatibility results              |
| GET    | `/api/compatibility/matrix`                     | Get the stored API compatibility matrix        |
| GET    | `/api/mappings/<source_api_id>/<target_api_id>` | Get mapping rules                              |
| POST   | `/api/mappings/<source_api_id>/<target_api_id>` | Store mapping rules                            |
| DELETE | `/api/mappings/<source_api_id>/<target_api_id>` | Delete mapping rules                           |
| GET    | `/api/transforms`                               | List transform runs                            |
| GET    | `/api/transforms/<run_id>`                      | Get one transform run                          |

---

## Example Backend Health Check

After the backend is running, test it with:

```bash
curl http://localhost:5050/api/health
```

Expected response:

```json
{
  "database": true,
  "status": "ok"
}
```

---

## Example Schema Comparison Request

```bash
curl -X POST http://localhost:5050/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "source_name": "Source API",
    "target_name": "Target API",
    "source_schema": {
      "type": "object",
      "properties": {
        "invoice_id": { "type": "string" },
        "amount": { "type": "number" }
      },
      "required": ["invoice_id", "amount"]
    },
    "target_schema": {
      "type": "object",
      "properties": {
        "invoice_id": { "type": "string" },
        "total": { "type": "number" }
      },
      "required": ["invoice_id", "total"]
    }
  }'
```

---

## Database Reset

To fully reset the database and start again:

```bash
docker compose down -v
docker compose up --build
```

This removes the old PostgreSQL volume and recreates the database using:

```txt
database/schema.sql
```

---

## Known Limitations

- The current system is a prototype and focuses on schema-level compatibility rather than live production API orchestration.
- Mapping suggestions are based on schema structure, field names, and type information. They may still require manual review.
- The system supports JSON and XML schema extraction, but complex real-world schemas may need further handling.
- The compatibility matrix depends on stored schemas and previous comparisons.
- Real external e-invoicing API authentication is not fully integrated in this version.

---

## Future Work

Possible future improvements include:

- More advanced automated mapping suggestions
- Better support for deeply nested XML and XSD schemas
- More complete validation against real e-invoicing standards
- Live API pipeline execution between transformation, validation, and communication APIs
- User accounts and role-based access control
- Exportable compatibility reports as PDF or CSV
- More end-to-end tests covering the full frontend, backend, and database workflow

---

## Notes for Markers

The full system should be run using Docker Compose.

Use:

```bash
docker compose up --build
```

Then open:

```txt
http://localhost:3000
```

The backend health check is available at:

```txt
http://localhost:5050/api/health
```

Frontend tests can be run with:

```bash
npm test
```

Backend tests can be run with:

```bash
docker compose up db -d
cd backend
python3 -m unittest test_db.py -v
```
