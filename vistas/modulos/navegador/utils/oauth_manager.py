"""
GoogleOAuthManager - Módulo de autenticación OAuth 2.0 PKCE para Multitool
=====================================================================
Re-exporta el gestor oficial OAuth 2.0 PKCE desde oauth_pkce.py.
"""

from .oauth_pkce import GoogleOAuthManager, GoogleClientConfigDialog, generate_pkce

__all__ = ["GoogleOAuthManager", "GoogleClientConfigDialog", "generate_pkce"]
