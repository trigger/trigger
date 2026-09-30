"""Regression tests for TLS dependency availability (issue #398).

pyOpenSSL used to arrive transitively (old service-identity hard-required
it; Twisted only ships it with the ``[tls]`` extra). When that changed,
fresh installs got a trigger whose Twisted TLS paths failed with
``ModuleNotFoundError: No module named 'OpenSSL'``. These tests keep the
TLS stack import-honest.
"""

import pytest


def test_pyopenssl_installed():
    """Test that pyOpenSSL is importable."""
    OpenSSL = pytest.importorskip("OpenSSL")
    assert OpenSSL.__version__


def test_twisted_tls_stack():
    """Test that Twisted's TLS context factory is importable.

    DefaultOpenSSLContextFactory is the code path used by
    trigger.contrib.xmlrpc.server.
    """
    ssl = pytest.importorskip("twisted.internet.ssl")
    assert hasattr(ssl, "DefaultOpenSSLContextFactory")


def test_service_identity_pyopenssl_hooks():
    """Test that service_identity's pyOpenSSL verification hooks load."""
    pytest.importorskip("service_identity.pyopenssl")
