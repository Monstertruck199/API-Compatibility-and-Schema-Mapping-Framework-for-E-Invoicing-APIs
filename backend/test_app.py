import unittest
from unittest.mock import Mock, patch

import app as app_module

SOURCE_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_id": {"type": "string"},
        "amount": {"type": "number"},
    },
    "required": ["invoice_id", "amount"],
}

TARGET_SCHEMA_DIRECT = {
    "type": "object",
    "properties": {
        "invoice_id": {"type": "string"},
        "amount": {"type": "number"},
    },
    "required": ["invoice_id", "amount"],
}

TARGET_SCHEMA_MAPPING = {
    "type": "object",
    "properties": {
        "invoice_id": {"type": "string"},
        "total": {"type": "number"},
    },
    "required": ["invoice_id", "total"],
}


class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    @patch("app._db_is_available", return_value=True)
    def test_health_returns_ok(self, _mock_db):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["database"])


class TestAnalyzeEndpoint(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def test_analyze_missing_url_returns_400(self):
        response = self.client.get("/api/analyze")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    @patch("app.http_requests.get")
    def test_analyze_json_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"invoice_id": "INV-001", "amount": 100}'
        mock_response.json.return_value = {
            "invoice_id": "INV-001",
            "amount": 100,
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.client.get("/api/analyze?url=http://example.com/invoice.json&format=json")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("schema", body)
        self.assertEqual(body["status"], 200)
        self.assertEqual(body["content_type"], "application/json")

    @patch("app.http_requests.get")
    def test_analyze_request_failure_returns_400(self, mock_get):
        mock_get.side_effect = app_module.http_requests.exceptions.RequestException("connection failed")

        response = self.client.get("/api/analyze?url=http://example.com/broken.json&format=json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Request failed", response.get_json()["error"])

    @patch("app.http_requests.get")
    def test_analyze_parse_failure_returns_422(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = "not json"
        mock_response.json.side_effect = ValueError("invalid json")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.client.get("/api/analyze?url=http://example.com/invalid.json&format=json")

        self.assertEqual(response.status_code, 422)
        self.assertIn("Could not parse response", response.get_json()["error"])


class TestCompareEndpoint(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def test_compare_missing_schemas_returns_400(self):
        response = self.client.post("/api/compare", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_compare_directly_compatible_schemas(self):
        response = self.client.post(
            "/api/compare",
            json={
                "source_name": "Transformation API",
                "target_name": "Validation API",
                "source_schema": SOURCE_SCHEMA,
                "target_schema": TARGET_SCHEMA_DIRECT,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["source"], "Transformation API")
        self.assertEqual(body["target"], "Validation API")
        self.assertEqual(body["compatibility"], "directly_compatible")
        self.assertIn("summary", body)
        self.assertIn("issues", body)

    def test_compare_mapping_required_schema(self):
        response = self.client.post(
            "/api/compare",
            json={
                "source_name": "Transformation API",
                "target_name": "Validation API",
                "source_schema": SOURCE_SCHEMA,
                "target_schema": TARGET_SCHEMA_MAPPING,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn(body["compatibility"], [
            "directly_compatible",
            "compatible_with_mapping",
            "incompatible",
        ])
        self.assertIn("issues", body)


class TestMatrixEndpoint(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def test_matrix_missing_schemas_returns_400(self):
        response = self.client.post("/api/matrix", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_matrix_returns_square_matrix(self):
        response = self.client.post(
            "/api/matrix",
            json={
                "schemas": [
                    {
                        "name": "API A",
                        "schema": SOURCE_SCHEMA,
                    },
                    {
                        "name": "API B",
                        "schema": TARGET_SCHEMA_DIRECT,
                    },
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()

        self.assertIn("matrix", body)
        self.assertEqual(len(body["matrix"]), 2)
        self.assertEqual(len(body["matrix"][0]), 2)
        self.assertEqual(body["matrix"][0][0]["compatibility"], "same_schema")
        self.assertEqual(body["matrix"][1][1]["compatibility"], "same_schema")


class TestTransformEndpoint(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def test_transform_missing_schemas_returns_400(self):
        response = self.client.post(
            "/api/transform",
            json={
                "data": {
                    "invoice_id": "INV-001",
                    "amount": 100,
                }
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_transform_missing_data_returns_400(self):
        response = self.client.post(
            "/api/transform",
            json={
                "source_schema": SOURCE_SCHEMA,
                "target_schema": TARGET_SCHEMA_DIRECT,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("data is required", response.get_json()["error"])

    def test_transform_invalid_format_returns_400(self):
        response = self.client.post(
            "/api/transform",
            json={
                "source_schema": SOURCE_SCHEMA,
                "target_schema": TARGET_SCHEMA_DIRECT,
                "data": {
                    "invoice_id": "INV-001",
                    "amount": 100,
                },
                "format": "csv",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("format must be json or xml", response.get_json()["error"])

    @patch("app._db_is_available", return_value=False)
    def test_transform_json_success(self, _mock_db):
        response = self.client.post(
            "/api/transform",
            json={
                "source_schema": SOURCE_SCHEMA,
                "target_schema": TARGET_SCHEMA_DIRECT,
                "data": {
                    "invoice_id": "INV-001",
                    "amount": 100,
                },
                "format": "json",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()

        self.assertEqual(body["format"], "json")
        self.assertIn("result", body)
        self.assertEqual(body["result"]["invoice_id"], "INV-001")
        self.assertEqual(body["result"]["amount"], 100)
        self.assertIn("mapping_status", body)
        self.assertIn("warnings", body)
        self.assertIn("transform_code", body)

    @patch("app._db_is_available", return_value=False)
    def test_transform_xml_success(self, _mock_db):
        response = self.client.post(
            "/api/transform",
            json={
                "source_schema": SOURCE_SCHEMA,
                "target_schema": TARGET_SCHEMA_DIRECT,
                "data": {
                    "invoice_id": "INV-001",
                    "amount": 100,
                },
                "format": "xml",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()

        self.assertEqual(body["format"], "xml")
        self.assertIn("<record>", body["result"])
        self.assertIn("<invoice_id>INV-001</invoice_id>", body["result"])
        self.assertIn("<amount>100</amount>", body["result"])

    @patch("app._db_is_available", return_value=False)
    def test_transform_invalid_source_data_returns_400(self, _mock_db):
        response = self.client.post(
            "/api/transform",
            json={
                "source_schema": SOURCE_SCHEMA,
                "target_schema": TARGET_SCHEMA_DIRECT,
                "data": {
                    "invoice_id": "INV-001"
                },
                "format": "json",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()