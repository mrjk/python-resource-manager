import json
import logging
import os
import re
from pathlib import Path

import yaml


log = logging.getLogger(__name__)


def from_json(string):
    "Transform JSON string to python dict"
    return json.loads(string)


def to_json(obj, nice=True):
    "Transform JSON string to python dict"
    if nice:
        return json.dumps(obj, indent=2)
    return json.dumps(obj)


def from_yaml(string, strip_last=False):
    "Transform YAML string to python dict"
    data = yaml.safe_load(string)
    if strip_last:
        return data.rstrip()
    return data


def to_yaml(obj, strip_last=False):
    "Transform obj to YAML"
    data = yaml.dump(obj)
    if strip_last:
        return data.rstrip()
    return data

    # # Ruamel support
    # options = {}
    # string_stream = StringIO()

    # if isinstance(obj, str):
    #     obj = json.loads(obj)

    # yaml.dump(obj, string_stream, **options)
    # output_str = string_stream.getvalue()
    # string_stream.close()
    # if not headers:
    #     output_str = output_str.split("\n", 2)[2]
    # return output_str



def read_file(file):
    "Read file content, accept pathlib objects"
    file = str(file) if isinstance(file, Path) else file
    with open(file, encoding="utf-8") as _file:
        return "".join(_file.readlines())


def write_file(file, content):
    "Write content to file, accept pathlib objects"

    file = str(file) if isinstance(file, Path) else file
    file_folder = os.path.dirname(file)
    if not os.path.exists(file_folder):
        os.makedirs(file_folder)

    with open(file, "w", encoding="utf-8") as _file:
        _file.write(content)

