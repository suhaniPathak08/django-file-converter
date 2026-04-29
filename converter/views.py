import os
import subprocess
from django.shortcuts import render
from django.http import FileResponse
from django.conf import settings
from .forms import UploadFileForm


UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'uploads')
CONVERTED_DIR = os.path.join(settings.MEDIA_ROOT, 'converted')


def index(request):
    form = UploadFileForm()
    return render(request, 'converter/index.html', {'form': form})


def convert_file(request):
    if request.method != 'POST':
        return render(request, 'converter/index.html', {'form': UploadFileForm()})

    form = UploadFileForm(request.POST, request.FILES)

    if not form.is_valid():
        return render(request, 'converter/index.html', {
            'form': form,
            'error': 'Invalid form submission.'
        })

    uploaded_file = request.FILES['file']
    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ['.pdf', '.docx']:
        return render(request, 'converter/index.html', {
            'form': UploadFileForm(),
            'error': 'Only .pdf and .docx files are supported.'
        })

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CONVERTED_DIR, exist_ok=True)

    upload_path = os.path.join(UPLOAD_DIR, filename)

    # Save uploaded file
    with open(upload_path, 'wb+') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    base_name = os.path.splitext(filename)[0]

    try:
        # ✅ PDF → DOCX
        if ext == '.pdf':
            output_filename = base_name + '.docx'
            output_path = os.path.join(CONVERTED_DIR, output_filename)

            from pdf2docx import Converter
            cv = Converter(upload_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()

        # ✅ DOCX → PDF using LibreOffice
        elif ext == '.docx':
            output_filename = base_name + '.pdf'
            output_path = os.path.join(CONVERTED_DIR, output_filename)

            # Run LibreOffice command
            subprocess.run([
                "soffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", CONVERTED_DIR,
                upload_path
            ], check=True)

            # LibreOffice saves with same base name
            output_path = os.path.join(CONVERTED_DIR, base_name + ".pdf")

    except Exception as e:
        return render(request, 'converter/index.html', {
            'form': UploadFileForm(),
            'error': f'Conversion failed: {str(e)}'
        })

    if not os.path.exists(output_path):
        return render(request, 'converter/index.html', {
            'form': UploadFileForm(),
            'error': 'Conversion failed: output file not created.'
        })

    return FileResponse(open(output_path, 'rb'), as_attachment=True, filename=output_filename)