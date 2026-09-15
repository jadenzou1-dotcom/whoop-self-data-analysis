"""
Whoop API client with OAuth2 authorization-code login.

Setup:
    pip install requests python-dotenv

First run (does the browser login, saves tokens to token.json):
    python whoop_client.py

Later, import and use:
    from whoop_client import WhoopClient
    client = WhoopClient()
    print(client.get_profile())
    print(client.get_recovery())
"""

import http.server
import json
import os
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
API_BASE = "https://api.prod.whoop.com/developer/v2"

SCOPES = [
    "read:recovery",
    "read:cycles",
    "read:sleep",
    "read:workout",
    "read:profile",
    "read:body_measurement",
    "offline",
]

TOKEN_FILE = PROJECT_ROOT / "token.json"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        self.server.auth_code = params.get("code", [None])[0]
        self.server.state = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>Whoop login complete, you can close this tab.</body></html>")

    def log_message(self, *args):
        pass


def _run_oauth_flow(client_id: str, redirect_uri: str) -> dict:
    port = urllib.parse.urlparse(redirect_uri).port or 8000
    server = http.server.HTTPServer(("localhost", port), _CallbackHandler)
    server.auth_code = None
    server.state = None

    thread = threading.Thread(target=server.handle_request)
    thread.start()

    state = "whoop-local-auth"
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "state": state,
        }
    )
    print("Opening browser for Whoop login...")
    webbrowser.open(f"{AUTH_URL}?{query}")

    thread.join(timeout=180)
    if not server.auth_code:
        raise RuntimeError("Did not receive an authorization code from Whoop.")
    if server.state != state:
        raise RuntimeError("OAuth state mismatch, aborting.")

    return {"code": server.auth_code, "redirect_uri": redirect_uri}


class WhoopClient:
    def __init__(self):
        self.client_id = os.environ["WHOOP_CLIENT_ID"]
        self.client_secret = os.environ["WHOOP_CLIENT_SECRET"]
        self.redirect_uri = os.environ["WHOOP_REDIRECT_URI"]
        self._tokens = self._load_or_authorize()

    def _load_or_authorize(self) -> dict:
        if TOKEN_FILE.exists():
            return json.loads(TOKEN_FILE.read_text())

        result = _run_oauth_flow(self.client_id, self.redirect_uri)
        tokens = self._exchange_code_for_token(result["code"], result["redirect_uri"])
        self._save_tokens(tokens)
        return tokens

    def _exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def _refresh_token(self) -> dict:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._tokens["refresh_token"],
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "offline",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        self._save_tokens(tokens)
        return tokens

    def _save_tokens(self, tokens: dict):
        self._tokens = tokens
        TOKEN_FILE.write_text(json.dumps(tokens, indent=2))

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{API_BASE}{path}"
        headers = {"Authorization": f"Bearer {self._tokens['access_token']}"}
        resp = requests.request(method, url, headers=headers, **kwargs)

        if resp.status_code == 401:
            self._refresh_token()
            headers = {"Authorization": f"Bearer {self._tokens['access_token']}"}
            resp = requests.request(method, url, headers=headers, **kwargs)

        resp.raise_for_status()
        return resp.json()

    def get_profile(self) -> dict:
        return self._request("GET", "/user/profile/basic")

    def get_body_measurements(self) -> dict:
        return self._request("GET", "/user/measurement/body")

    def _get_all_pages(self, path: str, **params) -> dict:
        """Loop through nextToken pages until the API stops returning one.
        The `limit` param (max 25 per WHOOP's API) controls page size, not
        the total returned - this collects every page into one record list."""
        params.setdefault("limit", 25)
        records = []
        next_token = None
        while True:
            page_params = dict(params)
            if next_token:
                page_params["nextToken"] = next_token
            page = self._request("GET", path, params=page_params)
            records.extend(page.get("records", []))
            next_token = page.get("next_token")
            if not next_token:
                break
        return {"records": records}

    def get_cycles(self, all_pages: bool = True, **params) -> dict:
        if all_pages:
            return self._get_all_pages("/cycle", **params)
        return self._request("GET", "/cycle", params=params)

    def get_recovery(self, all_pages: bool = True, **params) -> dict:
        if all_pages:
            return self._get_all_pages("/recovery", **params)
        return self._request("GET", "/recovery", params=params)

    def get_sleep(self, all_pages: bool = True, **params) -> dict:
        if all_pages:
            return self._get_all_pages("/activity/sleep", **params)
        return self._request("GET", "/activity/sleep", params=params)

    def get_workouts(self, all_pages: bool = True, **params) -> dict:
        if all_pages:
            return self._get_all_pages("/activity/workout", **params)
        return self._request("GET", "/activity/workout", params=params)


if __name__ == "__main__":
    client = WhoopClient()
    print(json.dumps(client.get_profile(), indent=2))
