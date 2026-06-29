"""
Image search helper for the custtr-lab-doc skill.

Usage:
    python find_images.py <keyword> [keyword2 ...]

Searches the image_index.json (15,052 images from T:\\Graphics_Repository)
and returns matching file paths (relative to T:\\Graphics_Repository),
sorted with the MOST RECENT version first.

Version detection: extracts year from filename patterns like:
  [2024.2], [2023.1], 2025.2, _25.2, _2024, etc.
Images without a version tag are treated as version 0 (shown last).

Examples:
    python find_images.py hardware manager
    python find_images.py ILA dashboard
    python find_images.py synthesis complete
    python find_images.py KCU105 board
    python find_images.py mark debug nets
"""

import json
import os
import re
import sys

INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          '..', 'images', 'image_index.json')


def extract_version(path):
    """
    Extract full version as a sortable float from path. Higher = newer.
    Priority order: 2025.2 > 2025.1 > 2024.2 > 2024.1 > 2023.2 > 2023.1 > ...
    Handles patterns: [2025.2], [2024.1], _25.2, _2023.1, 2024.2, etc.
    """
    best = 0.0

    # Full 4-digit year with minor: [2025.2] or 2024.1 or _2023.2
    for m in re.finditer(r'(20\d\d)[\.\-](\d)', path):
        ver = int(m.group(1)) + int(m.group(2)) * 0.1
        if ver > best:
            best = ver

    # Short form: [25.2] or _25.1
    for m in re.finditer(r'[\[\s_](\d\d)\.(\d)[\]\s_\.]', path):
        year = 2000 + int(m.group(1))
        ver = year + int(m.group(2)) * 0.1
        if ver > best:
            best = ver

    return best


def search(keywords, max_results=30):
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index = json.load(f)

    keywords_lower = [k.lower() for k in keywords]
    matches = []
    for path in index:
        name_lower = path.lower()
        if all(k in name_lower for k in keywords_lower):
            matches.append(path)

    # Sort: newest version first, then alphabetically
    matches.sort(key=lambda p: (-extract_version(p), p.lower()))

    return matches[:max_results]


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    keywords = sys.argv[1:]
    results = search(keywords)

    if not results:
        print(f'No images found matching: {" ".join(keywords)}')
    else:
        print(f'Found {len(results)} image(s) matching "{" ".join(keywords)}" '
              f'(newest version first):\n')
        for r in results:
            ver = extract_version(r)
            ver_tag = f'[{ver:.1f}]' if ver else '[no ver]'
            print(f'  {ver_tag:9s}  {r}')
        print(f'\nUse MOST RECENT version in lab_config.json:')
        print(f'  {{"image": "{results[0]}", "caption": "..."}}')
