import os
import tempfile
import subprocess
import logging

try:
    TimeoutExpired = subprocess.TimeoutExpired
    HAS_TIMEOUT = True
except AttributeError:
    # Python 2
    TimeoutExpired = Exception
    HAS_TIMEOUT = False


OFFICE_FILETYPES = (
    'application/msexcel',
    'application/vnd.ms-excel',
    'application/msword',
    'application/vnd.msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
)
OFFICE_EXTENSIONS = (
    '.doc',
    '.docx',
    '.odt'
)

PDF_FILETYPES = (
    'application/pdf',
    'application/x-pdf',
    'pdf/application',
    'application/acrobat',
    'applications/vnd.pdf',
    'text/pdf',
    'text/x-pdf'
)

IMAGE_FILETYPES = (
    'image/png',
    'image/jpeg',
    'image/jpg',
)

TEXT_FILETYPES = (
    'application/text-plain:formatted',
    'text/plain'
)

POSTAL_CONTENT_TYPES = PDF_FILETYPES + IMAGE_FILETYPES


def can_convert_to_pdf(filetype, name=None):
    return filetype.lower() in OFFICE_FILETYPES or (
        name is not None and name.lower().endswith(OFFICE_EXTENSIONS))


def convert_to_pdf(filepath, binary_name=None, construct_call=None, timeout=50):
    if binary_name is None and construct_call is None:
        return
    outpath = tempfile.mkdtemp()
    path, filename = os.path.split(filepath)
    name, extension = filename.rsplit('.', 1)
    output_file = os.path.join(outpath, '%s.pdf' % name)
    arguments = [
        binary_name,
        '--headless',
        '--nodefault',
        '--nofirststartwizard',
        '--nolockcheck',
        '--nologo',
        '--norestore',
        '--invisible',
        '--convert-to',
        'pdf',
        '--outdir',
        outpath,
        filepath
    ]
    if construct_call is not None:
        arguments, output_file = construct_call(filepath, outpath)

    # Set different HOME so libreoffice can write to it
    env = dict(os.environ)
    env.update({'HOME': outpath})

    logging.info("Running: %s", ' '.join(arguments))
    logging.info("Env: %s", env)
    out, err = '', ''
    try:
        p = subprocess.Popen(
            arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        kwargs = {}
        if HAS_TIMEOUT:
            kwargs['timeout'] = timeout

        out, err = p.communicate(**kwargs)
        p.wait()
    except TimeoutExpired:
        p.kill()
        out, err = p.communicate()
    finally:
        if p.returncode is None:
            p.kill()
            out, err = p.communicate()
    if p.returncode == 0:
        if os.path.exists(output_file):
            return output_file
    else:
        logging.error("Error during Doc to PDF conversion: %s", err)
    logging.error(err)
    return None
