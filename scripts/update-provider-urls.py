#!/usr/bin/env python3
"""
Update PROVIDER_BASE_URLS in frugality.py from free-coding-models sources.
"""

import json
import re
import sys
from pathlib import Path


def update_provider_urls(urls_file, frugality_file):
    """Update PROVIDER_BASE_URLS in frugality.py with new URLs."""

    # Read the new URLs
    with open(urls_file, 'r') as f:
        new_urls = json.load(f)

    # Read frugality.py
    with open(frugality_file, 'r') as f:
        content = f.read()

    # Find PROVIDER_BASE_URLS section
    # Look for the start: PROVIDER_BASE_URLS = {
    # and capture everything until the closing }
    pattern = r'(PROVIDER_BASE_URLS\s*=\s*\{)([^}]*(?:\n[^}]*)*?)(\n\}$)'
    match = re.search(pattern, content, re.MULTILINE)

    if not match:
        print("ERROR: Could not find PROVIDER_BASE_URLS in frugality.py")
        sys.exit(1)

    # Build the new dictionary content
    entries = []
    for provider, url in sorted(new_urls.items()):
        # Escape any curly braces in URLs (like in cloudflare)
        escaped_url = url.replace('{', '{{').replace('}', '}}')
        entries.append(f'    "{provider}": "{escaped_url}",')

    # Add any providers from the old dict that might not be in free-coding-models
    # (like ollama or other local providers)
    old_providers_pattern = r'"([^"]+)"\s*:\s*"([^"]+)"'
    old_matches = re.findall(old_providers_pattern, match.group(2))
    old_providers = dict(old_matches)

    extra_providers = set(old_providers.keys()) - set(new_urls.keys())
    for provider in sorted(extra_providers):
        if provider not in new_urls:
            escaped_url = old_providers[provider].replace('{', '{{').replace('}', '}}')
            entries.append(f'    "{provider}": "{escaped_url}",')

    # Build the new section
    new_section = match.group(1) + '\n' + '\n'.join(entries) + match.group(3)

    # Replace the old section with the new one
    new_content = content[:match.start()] + new_section + content[match.end():]

    # Create backup
    backup_file = frugality_file + '.backup'
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"Backed up original to {backup_file}")

    # Write the updated content
    with open(frugality_file, 'w') as f:
        f.write(new_content)

    print(f"Updated {frugality_file} with {len(new_urls)} providers")
    print("New providers added:", sorted(set(new_urls.keys()) - set(old_providers.keys())))
    print("Old providers removed:", sorted(set(old_providers.keys()) - set(new_urls.keys())))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <provider-urls.json>")
        sys.exit(1)

    urls_file = sys.argv[1]
    frugality_file = Path(__file__).parent.parent / "frugality.py"

    if not Path(urls_file).exists():
        print(f"ERROR: {urls_file} not found")
        sys.exit(1)

    update_provider_urls(urls_file, frugality_file)