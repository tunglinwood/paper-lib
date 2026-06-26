"""LDAP/AD authentication helper.

This mirrors the Java reference implementation that binds to an LDAPS server
using simple authentication and a disabled SSL certificate check.
"""

import os
import ssl
import traceback
from typing import Optional

from ldap3 import AUTO_BIND_NO_TLS, SIMPLE, Server, Connection, Tls
from ldap3.core.exceptions import LDAPExceptionError

LDAP_URL = os.getenv("LDAP_URL", "ldaps://HUACNSDC003.HUA.COM:636")
LDAP_DOMAIN = os.getenv("LDAP_DOMAIN", "huamedicine.com")
_LDAP_VERIFY_SSL = os.getenv("LDAP_VERIFY_SSL", "false").lower() in ("true", "1", "yes")


def check_username_and_password(username: str, password: str, upn: Optional[str] = None) -> bool:
    """
    Authenticate `username` and `password` against the configured LDAP/AD server.

    If `upn` is provided (e.g. the user's stored email / userPrincipalName),
    it is used for the LDAP bind instead of `username@LDAP_DOMAIN`. This lets
    local accounts with email addresses map to their real LDAP accounts.

    Returns True if the bind succeeds, False otherwise. Exceptions are swallowed
    and treated as authentication failures so login failures do not leak details.
    """
    if not username or not password:
        return False

    user_principal = upn if upn and "@" in upn else f"{username}@{LDAP_DOMAIN}"

    # Mirror the Java implementation's behaviour of trusting all certificates.
    # This is insecure and should only be used inside a trusted network.
    tls = Tls(validate=ssl.CERT_NONE) if not _LDAP_VERIFY_SSL else None

    try:
        server = Server(LDAP_URL, use_ssl=True, tls=tls)
        conn = Connection(
            server,
            user=user_principal,
            password=password,
            authentication=SIMPLE,
            auto_bind=AUTO_BIND_NO_TLS,
            read_only=True,
        )
        bound = conn.bound
        conn.unbind()
        return bound
    except LDAPExceptionError as e:
        print(f"[ldap_auth] LDAP bind failed for {user_principal}: {e}", flush=True)
        return False
    except Exception as e:
        # Catch-all for network / SSL / configuration errors.
        print(f"[ldap_auth] Unexpected error for {user_principal}: {e}", flush=True)
        traceback.print_exc()
        return False


def ldap_user_email(username: str) -> str:
    """Return the default email address for an LDAP user."""
    return f"{username}@{LDAP_DOMAIN}"
