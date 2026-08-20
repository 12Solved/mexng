import os
import pathlib

from mailextractor.app.config import config

FILE_EXTRACT_PATH = config.FILE_EXTRACT_PATH


def resolve_and_validate_path(file_path):
    """Resolves file_path to an absolute path and enforces that it stays
    inside FILE_EXTRACT_PATH. Raises if it doesn't."""
    real_path = os.path.abspath(file_path)
    dirname = os.path.dirname(real_path)
    if not os.path.commonpath([FILE_EXTRACT_PATH, real_path, dirname]) == FILE_EXTRACT_PATH:
        raise Exception("{} does not start with FILE_EXTRACT_PATH={}".format(
                real_path, config.FILE_EXTRACT_PATH
            ))
    return real_path


def secure_save_file(file_path, file_content, create_parent = False):
    real_path = resolve_and_validate_path(file_path)
    dirname = os.path.dirname(real_path)
    filename = os.path.basename(real_path)
    if create_parent:
        os.makedirs(dirname, exist_ok=True)
    if filename:
        with open(real_path, "wb", os.O_NOFOLLOW) as f:
            f.write(file_content)
    return real_path

