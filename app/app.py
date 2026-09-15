import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from time import time

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask.sessions import SessionInterface, SessionMixin
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import ArrayObject, NameObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from werkzeug.datastructures import CallbackDict
from werkzeug.exceptions import RequestEntityTooLarge

BASE = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE / "documents"
DEFAULT_CONFIG_PATH = BASE / "config" / "documents.json"
EXAMPLE_CONFIG_PATH = BASE / "config" / "documents.example.json"
SESSION_DB_PATH = BASE / "data" / "sessions.sqlite3"
SESSION_COOKIE_NAME = "boi_session"
CSRF_SESSION_KEY = "_csrf_token"
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,128}$")


class SQLiteSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None, new=False):
        def on_update(*_args):
            self.modified = True

        super().__init__(initial or {}, on_update)
        self.sid = sid
        self.new = new
        self.modified = new


class SQLiteSessionInterface(SessionInterface):
    session_class = SQLiteSession

    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    sid TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )

    def _connect(self):
        connection = sqlite3.connect(str(self.database_path), timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def open_session(self, app, request):
        sid = request.cookies.get(self.get_cookie_name(app))
        if not sid or not SESSION_ID_PATTERN.fullmatch(sid):
            return self.session_class({}, sid=secrets.token_urlsafe(32), new=True)

        with self._connection() as connection:
            row = connection.execute(
                "SELECT data FROM sessions WHERE sid = ?", (sid,)
            ).fetchone()
        if not row:
            return self.session_class({}, sid=secrets.token_urlsafe(32), new=True)

        try:
            data = json.loads(row[0])
        except (TypeError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        return self.session_class(data, sid=sid, new=False)

    def save_session(self, app, session, response):
        cookie_name = self.get_cookie_name(app)
        cookie_domain = self.get_cookie_domain(app)
        cookie_path = self.get_cookie_path(app)

        if not session:
            with self._connection() as connection:
                connection.execute("DELETE FROM sessions WHERE sid = ?", (session.sid,))
            response.delete_cookie(cookie_name, domain=cookie_domain, path=cookie_path)
            return

        if not session.modified and not session.new:
            return

        serialized = json.dumps(dict(session), ensure_ascii=False, separators=(",", ":"))
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO sessions (sid, data, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(sid) DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (session.sid, serialized, int(time())),
            )

        response.set_cookie(
            cookie_name,
            session.sid,
            httponly=app.config.get("SESSION_COOKIE_HTTPONLY", True),
            secure=app.config.get("SESSION_COOKIE_SECURE", False),
            samesite=app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
            domain=cookie_domain,
            path=cookie_path,
        )


app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.environ.get("BOI_SECRET_KEY") or secrets.token_urlsafe(32),
    MAX_CONTENT_LENGTH=256 * 1024,
    SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=False,
)
app.session_interface = SQLiteSessionInterface(SESSION_DB_PATH)

FONT_OPTIONS = {
    "thsarabun": ("TH Sarabun New", Path(r"C:\Windows\Fonts\THSarabunNew.ttf"), "THSarabunNew"),
    "tahoma": ("Tahoma", Path(r"C:\Windows\Fonts\tahoma.ttf"), "Tahoma"),
    "arial": ("Arial", Path(r"C:\Windows\Fonts\arial.ttf"), "Arial"),
}
ACCENT_OPTIONS = {
    "purple": {"label": "ม่วง", "color": "#68136f"},
    "blue": {"label": "น้ำเงิน", "color": "#1b5f8a"},
    "green": {"label": "เขียว", "color": "#2c6b51"},
    "orange": {"label": "ส้มอิฐ", "color": "#a65b2a"},
}
THEME_OPTIONS = {
    "light": "Light",
    "dark": "Dark",
    "auto": "Auto",
}
for _, path, registered_name in FONT_OPTIONS.values():
    if path.exists():
        pdfmetrics.registerFont(TTFont(registered_name, str(path)))
DEFAULT_FONT = "thsarabun" if FONT_OPTIONS["thsarabun"][1].exists() else "tahoma"
DEFAULT_FONT_SIZE = 12
DEFAULT_ACCENT = "purple"
DEFAULT_THEME = "light"
DEFAULT_MAX_LENGTHS = {
    "text": 200,
    "textarea": 2000,
    "date": 10,
    "number": 3,
}


def field_max_length(definition):
    try:
        fallback = DEFAULT_MAX_LENGTHS.get(definition.get("type"), 200)
        return max(1, int(definition.get("max_length", fallback)))
    except (AttributeError, TypeError, ValueError):
        return 200


@app.template_global("field_max_length")
def template_field_max_length(definition):
    return field_max_length(definition)


@app.template_global("csrf_token")
def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def is_loopback_request():
    hostname = request.host
    if hostname.startswith("["):
        hostname = hostname[1:].split("]", 1)[0]
    else:
        hostname = hostname.split(":", 1)[0]
    if hostname.lower() not in {"127.0.0.1", "localhost", "::1"}:
        return False
    return not request.remote_addr or request.remote_addr in {"127.0.0.1", "::1"}


@app.before_request
def enforce_loopback_only():
    if not is_loopback_request():
        abort(403)


@app.before_request
def protect_state_changing_requests():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    expected = session.get(CSRF_SESSION_KEY, "")
    submitted = request.form.get("csrf_token", "")
    if not expected or not submitted or not hmac.compare_digest(str(expected), str(submitted)):
        abort(400, description="คำขอไม่ถูกต้อง กรุณาโหลดหน้าเว็บใหม่แล้วลองอีกครั้ง")


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; object-src 'none'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'; "
        "script-src 'self'; script-src-attr 'none'; style-src 'self'; "
        "style-src-attr 'none'; img-src 'self' data:; font-src 'self'",
    )
    return response


@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(_error):
    return "ข้อมูลที่ส่งมายาวเกินขนาดที่ระบบรองรับ", 413, {
        "Content-Type": "text/plain; charset=utf-8"
    }


@app.errorhandler(400)
def handle_bad_request(error):
    message = getattr(error, "description", None) or "คำขอไม่ถูกต้อง"
    return message, 400, {"Content-Type": "text/plain; charset=utf-8"}


@app.errorhandler(403)
def handle_forbidden(_error):
    return "ระบบนี้เปิดให้ใช้งานเฉพาะเครื่องนี้เท่านั้น", 403, {
        "Content-Type": "text/plain; charset=utf-8"
    }


def load_config():
    configured_path = os.environ.get("BOI_DOCUMENTS_CONFIG")
    if configured_path:
        config_path = Path(configured_path)
        if not config_path.is_absolute():
            config_path = BASE / config_path
    else:
        config_path = DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    if config.get("version") != 1:
        raise ValueError("config/documents.json ต้องเป็น version 1")
    return config


CONFIG = load_config()
FIELD_DEFS = CONFIG.get("fields", {})
DOCUMENTS = sorted(
    [doc for doc in CONFIG.get("documents", []) if doc.get("enabled", True)],
    key=lambda doc: (doc.get("order", 9999), doc.get("id", "")),
)


def form_field_names(pdf_path):
    reader = PdfReader(str(pdf_path))
    names = set((reader.get_fields() or {}).keys())
    for page in reader.pages:
        for annotation_ref in page.get("/Annots", []):
            annotation = annotation_ref.get_object()
            name = annotation.get("/T")
            if not name and annotation.get("/Parent"):
                name = annotation["/Parent"].get_object().get("/T")
            if name:
                names.add(str(name))
    return names


def validate_documents():
    errors = []
    ids = set()
    for doc in DOCUMENTS:
        doc_id = doc.get("id")
        if not doc_id or doc_id in ids:
            errors.append(f"รหัสเอกสารซ้ำหรือว่าง: {doc_id or '(ว่าง)'}")
        ids.add(doc_id)
        pdf_path = DOCUMENTS_DIR / doc.get("filename", "")
        if not pdf_path.exists():
            errors.append(f"ไม่พบไฟล์ PDF ของ {doc.get('title', doc_id)}: {pdf_path.name}")
            continue
        try:
            available = form_field_names(pdf_path)
        except (KeyError, OSError, PdfReadError, TypeError, ValueError) as exc:
            errors.append(f"อ่าน PDF ไม่ได้ ({pdf_path.name}): {exc}")
            continue
        for binding in doc.get("bindings", []):
            pdf_field = binding.get("pdf_field")
            key = binding.get("key")
            if pdf_field not in available:
                errors.append(f"ไม่พบ PDF Field '{pdf_field}' ใน {pdf_path.name}")
            if key not in FIELD_DEFS:
                errors.append(f"ไม่พบข้อมูลกลาง '{key}' ที่ mapping จาก {pdf_field}")
    return errors


CONFIG_ERRORS = validate_documents()


def val(data, key):
    return (data.get(key) or "").strip()


THAI_MONTHS = (
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
)


def thai_date(value):
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return value or ""
    return f"{parsed.day} {THAI_MONTHS[parsed.month - 1]} {parsed.year + 543}"


def normalize_date_input(value):
    value = (value or "").strip()
    if not value:
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        pass

    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    if year >= 2400:
        year -= 543
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


@app.template_global("thai_numeric_date")
def thai_numeric_date(value):
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return ""
    return f"{parsed.day:02d}/{parsed.month:02d}/{parsed.year + 543:04d}"


@app.template_global("date_input_value")
def date_input_value(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        return ""


@app.template_global("format_value")
def format_value(value, key):
    if FIELD_DEFS.get(key, {}).get("type") == "date":
        return thai_date(value)
    return value or ""


def get_font_name(font_key):
    _, font_path, registered_name = FONT_OPTIONS.get(font_key, FONT_OPTIONS[DEFAULT_FONT])
    return registered_name if font_path.exists() else FONT_OPTIONS[DEFAULT_FONT][2]


def normalize_font_size(value):
    try:
        return max(7.0, min(24.0, float(value)))
    except (TypeError, ValueError):
        return 12.0


def current_settings():
    saved = session.get("settings", {})
    font_key = saved.get("font_name", DEFAULT_FONT)
    if font_key not in FONT_OPTIONS:
        font_key = DEFAULT_FONT
    accent_key = saved.get("accent", DEFAULT_ACCENT)
    if accent_key not in ACCENT_OPTIONS:
        accent_key = DEFAULT_ACCENT
    theme_key = saved.get("theme", DEFAULT_THEME)
    if theme_key not in THEME_OPTIONS:
        theme_key = DEFAULT_THEME
    return {
        "font_name": font_key,
        "font_size": normalize_font_size(saved.get("font_size", DEFAULT_FONT_SIZE)),
        "accent": accent_key,
        "theme": theme_key,
    }


def build_progress(active_step):
    has_data = bool(session.get("case_data"))
    definitions = [
        (1, "เลือกเอกสาร", url_for("select_documents_page")),
        (2, "กรอกข้อมูล", url_for("data_form")),
        (3, "ตรวจสอบ", url_for("review")),
        (4, "Export", url_for("export")),
    ]
    result = []
    for number, label, href in definitions:
        available = number <= active_step or (number == 3 and has_data) or (number == 4 and active_step >= 3 and has_data)
        result.append({"number": number, "label": label, "href": href if available else None,
                       "current": number == active_step, "complete": number < active_step})
    return result


def get_document(doc_id):
    return next((doc for doc in DOCUMENTS if doc["id"] == doc_id), None)


def selected_documents(ids):
    documents_by_id = {doc["id"]: doc for doc in DOCUMENTS}
    result = []
    seen = set()
    for doc_id in ids:
        if doc_id in documents_by_id and doc_id not in seen:
            result.append(documents_by_id[doc_id])
            seen.add(doc_id)
    return result


def apply_document_order(raw_order, docs):
    submitted_order = [
        doc_id.strip()
        for doc_id in (raw_order or "").split(",")
        if doc_id.strip()
    ]
    allowed_ids = {doc["id"] for doc in docs}
    if len(submitted_order) == len(allowed_ids) and set(submitted_order) == allowed_ids:
        session["selected_documents"] = submitted_order
        return selected_documents(submitted_order)
    return docs


def selected_field_defs(docs):
    keys = {binding["key"] for doc in docs for binding in doc.get("bindings", [])}
    return sorted(
        [(key, FIELD_DEFS[key]) for key in keys if key in FIELD_DEFS],
        key=lambda item: (item[1].get("order", 9999), item[0]),
    )


def document_field_defs(doc):
    fields = []
    seen = set()
    for binding in doc.get("bindings", []):
        key = binding.get("key")
        if key in FIELD_DEFS and key not in seen:
            fields.append((key, FIELD_DEFS[key]))
            seen.add(key)
    return fields


def document_is_complete(doc, data):
    return all(val(data, key) for key, _ in document_field_defs(doc))


def field_widgets(page):
    result = []
    for annotation_ref in page.get("/Annots", []):
        widget = annotation_ref.get_object()
        field_name = widget.get("/T")
        if not field_name and widget.get("/Parent"):
            field_name = widget["/Parent"].get_object().get("/T")
        rect = widget.get("/Rect")
        if field_name and rect:
            rect = [float(item.get_object() if hasattr(item, "get_object") else item) for item in rect]
            result.append((str(field_name), rect))
    return result


def split_reason(text, font_name, font_size, first_width):
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if not text:
        return "", ""
    width = max(30, first_width - 5)
    words = text.split(" ")
    first = ""
    remaining_index = len(words)
    for index, word in enumerate(words):
        candidate = word if not first else f"{first} {word}"
        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= width:
            first = candidate
            continue
        if first:
            remaining_index = index
            break

        partial = ""
        remainder = word
        while remainder:
            candidate = partial + remainder[0]
            if partial and pdfmetrics.stringWidth(candidate, font_name, font_size) > width:
                break
            partial = candidate
            remainder = remainder[1:]
        first = partial or word[:1]
        words[index] = remainder
        remaining_index = index
        break

    second = " ".join(words[remaining_index:]).strip() if remaining_index < len(words) else ""
    return first.rstrip(), second


def binding_values(doc, central_data, font_key, font_size, reader):
    font_name = get_font_name(font_key)
    widgets = [item for page in reader.pages for item in field_widgets(page)]
    widths = {name: max(rect[2] - rect[0] for field, rect in widgets if field == name) for name in {field for field, _ in widgets}}
    values = {}
    reason_cache = {}
    reason_widths = {
        binding["key"]: widths.get(binding["pdf_field"], 200)
        for binding in doc.get("bindings", [])
        if binding.get("transform") == "reason_line_1"
    }
    for binding in doc.get("bindings", []):
        pdf_field = binding["pdf_field"]
        key = binding["key"]
        transform = binding.get("transform")
        if transform in {"reason_line_1", "reason_line_2"}:
            split_width = reason_widths.get(key, widths.get(pdf_field, 200))
            cache_key = (key, split_width)
            if cache_key not in reason_cache:
                reason_cache[cache_key] = split_reason(
                    val(central_data, key), font_name, font_size, split_width
                )
            values[pdf_field] = reason_cache[cache_key][0 if transform == "reason_line_1" else 1]
        else:
            values[pdf_field] = format_value(val(central_data, key), key)
    return values


def render_filled_pdf(doc, central_data, font_key, font_size):
    pdf_path = DOCUMENTS_DIR / doc["filename"]
    reader = PdfReader(str(pdf_path))
    font_name = get_font_name(font_key)
    values = binding_values(doc, central_data, font_key, font_size, reader)
    overlay = BytesIO()
    c = canvas.Canvas(overlay)
    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        c.setPageSize((width, height))
        for field_name, rect in field_widgets(page):
            text = values.get(field_name, "")
            if not text:
                continue
            x0, y0, x1, y1 = rect
            available = max(10, x1 - x0 - 5)
            size = font_size
            while size > 7 and pdfmetrics.stringWidth(text, font_name, size) > available:
                size -= 0.5
            c.setFont(font_name, size)
            c.drawString(x0 + 2, y0 + max(2, (y1 - y0 - size) / 2), text)
        c.showPage()
    c.save()
    overlay.seek(0)
    overlay_reader = PdfReader(overlay)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for index, page in enumerate(writer.pages):
        page.merge_page(overlay_reader.pages[index])
        annotations = page.get("/Annots")
        if annotations:
            kept = [ref for ref in annotations if ref.get_object().get("/Subtype") != "/Widget"]
            if kept:
                page[NameObject("/Annots")] = ArrayObject(kept)
            else:
                page.pop(NameObject("/Annots"), None)
    out = BytesIO()
    writer.write(out)
    out.seek(0)
    return out


def safe_filename(company, requested=None):
    filename = (requested or "").strip()
    if not filename:
        filename = f"หนังสือบริษัท {company}" if company else "หนังสือบริษัท"
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "", filename).strip(" .")
    filename = re.sub(r"\.pdf$", "", filename, flags=re.IGNORECASE).strip(" .")
    reserved_name = filename.split(".", 1)[0].upper()
    if reserved_name in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?:COM|LPT)[1-9]", reserved_name):
        filename = "_" + filename
    return (filename or "หนังสือบริษัท")[:180] + ".pdf"


def common_context(**extra):
    active_step = extra.pop("active_step", None)
    context = {
        "font_options": FONT_OPTIONS,
        "accent_options": ACCENT_OPTIONS,
        "theme_options": THEME_OPTIONS,
        "default_font": DEFAULT_FONT,
        "default_font_size": DEFAULT_FONT_SIZE,
        "settings": current_settings(),
        "config_errors": CONFIG_ERRORS,
        "active_step": active_step,
        "progress_steps": build_progress(active_step) if active_step else [],
        "progress_percent": ((active_step - 1) / 3 * 100) if active_step else 0,
    }
    context.update(extra)
    return context


@app.post("/clear")
def clear_case():
    session.clear()
    return redirect(url_for("select_documents_page"))


@app.get("/")
def select_documents_page():
    return render_template("select_documents.html", **common_context(
        documents=DOCUMENTS,
        selected_ids=session.get("selected_documents", []),
        active_step=1,
    ))


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    settings = current_settings()
    error = None
    if request.method == "POST":
        font_key = request.form.get("font_name", DEFAULT_FONT)
        accent_key = request.form.get("accent", DEFAULT_ACCENT)
        theme_key = request.form.get("theme", DEFAULT_THEME)
        if font_key not in FONT_OPTIONS:
            error = "ฟอนต์ที่เลือกไม่ถูกต้อง"
        elif accent_key not in ACCENT_OPTIONS:
            error = "สีหลักที่เลือกไม่ถูกต้อง"
        elif theme_key not in THEME_OPTIONS:
            error = "ธีมที่เลือกไม่ถูกต้อง"
        else:
            settings = {
                **settings,
                "font_name": font_key,
                "font_size": normalize_font_size(request.form.get("font_size", DEFAULT_FONT_SIZE)),
                "accent": accent_key,
                "theme": theme_key,
            }
            session["settings"] = settings
            if session.get("case_data"):
                session["case_data"].update(settings)
                session.modified = True
            return redirect(request.form.get("next") if request.form.get("next") in {"/", "/form", "/review", "/export"} else url_for("data_form"))
    return render_template("settings.html", **common_context(settings=settings, error=error,
                                                             next_url=request.args.get("next", "/form")))


@app.post("/select")
def choose_documents():
    ids = request.form.getlist("documents")
    docs = selected_documents(ids)
    if not docs:
        return render_template(
            "select_documents.html", **common_context(documents=DOCUMENTS,
                                                       selected_ids=ids,
                                                       error="กรุณาเลือกเอกสารอย่างน้อย 1 ไฟล์",
                                                       active_step=1)
        ), 400
    session["selected_documents"] = [doc["id"] for doc in docs]
    session.pop("case_data", None)
    session.pop("output_filename", None)
    return redirect(url_for("data_form"))


@app.route("/form", methods=["GET", "POST"])
def data_form():
    docs = selected_documents(session.get("selected_documents", []))
    if not docs:
        return redirect(url_for("select_documents_page"))
    fields = selected_field_defs(docs)
    document_fields = [(doc, document_field_defs(doc)) for doc in docs]
    existing_data = session.get("case_data")
    data = dict(existing_data or {})
    previous_company = val(existing_data or {}, "company")
    if request.method == "GET" and not existing_data and any(key == "letter_date" for key, _ in fields):
        data["letter_date"] = datetime.now().astimezone().date().isoformat()
    error = None
    if request.method == "POST":
        data = {key: "" for key, _ in fields}
        invalid_dates = []
        invalid_lengths = []
        for doc, doc_fields in document_fields:
            for key, definition in doc_fields:
                field_name = f"document__{doc['id']}__{key}"
                value = request.form.get(field_name, "").strip()
                if len(value) > field_max_length(definition):
                    label = definition.get("label", key)
                    if label not in invalid_lengths:
                        invalid_lengths.append(label)
                    continue
                if definition.get("type") == "date" and value:
                    normalized_date = normalize_date_input(value)
                    if normalized_date is None:
                        invalid_dates.append(definition.get("label", key))
                        continue
                    value = normalized_date
                if not val(data, key) and value:
                    data[key] = value
        data.update(current_settings())
        invalid_numbers = [
            definition.get("label", key)
            for key, definition in fields
            if definition.get("type") == "number" and val(data, key)
            and not re.fullmatch(r"[0-9]+", val(data, key))
        ]
        validation_errors = []
        if invalid_lengths:
            validation_errors.append(
                "ข้อมูลยาวเกินขนาดที่กำหนด: " + ", ".join(invalid_lengths)
            )
        if invalid_numbers:
            validation_errors.append("กรุณาใส่เป็นตัวเลขเท่านั้น: " + ", ".join(invalid_numbers))
        if invalid_dates:
            validation_errors.append("กรุณาใส่วันที่เป็น วว/ดด/พ.ศ. เช่น 01/09/2569: " + ", ".join(invalid_dates))
        if validation_errors:
            error = " ".join(validation_errors)
        else:
            session["case_data"] = data
            if previous_company != val(data, "company"):
                session.pop("output_filename", None)
            return redirect(url_for("review"))
    return render_template(
        "form.html",
        **common_context(documents=docs, fields=fields, document_fields=document_fields,
                         data=data, document_status={doc["id"]: document_is_complete(doc, data) for doc in docs},
                         error=error, active_step=2),
    )


@app.route("/review", methods=["GET", "POST"])
def review():
    docs = selected_documents(session.get("selected_documents", []))
    if not docs or not session.get("case_data"):
        return redirect(url_for("select_documents_page"))
    if request.method == "POST":
        return redirect(url_for("export"))
    data = session["case_data"]
    document_fields = [(doc, document_field_defs(doc)) for doc in docs]
    document_status = {
        doc["id"]: document_is_complete(doc, data)
        for doc in docs
    }
    return render_template(
        "review.html",
        **common_context(
            documents=docs,
            document_fields=document_fields,
            document_status=document_status,
            data=data,
            active_step=3,
        ),
    )


@app.route("/export", methods=["GET", "POST"])
def export():
    if CONFIG_ERRORS:
        return "เอกสารใน config มีข้อผิดพลาด:\n" + "\n".join(CONFIG_ERRORS), 500, {"Content-Type": "text/plain; charset=utf-8"}
    docs = selected_documents(session.get("selected_documents", []))
    data = session.get("case_data", {})
    if not docs or not data:
        return redirect(url_for("select_documents_page"))
    default_output_filename = session.get("output_filename") or safe_filename(val(data, "company"))
    if request.method == "GET":
        return render_template("export.html", **common_context(
            documents=docs, data=data, output_filename=default_output_filename, active_step=4
        ))
    docs = apply_document_order(request.form.get("document_order"), docs)
    saved_settings = current_settings()
    font_key = request.form.get("font_name", saved_settings["font_name"])
    if font_key not in FONT_OPTIONS:
        return render_template("export.html", **common_context(
            documents=docs,
            data=data,
            output_filename=request.form.get("output_filename", default_output_filename),
            error="ฟอนต์ที่เลือกไม่ถูกต้อง",
            active_step=4,
        )), 400
    font_size = normalize_font_size(request.form.get("font_size", saved_settings["font_size"]))
    settings = {**saved_settings, "font_name": font_key, "font_size": font_size}
    session["settings"] = settings
    if session.get("case_data"):
        session["case_data"].update(settings)
        session.modified = True
    output_filename = safe_filename(val(data, "company"), request.form.get("output_filename"))
    session["output_filename"] = output_filename
    try:
        writer = PdfWriter()
        for doc in docs:
            filled = render_filled_pdf(doc, data, font_key, font_size)
            writer.append(PdfReader(filled))
        out = BytesIO()
        writer.write(out)
        out.seek(0)
    except Exception:
        app.logger.exception("PDF export failed for documents=%s", [doc["id"] for doc in docs])
        return render_template(
            "export.html",
            **common_context(
                documents=docs,
                data=data,
                output_filename=output_filename,
                error="สร้าง PDF ไม่สำเร็จ กรุณาตรวจสอบแม่แบบหรือข้อมูล แล้วลองใหม่อีกครั้ง",
                active_step=4,
            ),
        ), 500
    return send_file(out, as_attachment=True, download_name=output_filename, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
