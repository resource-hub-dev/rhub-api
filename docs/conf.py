# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import pathlib

import sh
import requests
from sphinx.util import logging


logger = logging.getLogger(__name__)

# -- Path setup --------------------------------------------------------------

docs_path = pathlib.Path(__file__).parent.resolve()
src_path = pathlib.Path(docs_path / '..' / 'src').resolve()

sys.path.insert(0, str(src_path))


# -- Project information -----------------------------------------------------

project = 'Resource Hub'
copyright = '2021, Red Hat, Inc.'
author = 'Red Hat, Inc.'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx_rtd_theme',
    'sphinxcontrib.swaggerui',
    'reno.sphinxext',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

autodoc_default_options = {
    'special-members': '__init__, __tablename__',
}


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['custom.css']


# -- Event hooks -------------------------------------------------------------

def download(url, path):
    if not path.exists():
        logger.info(f'Downloading "{url!s}" to "{path!s}"')
        with requests.get(url, stream=True) as r, path.open('wb') as f:
            for c in r.iter_content(chunk_size=8192):
                f.write(c)


def hook_init(app):
    logger.info('Building code API' + str(src_path))
    sh.sphinx_apidoc(
        src_path / 'rhub',
        implicit_namespaces=True,
        doc_project='Code API reference',
        output_dir=docs_path / 'api-code',
        _fg=True,
    )

    os.makedirs(docs_path / '_static' / 'swaggerui', exist_ok=True)
    download('https://unpkg.com/swagger-ui-dist@3.51.1/swagger-ui.css',
             docs_path / '_static' / 'swaggerui' / 'swagger-ui.css')

    logger.info('Building OpenAPI spec file')
    sh.prance.compile(
        src_path / 'openapi' / 'openapi.yml',
        docs_path / '_static' / 'swaggerui' / 'openapi.json',
        _fg=True,
    )


def setup(app):
    app.connect('builder-inited', hook_init)
