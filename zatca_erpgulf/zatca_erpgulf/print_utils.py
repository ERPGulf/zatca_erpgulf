import base64
import functools

import frappe
from markupsafe import Markup


@functools.lru_cache(maxsize=1)
def _font_b64():
    path = frappe.get_app_path("zatca_erpgulf", "public", "fonts", "saudi_riyal.ttf")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def saudi_riyal_font_face():
    # "src:" is followed by a newline + indent on purpose: Frappe's relative-URL
    # rewriter only matches ":url(" or ": url(", and would otherwise append
    # "!important" inside the src descriptor and break it.
    return Markup(
        '@font-face { font-family: "saudi_riyal"; src:\n'
        f'        url(data:font/ttf;base64,{_font_b64()}) format("truetype");'
        " unicode-range: U+20C1; }\n"
        '.riyal { font-family: "saudi_riyal", "DejaVu Sans", sans-serif !important;'
        " font-weight: normal; }"
    )