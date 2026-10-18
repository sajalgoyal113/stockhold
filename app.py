"""
StockHold Web Application - Root Entry Point
Ensures seamless deployment whether Streamlit Community Cloud targets 'app.py' or 'stockhold/app.py'.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_STOCKHOLD = os.path.join(_ROOT, "stockhold")
_PREDICT = os.path.join(_ROOT, "predict", "scripts")

for _p in [_STOCKHOLD, _ROOT, _PREDICT]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

_app_path = os.path.join(_STOCKHOLD, "app.py")
with open(_app_path, "r", encoding="utf-8") as _f:
    _code = _f.read()

exec(compile(_code, _app_path, "exec"))
