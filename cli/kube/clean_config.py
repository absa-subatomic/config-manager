import logging
import os
import shutil
import sys
from os import path

import click


def configure_logging():
    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logger_instance = logging.getLogger("clean_config")
    stderr = logging.StreamHandler(sys.stdout)
    stderr.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
    stderr.setLevel(logging.DEBUG)
    logger_instance.addHandler(stderr)
    return logger_instance


log = configure_logging()


@click.command(name="clean", help="Remove local config")
def clean_config():
    cwd = os.getcwd()

    config_directory = path.join(cwd, "local-config")
    if os.path.exists(config_directory) and os.path.isdir(config_directory):
        shutil.rmtree(config_directory)
