from flask import Blueprint, make_response, abort

import rhub.cowsay

blueprint = Blueprint('cowsay', __name__)

@blueprint.route('/chars')
def chars():
    response = make_response(str(rhub.cowsay.chars))
    response.headers['content-type'] = 'text/plain'
    return response

@blueprint.route('/chars/<char>')
@blueprint.route('/', strict_slashes=False)
def char(char='cow'):
    if not rhub.cowsay.char_exists(char):
        abort(404)
    response = make_response(rhub.cowsay.cowsay_to_string(char))
    response.headers['content-type'] = 'text/plain'
    return response
