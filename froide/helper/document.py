import os
import tempfile
import subprocess
import shutil
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
    'image/gif'
)

TEXT_FILETYPES = (
    'application/text-plain:formatted',
    'text/plain'
)

EMBEDDABLE_FILETYPES = (
    PDF_FILETYPES +
    IMAGE_FILETYPES
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
    try:
        output_file = shell_call(arguments, outpath, output_file, timeout=timeout)
        return output_file
    except Exception as err:
        logging.error("Error during Doc to PDF conversion: %s", err)
    return None


def shell_call(arguments, outpath, output_file, timeout=50):
    env = dict(os.environ)
    env.update({'HOME': outpath})

    logging.info("Running: %s", arguments)
    logging.info("Env: %s", env)
    out, err = '', ''
    p = None
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
        if p is not None:
            p.kill()
            out, err = p.communicate()
    finally:
        if p is not None and p.returncode is None:
            p.kill()
            out, err = p.communicate()
    if p is not None and p.returncode == 0:
        if os.path.exists(output_file):
            return output_file
    raise Exception(err)


def decrypt_pdf_in_place(filename, timeout=50):
    try:
        temp_dir = tempfile.mkdtemp()

        # I'm not sure if a qpdf failure could leave the file in a halfway
        # state, so have it write to a temporary file instead of reading from one
        temp_out = os.path.join(temp_dir, 'qpdf_out.pdf')

        arguments = ['qpdf', '--decrypt', filename, temp_out]
        output_file = shell_call(arguments, temp_dir, temp_out, timeout=timeout)

        # I'm not sure if a qpdf failure could leave the file in a halfway
        # state, so write to a temporary file and then use os.rename to
        # overwrite the original atomically.
        # (We use shutil.move instead of os.rename so it'll fall back to a copy
        #  operation if the dir= argument to mkdtemp() gets removed)
        shutil.move(output_file, filename)
        return filename
    except Exception as err:
        logging.error("Error during PDF decryption %s", err)
        return None
    finally:
        # Delete all temporary files
        shutil.rmtree(temp_dir)
