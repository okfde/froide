import os
import tempfile
import subprocess
import logging


def convert_to_pdf(filepath, binary_name=None, construct_call=None):
    if binary_name is None and construct_call is None:
        return
    outpath = tempfile.mkdtemp()
    path, filename = os.path.split(filepath)
    name, extension = filename.rsplit('.', 1)
    output_file = os.path.join(outpath, '%s.pdf' % name)
    arguments = [
        binary_name,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        outpath,
        filepath
    ]
    if construct_call is not None:
        arguments, output_file = construct_call(filepath, outpath)

    # Set different HOME so libreoffice can write to it
    env = dict(os.environ)
    env.update({'HOME': outpath})

    p = subprocess.Popen(
        arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    out, err = p.communicate()
    p.wait()
    if p.returncode == 0:
        if os.path.exists(output_file):
            return output_file
    else:
        logging.error("Error during Doc to PDF conversion: %s", err)
    return None
