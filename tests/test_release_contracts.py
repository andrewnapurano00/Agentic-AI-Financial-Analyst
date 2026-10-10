"""Release inputs and offline boundary regressions."""
from pathlib import Path
import socket
import tomllib
import pytest
import requests
import httpx
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def test_direct_dependencies_match_and_newspaper_namespace_has_one_owner():
    root = Path(__file__).resolve().parents[1]
    def normalize(lines):
        return {canonicalize_name(r.name): str(r.specifier) for line in lines if line.strip() and not line.startswith('#') for r in [Requirement(line)]}
    requirements = normalize((root / 'requirements.txt').read_text().splitlines())
    project = normalize(tomllib.loads((root / 'pyproject.toml').read_text())['project']['dependencies'])
    assert requirements == project
    assert 'newspaper4k' in requirements and 'newspaper3k' not in requirements


def test_external_transports_are_rejected_before_network():
    for action in (lambda: requests.get('https://example.com'),
                   lambda: httpx.get('https://example.com'),
                   lambda: socket.create_connection(('203.0.113.1', 443))):
        with pytest.raises(AssertionError, match='Offline tests forbid'):
            action()
