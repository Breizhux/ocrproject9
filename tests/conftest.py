"""Conftest POC : rend src/ importable pour tous les tests."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
