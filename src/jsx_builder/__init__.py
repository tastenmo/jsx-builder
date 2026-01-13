from pathlib import Path
from typing import Any, Dict

from sphinx.application import Sphinx

from jsx_builder.builders import JSONJSXBuilder, JSXBuilder

__version_info__ = (0, 0, 0)
__version__ = "0.0.0"


def setup(app: Sphinx) -> Dict[str, Any]:
    """Set up the JSX builder extension."""
    app.add_builder(JSXBuilder)
    app.add_builder(JSONJSXBuilder)
    return {"version": __version__, "parallel_read_safe": True}


