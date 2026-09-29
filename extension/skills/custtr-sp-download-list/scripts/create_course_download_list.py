#!/usr/bin/env python3
"""Create a Course Materials Links list of standard AMD training downloads."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://amdcloud.sharepoint.com/sites/arc/materials"
TEAMS_CLIENT_ID = "1fec8e78-bce4-4aaf-ab1b-5451cc387264"
TOKEN_FILE = Path.home() / ".config" / "microsoft-graph" / "token.json"
ITEM_SPECS = (
    ("Course materials file", "download", "{part}-{version}-all-rev1.7z", None),
    ("Lab files only", "download", "{part}-{version}-rev1-lab_files.7z", None),
    ("Participant book", "download", "{part}-{version}-wkbp-rev1.7z", None),
    ("Lab book", "download", "{part}-{version}-wkb-lab-rev1.7z", None),
    ("VILT workbooks", "download", "{part}-{version}-wkb-rev1_VILT.7z", None),
    ("Lab setup guide", "setup", None, None),
    (
        "Virtual machine",
        "vm",
        None,
        "The same virtual machine is used across all {version} courses so you will only need to download the VM once.",
    ),
)

_SSL_CONTEXT: ssl.SSLContext | None = None


def _ssl_context() -> ssl.SSLContext:
    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT
    cafile = (
        os.environ.get("SSL_CERT_FILE")
        or os.environ.get("REQUESTS_CA_BUNDLE")
        or os.environ.get("CURL_CA_BUNDLE")
    )
    if not cafile:
        for cand in (
            "/etc/pki/tls/certs/ca-bundle.crt",
            "/etc/ssl/certs/ca-certificates.crt",
        ):
            if os.path.isfile(cand):
                cafile = cand
                break
    _SSL_CONTEXT = (
        ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
    )
    return _SSL_CONTEXT


def list_title(course_title: str, version: str) -> str:
    title = course_title.strip()
    ver = version.strip()
    if title.endswith(ver):
        return title
    return f"{title} {ver}"


def item_url(kind: str, filename: str | None, part: str, version: str) -> str:
    if kind == "download":
        name = filename.format(part=part, version=version)
        return f"https://download.amd.com/opendownload/cust-training/{version}/{name}"
    if kind == "setup":
        guide = urllib.parse.quote(f"Common Lab Setup Guide {version}.pdf")
        return (
            "https://amdcloud.sharepoint.com/sites/arc/materials/"
            f"Lab%20Setup%20Guides/Common/{guide}"
        )
    if kind == "vm":
        return (
            "https://amdcloud.sharepoint.com/sites/arc/materials/"
            "Virtual%20Machines/Virtual%20Machines.aspx"
        )
    raise ValueError(kind)


def build_items(part: str, version: str) -> list[dict[str, str]]:
    out = []
    for alt, kind, filename, note in ITEM_SPECS:
        item = {"alt": alt, "url": item_url(kind, filename, part, version)}
        if note:
            item["notes"] = note.format(version=version)
        out.append(item)
    return out


def load_graph_token_file() -> dict:
    if not TOKEN_FILE.exists():
        print(
            "ERROR: No Graph token at ~/.config/microsoft-graph/token.json. "
            "Authenticate with the m365 SharePoint skill first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


def spo_access_token() -> str:
    saved = load_graph_token_file()
    refresh = saved.get("refresh_token") or ""
    tenant = saved.get("tenant_id") or ""
    client_id = saved.get("client_id") or TEAMS_CLIENT_ID
    if not refresh or not tenant:
        print("ERROR: Graph token is missing refresh_token or tenant_id.", file=sys.stderr)
        sys.exit(1)
    data = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "scope": "https://amdcloud.sharepoint.com/.default offline_access",
        }
    ).encode()
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: SharePoint token request failed: {e.read().decode()[:500]}", file=sys.stderr)
        sys.exit(1)
    token = body.get("access_token")
    if not token:
        print("ERROR: SharePoint token response had no access_token.", file=sys.stderr)
        sys.exit(1)
    return token


class SPO:
    def __init__(self, site: str, token: str) -> None:
        self.site = site.rstrip("/")
        self.token = token
        self.digest = ""

    def _headers(self, write: bool = False) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json;odata=nometadata",
        }
        if write:
            h["Content-Type"] = "application/json;odata=nometadata"
            if self.digest:
                h["X-RequestDigest"] = self.digest
        return h

    def request(self, method: str, url: str, body=None, extra=None):
        headers = self._headers(write=method != "GET")
        if extra:
            headers.update(extra)
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120, context=_ssl_context()) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {"status": resp.status}
        except urllib.error.HTTPError as e:
            text = e.read().decode()[:1500]
            raise RuntimeError(f"{method} {url} -> {e.code}: {text}") from e

    def refresh_digest(self) -> None:
        d = self.request("POST", f"{self.site}/_api/contextinfo", body={})
        self.digest = d.get("FormDigestValue") or ""
        if not self.digest:
            raise RuntimeError("Could not get SharePoint request digest")


def get_list_by_title(spo: SPO, title: str) -> dict | None:
    quoted = title.replace("'", "''")
    filter_q = urllib.parse.urlencode(
        {"$filter": f"Title eq '{quoted}'", "$select": "Id,Title,OnQuickLaunch,ItemCount,DefaultViewUrl"}
    )
    try:
        data = spo.request("GET", f"{spo.site}/_api/web/lists?{filter_q}")
    except RuntimeError:
        return None
    values = data.get("value") or []
    return values[0] if values else None


def create_links_list(spo: SPO, title: str) -> dict:
    return spo.request(
        "POST",
        f"{spo.site}/_api/web/lists",
        body={
            "AllowContentTypes": False,
            "BaseTemplate": 103,
            "ContentTypesEnabled": False,
            "Description": "",
            "Title": title,
            "OnQuickLaunch": False,
            "Hidden": False,
        },
    )


def ensure_not_on_quick_launch(spo: SPO, list_id: str, on_quick_launch: bool) -> None:
    if not on_quick_launch:
        return
    spo.request(
        "POST",
        f"{spo.site}/_api/web/lists(guid'{list_id}')",
        body={"OnQuickLaunch": False},
        extra={"X-HTTP-Method": "MERGE", "IF-MATCH": "*"},
    )


def list_items(spo: SPO, list_id: str) -> list[dict]:
    data = spo.request(
        "GET",
        f"{spo.site}/_api/web/lists(guid'{list_id}')/items?$select=Id,URL,Comments",
    )
    return data.get("value") or []


def add_item(spo: SPO, list_id: str, alt: str, url: str, notes: str | None) -> dict:
    body = {"URL": {"Description": alt, "Url": url}}
    if notes:
        body["Comments"] = notes
    return spo.request("POST", f"{spo.site}/_api/web/lists(guid'{list_id}')/items", body=body)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create an AMD course download Links list")
    p.add_argument("--title", required=True, help="Course title (version appended if missing)")
    p.add_argument("--part", required=True, help="Download part number, e.g. ver-dm")
    p.add_argument("--version", required=True, help="Course version, e.g. 2026.1")
    p.add_argument("--site", default=SITE, help="SharePoint site URL")
    p.add_argument("--dry-run", action="store_true", help="Print planned list/items only")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    part = args.part.strip()
    version = args.version.strip()
    title = list_title(args.title, version)
    items = build_items(part, version)
    planned = {"title": title, "part": part, "version": version, "items": items}
    if args.dry_run:
        print(json.dumps(planned, indent=2))
        return

    spo = SPO(args.site, spo_access_token())
    spo.refresh_digest()

    existing = get_list_by_title(spo, title)
    created = False
    if existing:
        list_id = existing["Id"]
    else:
        created_list = create_links_list(spo, title)
        list_id = created_list["Id"]
        created = True
        existing = get_list_by_title(spo, title) or created_list

    ensure_not_on_quick_launch(spo, list_id, bool(existing.get("OnQuickLaunch")))

    current = list_items(spo, list_id)
    have = set()
    for it in current:
        url_val = it.get("URL") or {}
        if isinstance(url_val, dict) and url_val.get("Description"):
            have.add(url_val["Description"])

    added = []
    for item in items:
        if item["alt"] in have:
            continue
        add_item(spo, list_id, item["alt"], item["url"], item.get("notes"))
        added.append(item["alt"])

    final = get_list_by_title(spo, title) or existing
    view = final.get("DefaultViewUrl") or ""
    web_url = f"https://amdcloud.sharepoint.com{view}" if view.startswith("/") else view
    print(
        json.dumps(
            {
                "created": created,
                "title": title,
                "id": list_id,
                "webUrl": web_url,
                "onQuickLaunch": bool(final.get("OnQuickLaunch")),
                "itemCount": final.get("ItemCount"),
                "added": added,
                "items": items,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
