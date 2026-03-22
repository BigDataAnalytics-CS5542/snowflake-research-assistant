"""
Snowflake connection helper.
Reads config from .env (account, user, warehouse, database, schema).

Authentication (pick one):
  - Local dev:
      SNOWFLAKE_PASSWORD=your_password
      call get_conn(passcode="123456") for MFA
  - Railway / cloud (key-pair, no MFA):
      SNOWFLAKE_PRIVATE_KEY=<raw PEM content as single env var>

Usage:
    from scripts.sf_connect import get_conn
    conn = get_conn()

    python scripts/sf_connect.py
"""
import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


def _load_private_key():
    """
    Load RSA private key from SNOWFLAKE_PRIVATE_KEY env var (raw PEM string).
    Used for Railway deployment — no MFA, no network policy needed.
    Returns DER bytes or None if not set.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    raw_key = (os.getenv("SNOWFLAKE_PRIVATE_KEY") or "").strip() or None
    if not raw_key:
        return None

    # Railway stores env vars as one line — normalize literal \n to real newlines
    pem_bytes = raw_key.replace("\\n", "\n").encode()

    private_key = serialization.load_pem_private_key(
        pem_bytes,
        password=None,
        backend=default_backend(),
    )

    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_conn(passcode=""):
    required = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}. Fill .env from .env.example")

    private_key_bytes = _load_private_key()

    if not private_key_bytes and not os.getenv("SNOWFLAKE_PASSWORD"):
        raise RuntimeError(
            "Missing credentials: set SNOWFLAKE_PASSWORD (local) or "
            "SNOWFLAKE_PRIVATE_KEY (Railway). See .env.example."
        )

    conn_kwargs = dict(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        role=os.getenv("SNOWFLAKE_ROLE") or None,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

    if private_key_bytes:
        conn_kwargs["authenticator"] = "snowflake_jwt"
        conn_kwargs["private_key"] = private_key_bytes
        print("Using key-pair authentication (snowflake_jwt)...")
    else:
        conn_kwargs["password"] = os.getenv("SNOWFLAKE_PASSWORD")
        if passcode:
            conn_kwargs["authenticator"] = "username_password_mfa"
            conn_kwargs["passcode"] = passcode

    conn_kwargs = {k: v for k, v in conn_kwargs.items() if v}
    return snowflake.connector.connect(**conn_kwargs)


if __name__ == "__main__":
    try:
        if os.getenv("SNOWFLAKE_PRIVATE_KEY"):
            conn = get_conn()
        else:
            mfa = input("Enter MFA code (or press Enter if no MFA): ").strip()
            conn = get_conn(passcode=mfa)
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_USER(), CURRENT_WAREHOUSE(), CURRENT_DATABASE()")
        print("Connected:", cur.fetchone())
        conn.close()
    except Exception as e:
        print("Connection failed:", e)