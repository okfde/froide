import os
import tempfile
import subprocess
import logging

try:
    TimeoutExpired = subprocess.TimeoutExpired
    HAS_TIMEOUT = True
except AttributeError:
    TimeoutExpired = Exception
    HAS_TIMEOUT = False


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
