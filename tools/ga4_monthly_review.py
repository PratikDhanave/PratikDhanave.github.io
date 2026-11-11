#!/usr/bin/env python3
"""Monthly GA4 conversion review for pratikdhanave.com.

Pulls the last ~30 days of conversion events (book_discovery_call,
services_click, playbook_click, readiness_check_click, newsletter_submit,
topmate_booking, contact_click) broken down by the page they fired on,
compares against the previous report, and writes a markdown report to
~/Reports/pratikdhanave-ga4/YYYY-MM.md. Run by a monthly launchd job
(com.pratikdhanave.ga4review); safe to run by hand any time.

Auth (preferred): a Google Cloud SERVICE ACCOUNT key at
~/.config/pratikdhanave/ga4-sa.json (override with env GA4_SA_KEY), whose
email has been granted Viewer access on the GA4 property (GA4 Admin ->
Property access management). The token is minted locally (stdlib + openssl),
no gcloud involved. This avoids Google's "app is blocked" refusal, which
hits `gcloud auth application-default login` when it requests the sensitive
Analytics scope through Google's shared OAuth client.

Fallback: user ADC via gcloud, if it ever exists with the right scope.

If credentials are missing the script still writes a report explaining
exactly what to do, and posts a macOS notification either way.
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import date

EVENTS = [
    "book_discovery_call", "services_click", "playbook_click",
    "readiness_check_click", "newsletter_submit", "topmate_booking",
    "contact_click", "consulting_click",
]
REPORT_DIR = os.path.expanduser("~/Reports/pratikdhanave-ga4")
PROPERTY_CACHE = os.path.join(REPORT_DIR, "property_id.txt")
SITE_HINT = "pratikdhanave"


def notify(title, body):
    try:
        subprocess.run(["osascript", "-e",
                        f'display notification "{body}" with title "{title}"'],
                       capture_output=True, timeout=10)
    except Exception:
        pass


def write_report(name, text):
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, name)
    with open(path, "w") as f:
        f.write(text)
    return path


SA_KEY_PATH = os.environ.get(
    "GA4_SA_KEY", os.path.expanduser("~/.config/pratikdhanave/ga4-sa.json"))
SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def sa_token():
    """Mint an access token from a service-account key: RS256 JWT via openssl."""
    if not os.path.exists(SA_KEY_PATH):
        return None, f"no service-account key at {SA_KEY_PATH}"
    try:
        key = json.load(open(SA_KEY_PATH))
        now = int(time.time())
        header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claims = _b64url(json.dumps({
            "iss": key["client_email"], "scope": SCOPE,
            "aud": key["token_uri"], "iat": now, "exp": now + 3600,
        }).encode())
        signing_input = header + b"." + claims
        with tempfile.NamedTemporaryFile("w", suffix=".pem") as pem:
            pem.write(key["private_key"]); pem.flush()
            p = subprocess.run(["openssl", "dgst", "-sha256", "-sign", pem.name],
                               input=signing_input, capture_output=True)
        if p.returncode != 0:
            return None, "openssl signing failed: " + p.stderr.decode()[:200]
        jwt = (signing_input + b"." + _b64url(p.stdout)).decode()
        body = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt}).encode()
        req = urllib.request.Request(key["token_uri"], data=body, headers={
            "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["access_token"], None
    except Exception as e:  # noqa: BLE001 — report any auth failure in the output
        detail = e.read().decode()[:300] if hasattr(e, "read") else str(e)
        return None, f"service-account auth failed: {detail}"


def adc_token():
    token, sa_err = sa_token()
    if token:
        return token, None
    p = subprocess.run(["gcloud", "auth", "application-default",
                        "print-access-token"], capture_output=True, text=True)
    if p.returncode != 0:
        return None, f"{sa_err}; gcloud ADC also unavailable: {p.stderr.strip()[:200]}"
    return p.stdout.strip(), None


def api(url, token, payload=None):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }, data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def find_property(token):
    if os.path.exists(PROPERTY_CACHE):
        return open(PROPERTY_CACHE).read().strip()
    data = api("https://analyticsadmin.googleapis.com/v1beta/accountSummaries?pageSize=200", token)
    candidates = []
    for acct in data.get("accountSummaries", []):
        for prop in acct.get("propertySummaries", []):
            candidates.append((prop.get("displayName", ""), prop["property"]))
    for name, prop in candidates:
        if SITE_HINT in name.lower():
            pid = prop.split("/")[-1]
            os.makedirs(REPORT_DIR, exist_ok=True)
            open(PROPERTY_CACHE, "w").write(pid)
            return pid
    if len(candidates) == 1:
        pid = candidates[0][1].split("/")[-1]
        os.makedirs(REPORT_DIR, exist_ok=True)
        open(PROPERTY_CACHE, "w").write(pid)
        return pid
    raise RuntimeError(f"Could not auto-pick a GA4 property; candidates: {candidates}. "
                       f"Write the numeric id into {PROPERTY_CACHE}")


def run_report(token, pid):
    payload = {
        "dateRanges": [{"startDate": "30daysAgo", "endDate": "yesterday"}],
        "dimensions": [{"name": "pagePath"}, {"name": "eventName"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {"filter": {
            "fieldName": "eventName",
            "inListFilter": {"values": EVENTS},
        }},
        "limit": 10000,
    }
    return api(f"https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport",
               token, payload)


def load_previous_totals():
    """Totals from the most recent previous report, parsed from its own summary table."""
    if not os.path.isdir(REPORT_DIR):
        return None, None
    reports = sorted(f for f in os.listdir(REPORT_DIR) if re.fullmatch(r"\d{4}-\d{2}\.md", f))
    if not reports:
        return None, None
    prev = reports[-1]
    totals = {}
    for line in open(os.path.join(REPORT_DIR, prev)):
        m = re.match(r"\| (\w+) \| (\d+) \|$", line.strip())
        if m and m.group(1) in EVENTS:
            totals[m.group(1)] = int(m.group(2))
    return prev[:-3], totals or None


def main():
    today = date.today()
    report_name = f"{today:%Y-%m}.md"

    token, err = adc_token()
    if not token:
        text = (f"# GA4 conversion review — {today:%Y-%m} — SETUP NEEDED\n\n"
                "No usable Google credentials. One-time setup (service account — the\n"
                "user-login path gets blocked by Google for the Analytics scope):\n\n"
                "```\n"
                "gcloud auth login                               # plain login, not blocked\n"
                "gcloud projects create pratikdhanave-ga4 2>/dev/null || true\n"
                "gcloud config set project pratikdhanave-ga4\n"
                "gcloud services enable analyticsdata.googleapis.com analyticsadmin.googleapis.com\n"
                "gcloud iam service-accounts create ga4-reader --display-name='GA4 monthly review'\n"
                "mkdir -p ~/.config/pratikdhanave\n"
                "gcloud iam service-accounts keys create ~/.config/pratikdhanave/ga4-sa.json \\\n"
                "  --iam-account=ga4-reader@pratikdhanave-ga4.iam.gserviceaccount.com\n"
                "chmod 600 ~/.config/pratikdhanave/ga4-sa.json\n"
                "```\n\n"
                "Then in GA4 (analytics.google.com): Admin -> Property access management ->\n"
                "add `ga4-reader@pratikdhanave-ga4.iam.gserviceaccount.com` as **Viewer**.\n\n"
                "Then re-run: python3 tools/ga4_monthly_review.py\n\n"
                f"Details: {err}\n")
        path = write_report(report_name, text)
        notify("GA4 review: setup needed", "No Google credentials — see report for the one-time login command")
        print(path)
        return 0

    try:
        pid = find_property(token)
        data = run_report(token, pid)
    except (urllib.error.HTTPError, RuntimeError) as e:
        detail = e.read().decode()[:2000] if hasattr(e, "read") else str(e)
        text = (f"# GA4 conversion review — {today:%Y-%m} — API ERROR\n\n"
                f"```\n{detail}\n```\n\n"
                "Common causes: Analytics Data/Admin API not enabled on the quota project, "
                "or the logged-in Google account lacks access to the GA4 property.\n")
        path = write_report(report_name, text)
        notify("GA4 review: API error", "See report for details")
        print(path)
        return 1

    rows = data.get("rows", [])
    by_event, by_page, pairs = {}, {}, []
    for r in rows:
        page, event = r["dimensionValues"][0]["value"], r["dimensionValues"][1]["value"]
        n = int(r["metricValues"][0]["value"])
        by_event[event] = by_event.get(event, 0) + n
        by_page[page] = by_page.get(page, 0) + n
        pairs.append((page, event, n))

    prev_month, prev_totals = load_previous_totals()

    lines = [f"# GA4 conversion review — {today:%Y-%m}",
             "", f"Window: last 30 days (property {pid}). "
             f"Events: {', '.join(EVENTS)}.", "",
             "## Totals by event", "", "| event | count |", "|---|---|"]
    for e in EVENTS:
        lines.append(f"| {e} | {by_event.get(e, 0)} |")
    if prev_totals:
        lines += ["", f"### vs previous report ({prev_month})", "",
                  "| event | now | then | delta |", "|---|---|---|---|"]
        for e in EVENTS:
            now, then = by_event.get(e, 0), prev_totals.get(e, 0)
            sign = "+" if now >= then else ""
            lines.append(f"| {e} | {now} | {then} | {sign}{now - then} |")
    lines += ["", "## Top converting pages (all events)", "",
              "| page | conversions |", "|---|---|"]
    for page, n in sorted(by_page.items(), key=lambda kv: -kv[1])[:25]:
        lines.append(f"| {page} | {n} |")
    lines += ["", "## Page x event detail", "", "| page | event | count |", "|---|---|---|"]
    for page, event, n in sorted(pairs, key=lambda t: -t[2])[:60]:
        lines.append(f"| {page} | {event} | {n} |")
    lines += ["", "## How to read this", "",
              "- Pages here are where the click fired — i.e. the content that was doing the selling.",
              "- Blog posts appearing high = the contextual CTA earning its keep; consider writing more in that cluster.",
              "- High traffic clusters absent from this list = CTA or content mismatch worth a look.",
              "- Paste this report into Claude Code and ask for content recommendations.", ""]

    path = write_report(report_name, "\n".join(lines))
    total = sum(by_event.values())
    notify("GA4 monthly review ready", f"{total} conversions in 30d — report in ~/Reports/pratikdhanave-ga4/")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
