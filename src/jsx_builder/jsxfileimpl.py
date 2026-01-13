"""JSON serializer implementation wrapper."""

from __future__ import annotations

import json
from collections import UserString
from typing import IO, Any


class SphinxJSONEncoder(json.JSONEncoder):
    """JSONEncoder subclass that forces translation proxies."""
    def default(self, obj: Any) -> str:
        if isinstance(obj, UserString):
            return str(obj)
        return super().default(obj)

def dump(obj: Any, file: IO[str] | IO[bytes], *args: Any, **kwds: Any) -> None:
    kwds['cls'] = SphinxJSONEncoder
    json.dump(obj, file, *args, **kwds)

def createPage(obj: Any, *args: Any, **kwargs: Any) -> None:
    if kwargs["outDir"]:

        if isinstance(obj, dict) and "current_page_name" in obj and "body" in obj:
            with open(f"{kwargs['outDir']}/{obj['current_page_name']}.html", "w", encoding="utf-8") as f:
                f.write(obj["body"])

