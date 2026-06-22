"""
get_refresh_token.py  –  run this ONCE locally, then never again.
----------------------------------------------------------------
It opens your browser for a normal Google sign-in, captures the
refresh token, and prints the three values you need to paste into
GitHub Secrets.

Prerequisites:
  pip install google-auth-oauthlib

Steps:
  1. Download your OAuth client JSON from Google Cloud Console
     (see setup guide in README or SETUP.md)
  2. Save it as  client_secret.json  in the same folder as this script
  3. Run:  python get_refresh_token.py
  4. Copy the three printed values into GitHub → Settings → Secrets
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\n" + "="*60)
print("Copy these three values into your GitHub repo Secrets:\n")
print(f"GOOGLE_CLIENT_ID     = {creds.client_id}")
print(f"GOOGLE_CLIENT_SECRET = {creds.client_secret}")
print(f"GOOGLE_REFRESH_TOKEN = {creds.refresh_token}")
print("="*60 + "\n")
print("You can delete client_secret.json and this script afterwards.")
