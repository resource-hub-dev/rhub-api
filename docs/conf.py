# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys


docs_path = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.abspath(os.path.join(docs_path, '..', 'src'))

sys.path.insert(0, src_path)


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
