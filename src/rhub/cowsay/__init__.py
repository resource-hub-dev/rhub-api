import cowsay
import io
import contextlib

chars = cowsay.char_names

def char_exists(char):
    return char in chars

def cowsay_to_string(char):
    string = io.StringIO()
    with contextlib.redirect_stdout(string):
        getattr(cowsay, char)('Hello Resource Hub!')
    return string.getvalue()
