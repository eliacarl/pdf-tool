from flask import Flask, request, send_file, render_template
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from io import BytesIO
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

def parse_pages(pages_str, total_pages):
    """Wandelt eine Zeichenkette wie '1,3-5' in eine Liste von Seiten-Indices (beginnend bei 0) um"""
    pages = set()
    if not pages_str:
        return list(range(total_pages))

    for part in pages_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            pages.update(range(int(start) - 1, int(end)))
        else:
            pages.add(int(part) - 1)

    return sorted([p for p in pages if 0 <= p < total_pages])

def generate_output_filename(uploaded_file, prefix, user_input=None):
    """Generiert einen sicheren PDF-Dateinamen mit optionalem Benutzerinput"""
    if user_input:
        if not user_input.lower().endswith(".pdf"):
            user_input += ".pdf"
        return secure_filename(user_input)
    base_name = os.path.splitext(uploaded_file.filename)[0]
    return secure_filename(f"{prefix}_{base_name}.pdf")

@app.route('/')
def index():
    return render_template('index.html')

### MERGE
@app.route('/merge', methods=['POST'])
def merge():
    files = request.files.getlist('pdfs')
    user_input = request.form.get('filename')

    if not user_input:
        base_names = [os.path.splitext(file.filename)[0] for file in files if file.filename]
        filename = secure_filename("merged_" + "_".join(base_names) + ".pdf")
    else:
        filename = secure_filename(user_input if user_input.lower().endswith('.pdf') else user_input + '.pdf')

    pages_str = request.form.get('pages')
    merger = PdfMerger()

    for file in files:
        reader = PdfReader(file)
        total_pages = len(reader.pages)
        pages = parse_pages(pages_str, total_pages)

        writer = PdfWriter()
        for i in pages:
            writer.add_page(reader.pages[i])

        pdf_bytes = BytesIO()
        writer.write(pdf_bytes)
        pdf_bytes.seek(0)
        merger.append(pdf_bytes)

    output = BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

### SPLIT
@app.route('/split', methods=['POST'])
def split():
    file = request.files['pdf']
    reader = PdfReader(file)
    pages_str = request.form.get('pages', '')
    selected_pages = parse_pages(pages_str, len(reader.pages))

    writer = PdfWriter()
    for i in selected_pages:
        writer.add_page(reader.pages[i])

    filename = generate_output_filename(file, "split", request.form.get("filename"))

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

### ROTATE
@app.route('/rotate', methods=['POST'])
def rotate():
    file = request.files['pdf']
    angle = int(request.form.get('angle', 90))
    pages_str = request.form.get('pages', '')
    reader = PdfReader(file)
    writer = PdfWriter()
    selected_pages = parse_pages(pages_str, len(reader.pages))

    for i, page in enumerate(reader.pages):
        if i in selected_pages:
            page.rotate(angle)
        writer.add_page(page)

    filename = generate_output_filename(file, "rotated", request.form.get("filename"))

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

### REMOVE PAGES
@app.route('/remove-pages', methods=['POST'])
def remove_pages():
    file = request.files['pdf']
    pages_str = request.form.get('pages', '')
    reader = PdfReader(file)
    writer = PdfWriter()

    total_pages = len(reader.pages)
    remove_set = set(parse_pages(pages_str, total_pages))

    for i, page in enumerate(reader.pages):
        if i not in remove_set:
            writer.add_page(page)

    filename = generate_output_filename(file, "removed", request.form.get("filename"))

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
