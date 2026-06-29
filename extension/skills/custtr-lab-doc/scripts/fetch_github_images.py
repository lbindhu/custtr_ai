#!/usr/bin/env python3
"""
fetch_github_images.py
Download all images from a GitHub tutorial directory into the lab image database.

Usage:
    python fetch_github_images.py <github_url> [--clear]

Example:
    python fetch_github_images.py https://github.com/Xilinx/Vitis-Tutorials/tree/2025.2/AI_Engine_Development/AIE/Design_Tutorials/04-Polyphase-Channelizer
"""

import argparse
import json
import os
import re
import urllib.request
import urllib.error

IMAGE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'images')
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif'}

# Subdirectories commonly used in AMD/Xilinx tutorials for images
IMAGE_SUBDIRS = ['', 'images', 'figures', 'media', 'docs', 'assets', 'img', 'figures/images']

GITHUB_API = 'https://api.github.com/repos'
GITHUB_RAW = 'https://raw.githubusercontent.com'


def parse_github_url(url):
    """Parse GitHub tree URL -> (owner, repo, branch, path)."""
    m = re.match(r'https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)', url.rstrip('/'))
    if not m:
        raise ValueError(f'Cannot parse GitHub URL: {url}')
    return m.group(1), m.group(2), m.group(3), m.group(4)


def github_api_get(url):
    """GET a GitHub API URL and return parsed JSON. Returns None on 404."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'lab-doc-builder/1.0',
        'Accept': 'application/vnd.github.v3+json',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f'  [warn] GitHub API error {e.code}: {url}')
        return None
    except Exception as e:
        print(f'  [warn] Request failed: {e}')
        return None


def list_dir(owner, repo, branch, path):
    """Return list of file/dir items in a GitHub directory path."""
    url = f'{GITHUB_API}/{owner}/{repo}/contents/{path}?ref={branch}'
    data = github_api_get(url)
    if data is None or not isinstance(data, list):
        return []
    return data


def download_image(raw_url, dest_path):
    """Download an image from raw GitHub URL to dest_path. Returns True on success."""
    req = urllib.request.Request(raw_url, headers={'User-Agent': 'lab-doc-builder/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest_path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        print(f'  [warn] Failed to download {raw_url}: {e}')
        return False


def fetch_images_from_dir(owner, repo, branch, dir_path, downloaded):
    """Fetch all image files from one GitHub directory into IMAGE_DB."""
    items = list_dir(owner, repo, branch, dir_path)
    for item in items:
        if item['type'] != 'file':
            continue
        ext = os.path.splitext(item['name'])[1].lower()
        if ext not in IMAGE_EXTS:
            continue
        fname = item['name']
        dest = os.path.join(IMAGE_DB, fname)
        raw_url = f"{GITHUB_RAW}/{owner}/{repo}/{branch}/{dir_path}/{fname}"
        print(f'  Downloading: {fname}  ({raw_url})')
        if download_image(raw_url, dest):
            downloaded.append({'filename': fname, 'source_dir': dir_path})


def main():
    parser = argparse.ArgumentParser(description='Fetch tutorial images into lab image database')
    parser.add_argument('url', help='GitHub tree URL of the tutorial directory')
    parser.add_argument('--clear', action='store_true',
                        help='Remove all existing images from the database before downloading')
    args = parser.parse_args()

    os.makedirs(IMAGE_DB, exist_ok=True)

    if args.clear:
        removed = 0
        for f in os.listdir(IMAGE_DB):
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                os.remove(os.path.join(IMAGE_DB, f))
                removed += 1
        if removed:
            print(f'Cleared {removed} existing image(s) from database.')

    owner, repo, branch, base_path = parse_github_url(args.url)
    print(f'Repo  : {owner}/{repo}')
    print(f'Branch: {branch}')
    print(f'Path  : {base_path}')
    print(f'DB    : {os.path.abspath(IMAGE_DB)}')
    print()

    downloaded = []

    for subdir in IMAGE_SUBDIRS:
        dir_path = (f'{base_path}/{subdir}'.rstrip('/')) if subdir else base_path
        items = list_dir(owner, repo, branch, dir_path)
        if items:
            has_images = any(
                os.path.splitext(i['name'])[1].lower() in IMAGE_EXTS
                for i in items if i['type'] == 'file'
            )
            if has_images:
                print(f'Searching: {dir_path}')
                fetch_images_from_dir(owner, repo, branch, dir_path, downloaded)

    print()
    if downloaded:
        print(f'Downloaded {len(downloaded)} image(s):')
        for entry in downloaded:
            print(f'  {entry["filename"]}  (from {entry["source_dir"]})')
    else:
        print('No images found in this tutorial directory.')

    # Save manifest for lab_config.json generation
    manifest_path = os.path.join(IMAGE_DB, '_last_fetch.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump({
            'url': args.url,
            'owner': owner,
            'repo': repo,
            'branch': branch,
            'base_path': base_path,
            'images': downloaded
        }, f, indent=2)
    print(f'\nManifest saved: {manifest_path}')
    return downloaded


if __name__ == '__main__':
    main()
