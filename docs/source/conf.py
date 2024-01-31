# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
from importlib.metadata import version as get_version

os.environ["SPHINX_AUTODOC_RELOAD_MODULES"] = "1"

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


project = "Chiru"
copyright = "2023, Lura Skye"
author = "Lura Skye"
release = get_version("chiru")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.jquery",
    "sphinx_inline_tabs",
    "sphinx.ext.graphviz",
    "sphinx.ext.inheritance_diagram",
]

templates_path = ["_templates"]
exclude_patterns = []

autodoc_default_options = {
    "members": None,
    "member-order": "bysource",
    "show-inheritance": None,
}

autodoc_class_signature = "separated"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "anyio": ("https://anyio.readthedocs.io/en/stable/", None),
    "trio": ("https://trio.readthedocs.io/en/stable/", None),
    "arrow": ("https://arrow.readthedocs.io/en/latest/", None),
    "cattr": ("https://catt.rs/en/stable/", None),  # damn, that's a nice domain hack
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = ["css/custom.css"]

html_theme_options = {
    "collapse_navigation": False,
    "style_external_links": True,
}


def skip_init_on_models(app, what, name, obj, skip, options):
    # gross and hacky.

    if name != "__init__":
        return skip

    if obj.__module__.startswith("chiru.event.model"):
        return True

    if obj.__module__.startswith("chiru.models"):
        if obj.__module__ not in ("chiru.models.factory", "chiru.models.base"):
            return True

        return skip

    return skip


def setup(app):
    app.connect("autodoc-skip-member", skip_init_on_models)
