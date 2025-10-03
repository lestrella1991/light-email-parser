import re, os, logging
import mailparser
import base64
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from typing import Dict, Any, List

UPLOAD_FOLDER = "uploads"
ALLOWED_EXT = {'eml'}
MAX_MB = 150

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_MB * 1024 * 1024  # max upload size

def allowed_filename(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXT

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])

def upload():
    """
    Espera archivos con nombre 'files[]' (multiple) o 'file' (single).
    Devuelve JSON con resultado por archivo.
    """
    results = []
    files = request.files.getlist('files[]') or request.files.getlist('file')
    if not files:
        return jsonify({'error': 'No files uploaded'}), 400

    for f in files:
        if f.filename == '':
            results.append({'filename': '', 'status': 'empty filename', 'ok': False})
            continue

        filename = secure_filename(f.filename)
        if not allowed_filename(filename):
            results.append({'filename': filename, 'status': 'extension not allowed', 'ok': False})
            continue

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Si querés evitar sobreescribir:
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(save_path):
            filename = f"{base}({counter}){ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter += 1

        f.save(save_path)

        try:
            raw_meta = parseEmail(save_path)  # puede ser dict o lista
        except Exception as e:
            # si parse falla, capturamos y seguimos
            logging.exception("parseEmail fallo")
            raw_meta = {"parse_error": str(e)}

        # Normalizar a dict
        if isinstance(raw_meta, list):
        # si es lista y tiene al menos un dict -> tomar el primero
            if len(raw_meta) > 0 and isinstance(raw_meta[0], dict):
                meta = raw_meta[0]
            else:
                meta = {}
        elif isinstance(raw_meta, dict):
                meta = raw_meta
        else:
            meta = {}

        results.append({
        "filename": filename,
        "status": "saved",
        "date": meta.get("date"),
        "from": meta.get("from"),
        "to": meta.get("to"),
        "subject": meta.get("subject"),
        "body": meta.get("body"),
        "attachments": meta.get("attachments")
        })

    return jsonify({'results': results})

def parseEmail(eml):
    mail = mailparser.parse_from_file(eml)
    body = mail.body
    print(body)
    to = mail.to[0][1]
    from_ = mail.from_[0][1]
    subject = mail.subject
    date_ = mail.date
    attachments = []
    attachments = mail.attachments
    URL_RE = re.compile(r'(https?://[^\s\)<>"\'\]]+|www\.[^\s\)<>"\'\]]+)', re.IGNORECASE)
    items = []
    urls = ""
    if attachments:
        for a in attachments:
            if "pdf" in a['mail_content_type'] or "octet-stream" in a['mail_content_type'] :
                payload = base64.b64decode(a['payload']).decode('latin-1')
                name = a['filename']
                urls = set(m.group(0).rstrip(').,;\'"') for m in URL_RE.finditer(payload))
                if len(urls) <=1:
                    url = next(iter(urls))
                    items.append({"filename":name,"url":url})
                else:
                    extracted_urls= ",".join(sorted(urls))
                    print(extracted_urls)
                    items.append({"filename":name,"urls":extracted_urls})
    
    meta = []
    meta.append({
        "from": from_,
        "to": to,
        "subject": subject,
        "date": date_,
        "body": body,
        "attachments": items
    })

    return meta
        

    


# opcional: servir archivos subidos (solo para demo)
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    # En desarrollo se puede usar debug, en prod no
    app.run(host='0.0.0.0', port=5000, debug=True)
