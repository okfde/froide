import os
import base64
import tempfile
import subprocess


def convert_to_pdf(post):
    path = tempfile.mkdtemp()
    pagenr = 1
    while True:
        data = post.get('page_%s' % pagenr)
        if data is None:
            break
        if not data.startswith('data:image/png;base64,'):
            continue
        prefix, data = data.split(',', 1)
        filename = os.path.join(path, 'page_%03d.png' % pagenr)
        file(filename, 'w').write(base64.b64decode(data))
        pagenr += 1
    filename = os.path.join(path, 'page_*')
    output_file = os.path.join(path, 'final.pdf')
    if subprocess.call(["convert", filename, output_file]) == 0:
        return output_file
    return None
