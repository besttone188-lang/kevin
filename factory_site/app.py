from __future__ import annotations

import csv
import json
import os
import smtplib
from datetime import datetime, timezone
from pathlib import Path
from email.message import EmailMessage
from io import BytesIO, StringIO

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INQUIRY_JSONL = DATA_DIR / "inquiries.jsonl"
INQUIRY_CSV = DATA_DIR / "inquiries.csv"
INQUIRY_STATUSES = ["New", "Contacted", "Quoted", "Sample Sent", "Order Won", "No Fit"]
DEFAULT_ADMIN_PASSWORD_HASH = "pbkdf2:sha256:260000$chNoEjBH8kiAsije$c290c0bdf9ff00f8f947468ba64490729f0e445e3af7fac4d6be28bee1c5324a"
DEFAULT_STATIC_ORIGIN = "https://meihua-musical-instruments.onrender.com"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FACTORY_SITE_SECRET", "local-factory-site")


PRODUCT_LINES = [
    {
        "name": "Electric Guitars",
        "image": "images/electric-guitars.png",
        "types": ["ST", "TL", "LP", "SG", "Offset", "Semi-hollow", "Bass"],
        "description": "Solid and semi-hollow electric guitars with precision pickups and electronics for rock, blues, jazz, metal and custom brand orders.",
        "options": ["Solid or semi-hollow body construction", "Pickup, electronics and hardware configuration", "ST, TL, LP, SG, Offset and bass models", "Gloss, matte, metallic and custom finishes"],
    },
    {
        "name": "Acoustic Guitars",
        "image": "images/acoustic-guitars.png",
        "types": ["Dreadnought", "OM", "GA", "Jumbo", "Parlor"],
        "description": "Acoustic guitars from dreadnoughts to concert and parlor models, designed for warm tone, reliable durability and B2B supply.",
        "options": ["Dreadnought, OM, GA, Jumbo and Parlor bodies", "Traditional and modern acoustic designs", "Cutaway and non-cutaway options", "Binding, rosette, pickup and finish customization"],
    },
    {
        "name": "Ukuleles",
        "image": "images/ukuleles.png",
        "types": ["21寸", "23寸", "26寸"],
        "description": "21-inch, 23-inch and 26-inch ukuleles in traditional and contemporary designs, lightweight, bright and fun to play.",
        "options": ["21-inch, 23-inch and 26-inch sizes", "Traditional or contemporary styling", "Logo, color and accessory bundle options", "Retail box or bulk carton packing"],
    },
]


def inquiry_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")


def normalize_inquiry(row: dict[str, str], index: int = 0) -> dict[str, str]:
    normalized = {key: "" if value is None else str(value) for key, value in row.items()}
    normalized.setdefault("id", f"legacy-{index}")
    normalized.setdefault("status", "New")
    normalized.setdefault("notes", "")
    normalized.setdefault("next_follow_up", "")
    normalized.setdefault("last_updated", normalized.get("created_at", ""))
    normalized.setdefault("body_type", "")
    normalized.setdefault("quantity", "")
    normalized.setdefault("target_price", "")
    normalized.setdefault("phone", "")
    normalized.setdefault("country", "")
    return normalized


def read_inquiries() -> list[dict[str, str]]:
    if not INQUIRY_JSONL.exists():
        return []
    rows = []
    for index, line in enumerate(INQUIRY_JSONL.read_text(encoding="utf-8").splitlines()):
        if line.strip():
            rows.append(normalize_inquiry(json.loads(line), index=index))
    return list(reversed(rows))


def write_inquiries(rows: list[dict[str, str]]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    chronological = list(reversed(rows))
    with INQUIRY_JSONL.open("w", encoding="utf-8") as file:
        for row in chronological:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    if not chronological:
        return
    fieldnames = list(chronological[0].keys())
    with INQUIRY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(chronological)


def save_inquiry(payload: dict[str, str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with INQUIRY_JSONL.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    file_exists = INQUIRY_CSV.exists()
    with INQUIRY_CSV.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(payload.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(payload)


def send_inquiry_alert(inquiry: dict[str, str]) -> None:
    smtp_host = os.environ.get("FACTORY_SMTP_HOST", "smtp.gmail.com")
    smtp_user = os.environ.get("FACTORY_SMTP_USER", "besttone188@gmail.com")
    smtp_password = os.environ.get("FACTORY_SMTP_PASSWORD")
    alert_to = os.environ.get("FACTORY_ALERT_EMAIL", "besttone188@gmail.com")
    if not all([smtp_host, smtp_user, smtp_password, alert_to]):
        return

    message = EmailMessage()
    product = inquiry.get("product_interest", "Product")
    company = inquiry.get("company", "Unknown company")
    message["Subject"] = f"New Meihua inquiry: {product} from {company}"
    message["From"] = smtp_user
    message["To"] = alert_to
    if inquiry.get("email"):
        message["Reply-To"] = inquiry["email"]
    message.set_content(
        "\n".join(
            [
                "A new purchase requirement was submitted on meihuamusical.com.",
                "",
                f"Name: {inquiry['name']}",
                f"Email: {inquiry['email']}",
                f"Company: {inquiry['company']}",
                f"Country: {inquiry['country']}",
                f"Phone: {inquiry['phone']}",
                f"Product: {inquiry['product_interest']}",
                f"Body Type: {inquiry['body_type']}",
                f"Quantity: {inquiry['quantity']}",
                f"Target Price: {inquiry['target_price']}",
                "",
                "Purchase Requirement:",
                inquiry["message"],
                "",
                "Admin: https://meihuamusical.com/admin?password=666888",
            ]
        )
    )
    smtp_port = int(os.environ.get("FACTORY_SMTP_PORT", "587"))
    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


def is_admin_password(password: str) -> bool:
    if check_password_hash(DEFAULT_ADMIN_PASSWORD_HASH, password):
        return True
    configured_password = os.environ.get("FACTORY_ADMIN_PASSWORD")
    if configured_password:
        return password == configured_password
    configured_hash = os.environ.get("FACTORY_ADMIN_PASSWORD_HASH", DEFAULT_ADMIN_PASSWORD_HASH)
    return check_password_hash(configured_hash, password)


def asset_url(filename: str) -> str:
    static_origin = os.environ.get("FACTORY_STATIC_ORIGIN", "").rstrip("/")
    if not static_origin and request.host in {"meihuamusical.com", "www.meihuamusical.com"}:
        static_origin = DEFAULT_STATIC_ORIGIN
    if static_origin:
        return f"{static_origin}/static/{filename.lstrip('/')}"
    return url_for("static", filename=filename)


@app.context_processor
def inject_asset_url():
    return {"asset_url": asset_url}


@app.get("/")
def home():
    return render_template("index.html", product_lines=PRODUCT_LINES)


@app.post("/api/inquiries")
def create_inquiry():
    form = request.form
    required_fields = ["name", "email", "company", "product_interest", "message"]
    missing = [field for field in required_fields if not form.get(field, "").strip()]
    if missing:
        return jsonify({"ok": False, "message": "Please complete the required fields."}), 400

    inquiry = {
        "id": inquiry_id(),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "New",
        "notes": "",
        "next_follow_up": "",
        "name": form.get("name", "").strip(),
        "email": form.get("email", "").strip(),
        "company": form.get("company", "").strip(),
        "country": form.get("country", "").strip(),
        "phone": form.get("phone", "").strip(),
        "product_interest": form.get("product_interest", "").strip(),
        "body_type": form.get("body_type", "").strip(),
        "quantity": form.get("quantity", "").strip(),
        "target_price": form.get("target_price", "").strip(),
        "message": form.get("message", "").strip(),
    }
    save_inquiry(inquiry)
    try:
        send_inquiry_alert(inquiry)
    except Exception:
        app.logger.exception("Failed to send inquiry alert")
    return jsonify({"ok": True, "message": "Thank you. We will review your request and reply soon."})


@app.get("/admin")
def admin():
    password = request.args.get("password", "")
    authorized = is_admin_password(password)
    rows = read_inquiries()
    status_filter = request.args.get("status", "")
    if status_filter:
        rows = [row for row in rows if row.get("status") == status_filter]
    return render_template(
        "admin.html",
        authorized=authorized,
        inquiries=rows,
        statuses=INQUIRY_STATUSES,
        status_filter=status_filter,
        password=password,
    )


@app.post("/admin/inquiries/<inquiry_id_value>")
def update_inquiry(inquiry_id_value: str):
    password = request.form.get("password", "")
    if not is_admin_password(password):
        return redirect(url_for("admin"))

    rows = read_inquiries()
    for row in rows:
        if row.get("id") == inquiry_id_value:
            row["status"] = request.form.get("status", row.get("status", "New"))
            row["notes"] = request.form.get("notes", "").strip()
            row["next_follow_up"] = request.form.get("next_follow_up", "").strip()
            row["last_updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            break
    write_inquiries(rows)
    return redirect(url_for("admin", password=password, status=request.form.get("status_filter", "")))


@app.get("/admin/export/<kind>")
def export_inquiries(kind: str):
    password = request.args.get("password", "")
    if not is_admin_password(password):
        return redirect(url_for("admin"))

    rows = read_inquiries()
    export_fields = [
        "created_at",
        "status",
        "next_follow_up",
        "name",
        "email",
        "phone",
        "company",
        "country",
        "product_interest",
        "body_type",
        "quantity",
        "target_price",
        "message",
        "notes",
    ]

    if kind == "csv":
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=export_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in export_fields})
        output = BytesIO(buffer.getvalue().encode("utf-8-sig"))
        return send_file(output, as_attachment=True, download_name="meihua-inquiries.csv", mimetype="text/csv")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inquiries"
    sheet.append(export_fields)
    for row in rows:
        sheet.append([row.get(field, "") for field in export_fields])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="meihua-inquiries.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    host = os.environ.get("FACTORY_SITE_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("FACTORY_SITE_PORT", "5060")))
    app.run(host=host, port=port, debug=False)
