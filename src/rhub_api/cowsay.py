from flask import Blueprint, make_response, abort

import rhub_cowsay

blueprint = Blueprint('cowsay', __name__)

@blueprint.route('/chars')
def chars():
    response = make_response(str(rhub_cowsay.chars))
    response.headers['content-type'] = 'text/plain'
    return response

@blueprint.route('/chars/<char>')
@blueprint.route('/', strict_slashes=False)
def char(char='cow'):
    if not rhub_cowsay.char_exists(char):
        abort(404)
    response = make_response(rhub_cowsay.cowsay_to_string(char))
    response.headers['content-type'] = 'text/plain'
    return response
