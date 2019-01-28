import os
from flask import json


def load_data(filename):
    root = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(root, "static/", filename)
    data = json.load(open(json_url))
    return data


def stream_template(app, template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    return rv
