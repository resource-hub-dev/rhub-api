from flask import Flask, abort

from rhub.api import cowsay

app = Flask(__name__)

app.register_blueprint(cowsay.blueprint, url_prefix='/cowsay')

@app.route('/')
def index():
    abort(501)
