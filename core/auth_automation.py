"""
core/auth_automation.py
=======================
Automates ICICI Direct Breeze API login using Playwright.
Launches a visible browser so the user can enter their password securely.
Extracts the session token from the redirect URL automatically.
"""

from __future__ import annotations

import urllib.parse
from utils.logger import get_logger

log = get_logger(__name__)

class AuthAutomationError(Exception):
    pass

def fetch_session_token(app_key: str) -> str:
    """
    Launch a visible browser to ICICI login page.
    Wait for the user to log in manually.
    Extract and return the apisession token from the callback URL.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        raise AuthAutomationError(
            "Playwright is not installed. Run: pip install playwright && playwright install chromium"
        )

    login_url = f"https://api.icicidirect.com/apiuser/login?api_key={app_key}"
    
    with sync_playwright() as p:
        try:
            # Launch visible browser for security/trust
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            log.info("Launching Playwright browser for ICICI login...")
            page.goto(login_url)
            
            # Wait for the user to login and be redirected
            # The redirect URL usually looks like http://127.0.0.1/?apisession=XYZ
            try:
                # We wait up to 3 minutes for the user to complete the login
                page.wait_for_url("**/apisession=*", timeout=180000)
            except PlaywrightTimeoutError:
                browser.close()
                raise AuthAutomationError("Login timed out after 3 minutes.")
                
            current_url = page.url
            browser.close()
            
            # Parse the session token from the URL
            parsed = urllib.parse.urlparse(current_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            if "apisession" in query_params:
                token = query_params["apisession"][0]
                log.info("Successfully extracted apisession token via Playwright.")
                return token
            else:
                raise AuthAutomationError("Could not find apisession in the redirect URL.")
                
        except Exception as e:
            raise AuthAutomationError(f"Automation failed: {e}")
