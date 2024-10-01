# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
import os

sys.path.insert(0, os.path.abspath("../../src/"))
sys.path.insert(0, os.path.abspath("../../"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "SoyutNet simulations"
copyright = "2024, Okan Demir"
author = "Okan Demir"
release = "latest"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
]
autosummary_generate = True
templates_path = ["_templates"]
exclude_patterns = []
autosectionlabel_prefix_document = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "classic"
html_static_path = ["_static"]
html_logo = "_static/soyutnet_logo.png"
html_theme_options = {
    "footerbgcolor": "#ffffff",
    "bgcolor": "#efefef",
    "sidebarbgcolor": "#f6f6f6",
    "sidebartextcolor": "#000000",
    "sidebarlinkcolor": "#496e89",
    "headbgcolor": "#edf6ff66",
    "stickysidebar": True,
}

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "private-members": True,
}
