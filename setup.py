# Compatibility shim — allows `pip install -e .` with older setuptools.
# pyproject.toml drives all configuration; this file is intentionally minimal.
from setuptools import setup

setup()

