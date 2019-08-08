import logging
import os
import subprocess


def shell_call(arguments, outpath, output_file=None, timeout=50):
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

        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if p is not None:
            p.kill()
            out, err = p.communicate()
    finally:
        if p is not None and p.returncode is None:
            p.kill()
            out, err = p.communicate()
    if p is not None and p.returncode == 0:
        if output_file is not None and os.path.exists(output_file):
            with open(output_file, 'rb') as f:
                return f.read()
    if output_file is not None:
        raise Exception(err)
