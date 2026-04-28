"""Integrations with other web frameworks.

The core fraud-detection pipeline (`fraud_detection.pipeline.analyze`)
is framework-agnostic. This subpackage provides thin wrappers so the
same pipeline can be served from frameworks other than the bundled
FastAPI app — most notably Flask, which is what runs on PythonAnywhere.
"""
