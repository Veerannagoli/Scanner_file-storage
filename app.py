import os
import sqlite3
import qrcode
import uuid
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------- Paths ----------
UPLOAD_FOLDER = "static/uploads"
QRCODE_FOLDER = "static/qrcodes"
DB_FILE = "database.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QRCODE_FOLDER, exist_ok=True)

# ---------- Database Setup ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    pin TEXT,
                    filenames TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# ---------- Routes ----------
@app.route("/")
def home():
    return render_template("create.html")

@app.route("/create", methods=["POST"])
def create():
    name = request.form["name"]
    pin = request.form["pin"]
    files = request.files.getlist("file")

    if not files or files[0].filename == "":
        flash("No files uploaded!")
        return redirect(url_for("home"))

    unique_id = str(uuid.uuid4())
    saved_files = []

    for file in files:
        filename = unique_id + "_" + file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        saved_files.append(filename)

    # Save to DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO files (id, name, pin, filenames) VALUES (?, ?, ?, ?)",
              (unique_id, name, pin, ",".join(saved_files)))
    conn.commit()
    conn.close()

    # Generate QR Code (stores URL)
    qr_url = request.url_root + "view/" + unique_id
    qr_img = qrcode.make(qr_url)
    qr_path = os.path.join(QRCODE_FOLDER, f"{unique_id}.png")
    qr_img.save(qr_path)

    # Use relative path for cloud deployment
    qr_image_relative = f"qrcodes/{unique_id}.png"
    return render_template("success.html", qr_image=qr_image_relative, qr_url=qr_url)

@app.route("/view/<file_id>", methods=["GET", "POST"])
def view(file_id):
    if request.method == "POST":
        entered_pin = request.form["pin"]

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT filenames, pin FROM files WHERE id=?", (file_id,))
        row = c.fetchone()
        conn.close()

        if row:
            filenames, correct_pin = row
            if entered_pin == correct_pin:
                file_list = filenames.split(",")
                return render_template("downloads.html", files=file_list)
            else:
                flash("❌ Incorrect PIN!")
                return redirect(url_for("view", file_id=file_id))
        else:
            return "File not found", 404

    return render_template("view.html", file_id=file_id)

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ---------- Run Application ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use dynamic port for cloud deployment
    app.run(host="0.0.0.0", port=port, debug=True)
