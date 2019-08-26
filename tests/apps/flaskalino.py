#!/usr/bin/env python
# -*- coding: utf-8 -*-
import opentracing.ext.tags as ext
from flask import Flask, redirect, render_template, render_template_string
from wsgiref.simple_server import make_server
from flask import jsonify

from instana.singletons import tracer
from ..helpers import testenv

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

testenv["wsgi_port"] = 10811
testenv["wsgi_server"] = ("http://127.0.0.1:" + str(testenv["wsgi_port"]))

app = Flask(__name__)
app.debug = False
app.use_reloader = False

flask_server = make_server('127.0.0.1', testenv["wsgi_port"], app.wsgi_app)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.route("/")
def hello():
    return "<center><h1>🐍 Hello Stan! 🦄</h1></center>"


@app.route("/complex")
def gen_opentracing():
    with tracer.start_active_span('asteroid') as pscope:
        pscope.span.set_tag(ext.COMPONENT, "Python simple example app")
        pscope.span.set_tag(ext.SPAN_KIND, ext.SPAN_KIND_RPC_SERVER)
        pscope.span.set_tag(ext.PEER_HOSTNAME, "localhost")
        pscope.span.set_tag(ext.HTTP_URL, "/python/simple/one")
        pscope.span.set_tag(ext.HTTP_METHOD, "GET")
        pscope.span.set_tag(ext.HTTP_STATUS_CODE, 200)
        pscope.span.log_kv({"foo": "bar"})

        with tracer.start_active_span('spacedust', child_of=pscope.span) as cscope:
            cscope.span.set_tag(ext.SPAN_KIND, ext.SPAN_KIND_RPC_CLIENT)
            cscope.span.set_tag(ext.PEER_HOSTNAME, "localhost")
            cscope.span.set_tag(ext.HTTP_URL, "/python/simple/two")
            cscope.span.set_tag(ext.HTTP_METHOD, "POST")
            cscope.span.set_tag(ext.HTTP_STATUS_CODE, 204)
            cscope.span.set_baggage_item("someBaggage", "someValue")

    return "<center><h1>🐍 Generated some OT spans... 🦄</h1></center>"


@app.route("/301")
def threehundredone():
    return redirect('/', code=301)


@app.route("/302")
def threehundredtwo():
    return redirect('/', code=302)


@app.route("/400")
def fourhundred():
    return "Simulated Bad Request", 400


@app.route("/405")
def fourhundredfive():
    return "Simulated Method not allowed", 405


@app.route("/500")
def fivehundred():
    return "Simulated Internal Server Error", 500


@app.route("/504")
def fivehundredfour():
    return "Simulated Gateway Timeout", 504


@app.route("/exception")
def exception():
    raise Exception('fake error')


@app.route("/exception-invalid-usage")
def exception_invalid_usage():
    raise InvalidUsage("Simulated custom exception", status_code=502)


@app.route("/render")
def render():
    return render_template('flask_render_template.html', name="Peter")


@app.route("/render_string")
def render_string():
    return render_template_string('hello {{ what }}', what='world')


@app.route("/render_error")
def render_error():
    return render_template('flask_render_error.html', what='world')


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    logger.error("InvalidUsage error handler invoked")
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


if __name__ == '__main__':
    flask_server.serve_forever()
