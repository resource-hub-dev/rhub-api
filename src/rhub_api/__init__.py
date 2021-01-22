from flask import Flask, abort

import rhub_api.cowsay

app = Flask(__name__)

app.register_blueprint(rhub_api.cowsay.blueprint, url_prefix='/cowsay')

@app.route('/')
def index():
    abort(501)
