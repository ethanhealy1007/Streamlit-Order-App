"""Read configuration without printing credentials.

Credentials are looked up in this order:
1. Streamlit secrets (Streamlit Community Cloud, or a local .streamlit/secrets.toml)
2. Environment variables / a local .env file
"""
import os
from pathlib import Path

from dotenv import load_dotenv


def read_setting(name):
    """Return a setting from Streamlit secrets, falling back to .env / environment."""
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        # No secrets file (for example, running a plain Python script locally)
        pass
    load_dotenv(Path(__file__).with_name(".env"))
    return os.getenv(name, "").strip()


def get_settings():
    """Return the Supabase URL and secret key, or raise ValueError with a setup hint."""
    url = read_setting("SUPABASE_URL").rstrip("/")
    key = read_setting("SUPABASE_SECRET_KEY")
    if not url.startswith("https://") or "YOUR_PROJECT" in url:
        raise ValueError("Set your project HTTPS URL (not the dashboard URL).")
    if not key.startswith("sb_secret_"):
        raise ValueError("Set SUPABASE_SECRET_KEY to your own project's sb_secret_ key.")
    return url, key


def get_app_password():
    """Return the classroom access password ("" if it has not been configured)."""
    return read_setting("APP_PASSWORD")
