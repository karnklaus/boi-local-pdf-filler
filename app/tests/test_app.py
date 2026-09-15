import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

APP_SOURCE = Path(__file__).resolve().parents[1] / "app.py"
APP_SPEC = importlib.util.spec_from_file_location("boi_app_under_test", APP_SOURCE)
app_module = importlib.util.module_from_spec(APP_SPEC)
sys.modules[APP_SPEC.name] = app_module
APP_SPEC.loader.exec_module(app_module)


def create_synthetic_pdf(path, field_names):
    document = canvas.Canvas(str(path), pagesize=letter)
    for index, field_name in enumerate(field_names):
        document.acroForm.textfield(
            name=field_name,
            x=36,
            y=letter[1] - 48 - index * 24,
            width=240,
            height=18,
            borderWidth=0,
        )
    document.showPage()
    document.save()


def synthetic_document(doc_id, title, keys, filename):
    bindings = []
    field_names = []
    for key in keys:
        transforms = ("reason_line_1", "reason_line_2") if key == "reason" else (None,)
        for transform in transforms:
            suffix = transform or "value"
            field_name = f"{doc_id}-{key}-{suffix}"
            binding = {"pdf_field": field_name, "key": key}
            if transform:
                binding["transform"] = transform
            bindings.append(binding)
            field_names.append(field_name)
    return {
        "id": doc_id,
        "title": title,
        "description": "Synthetic test document",
        "filename": filename,
        "enabled": True,
        "order": 10 if doc_id == "change-visa" else 20,
        "bindings": bindings,
    }, field_names


class AppWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temporary_directory = TemporaryDirectory()
        cls._original_interface = app_module.app.session_interface
        cls._original_testing = app_module.app.config.get("TESTING", False)
        cls._original_documents_dir = app_module.DOCUMENTS_DIR
        cls._original_documents = app_module.DOCUMENTS
        cls._original_config_errors = app_module.CONFIG_ERRORS
        cls._documents_directory = Path(cls._temporary_directory.name) / "documents"
        cls._documents_directory.mkdir()
        cls._documents = []
        for doc_id, title, keys, filename in (
            (
                "change-visa",
                "Synthetic change visa",
                [
                    "company", "letter_date", "business_start", "business_type", "address",
                    "foreigner_name", "age", "position", "expertise", "visa_from", "signer", "nationality",
                ],
                "change-visa.fill.pdf",
            ),
            (
                "income-explanation",
                "Synthetic income explanation",
                ["letter_date", "company", "business_start", "business_type", "address", "reason", "signer"],
                "income-explanation.fill.pdf",
            ),
        ):
            document, field_names = synthetic_document(doc_id, title, keys, filename)
            create_synthetic_pdf(cls._documents_directory / filename, field_names)
            cls._documents.append(document)
        app_module.DOCUMENTS_DIR = cls._documents_directory
        app_module.DOCUMENTS = cls._documents
        app_module.CONFIG_ERRORS = []
        app_module.app.session_interface = app_module.SQLiteSessionInterface(
            Path(cls._temporary_directory.name) / "sessions.sqlite3"
        )
        app_module.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        app_module.app.session_interface = cls._original_interface
        app_module.app.config.update(TESTING=cls._original_testing)
        app_module.DOCUMENTS_DIR = cls._original_documents_dir
        app_module.DOCUMENTS = cls._original_documents
        app_module.CONFIG_ERRORS = cls._original_config_errors
        cls._temporary_directory.cleanup()

    def csrf_token(self, client):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        with client.session_transaction() as stored:
            return stored[app_module.CSRF_SESSION_KEY]

    def form_data(self, token):
        return {
            "csrf_token": token,
            "document__change-visa__company": "บริษัททดสอบ จำกัด",
            "document__change-visa__letter_date": "01/09/2569",
            "document__change-visa__business_start": "01/01/2560",
            "document__change-visa__business_type": "ทดสอบระบบ",
            "document__change-visa__address": "ที่อยู่สมมติ",
            "document__change-visa__foreigner_name": "Synthetic Person",
            "document__change-visa__age": "35",
            "document__change-visa__position": "Tester",
            "document__change-visa__expertise": "Quality assurance",
            "document__change-visa__visa_from": "Tourist",
            "document__change-visa__signer": "Synthetic Signer",
            "document__change-visa__nationality": "Synthetic",
            "document__income-explanation__letter_date": "01/09/2569",
            "document__income-explanation__company": "บริษัททดสอบ จำกัด",
            "document__income-explanation__business_start": "01/01/2560",
            "document__income-explanation__business_type": "ทดสอบระบบ",
            "document__income-explanation__address": "ที่อยู่สมมติ",
            "document__income-explanation__reason": "เหตุผลทดสอบแบบไม่ใช่ข้อมูลจริง",
            "document__income-explanation__signer": "Synthetic Signer",
        }

    def test_export_and_clear_workflow(self):
        client = app_module.app.test_client()
        token = self.csrf_token(client)

        response = client.post(
            "/select",
            data={"csrf_token": token, "documents": ["change-visa", "income-explanation"]},
        )
        self.assertEqual(response.status_code, 302)

        response = client.post("/form", data=self.form_data(token))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/review"))

        response = client.post("/review", data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)

        response = client.post(
            "/export",
            data={
                "csrf_token": token,
                "document_order": "change-visa,income-explanation",
                "font_name": "tahoma",
                "font_size": "12",
                "output_filename": "synthetic-check",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertGreater(len(response.data), 1000)

        response = client.post("/clear", data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)
        with client.session_transaction() as stored:
            self.assertNotIn("case_data", stored)
            self.assertNotIn("selected_documents", stored)

    def test_state_changing_requests_require_csrf(self):
        client = app_module.app.test_client()
        response = client.post("/select", data={"documents": ["change-visa"]})
        self.assertEqual(response.status_code, 400)

    def test_input_length_is_validated(self):
        client = app_module.app.test_client()
        token = self.csrf_token(client)
        response = client.post(
            "/select",
            data={"csrf_token": token, "documents": ["change-visa"]},
        )
        self.assertEqual(response.status_code, 302)
        response = client.post(
            "/form",
            data={
                "csrf_token": token,
                "document__change-visa__company": "x" * 201,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("ข้อมูลยาวเกินขนาดที่กำหนด", response.get_data(as_text=True))

    def test_non_loopback_host_is_rejected(self):
        client = app_module.app.test_client()
        response = client.get("/", base_url="http://192.0.2.1:5000")
        self.assertEqual(response.status_code, 403)

    def test_security_headers_and_reserved_filename(self):
        client = app_module.app.test_client()
        response = client.get("/")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Pragma"], "no-cache")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(app_module.safe_filename("", "CON"), "_CON.pdf")


if __name__ == "__main__":
    unittest.main()
