#!/usr/bin/env python3
"""
Generate a JSON file with plugin information from various input sources.
"""

import json
import re
import sys
import urllib.request
import yaml
from datetime import datetime, timedelta


UPDATE_CENTER_URL = "https://mirrors.updates.jenkins.io/current/update-center.actual.json"
FIVE_YEARS_AGO = datetime.now() - timedelta(days=5*365)


def download_update_center():
    """Download and parse the Jenkins update center JSON."""
    print("Downloading update center data...", file=sys.stderr)
    with urllib.request.urlopen(UPDATE_CENTER_URL) as response:
        data = json.loads(response.read().decode('utf-8'))
    print("Downloaded successfully.", file=sys.stderr)
    return data


def is_deprecated(plugin_id, plugin_data, deprecations):
    """Check if plugin is deprecated via labels or deprecations list."""
    # Check labels
    labels = plugin_data.get('labels', [])
    if 'deprecated' in labels:
        return True

    # Check deprecations list
    if plugin_id in deprecations:
        return True

    return False


def get_security_warnings(plugin_id, current_version, warnings):
    """Get list of active security warnings for the plugin."""
    active_warnings = []

    # warnings is a list of warning objects
    for warning in warnings:
        # Check if this warning is for our plugin
        if warning.get('name') != plugin_id:
            continue

        # Check each version pattern in the warning
        for version_info in warning.get('versions', []):
            pattern = version_info.get('pattern')
            if pattern:
                try:
                    # Use fullmatch to match the entire version string, not just a prefix
                    if re.fullmatch(pattern, current_version):
                        # Get the security ID
                        security_id = warning.get('id', 'UNKNOWN')
                        if security_id not in active_warnings:
                            active_warnings.append(security_id)
                except re.error:
                    # Invalid regex pattern, skip
                    pass

    return active_warnings


def get_unmaintained_status(plugin_data):
    """Check if plugin is unmaintained (5+ years since last release)."""
    release_timestamp = plugin_data.get('releaseTimestamp')
    if not release_timestamp:
        # No release timestamp - very old
        return "Unmaintained (no release date)"

    try:
        # Parse ISO 8601 date string (e.g., "2025-07-09T14:53:43.00Z")
        if isinstance(release_timestamp, str):
            # Handle ISO 8601 format with or without fractional seconds
            # Remove the 'Z' suffix and parse
            date_str = release_timestamp.rstrip('Z')
            if '.' in date_str:
                release_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
            else:
                release_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        else:
            # If it's a number, treat it as Unix timestamp in milliseconds
            release_date = datetime.fromtimestamp(release_timestamp / 1000.0)

        if release_date < FIVE_YEARS_AGO:
            # Format as yyyy-mm
            date_str = release_date.strftime('%Y-%m')
            return f"Unmaintained (last release {date_str})"
    except (ValueError, OSError):
        # Invalid timestamp
        return "Unmaintained (invalid release date)"

    return None


def compute_notes(plugin_id, plugin_data, deprecations, warnings, plugin_notes):
    """Compute notes list for a plugin and concatenate into a string."""
    notes_list = []

    # Check for custom notes first
    custom_note = plugin_notes.get(plugin_id, '')
    if custom_note:
        notes_list.append(custom_note)

    # Check if deprecated
    if is_deprecated(plugin_id, plugin_data, deprecations):
        notes_list.append("Deprecated")

    # Check for "adopt-this-plugin" label
    labels = plugin_data.get('labels', [])
    if 'adopt-this-plugin' in labels:
        notes_list.append("Looking for maintainers")

    # Check for security warnings
    current_version = plugin_data.get('version', '')
    security_warnings = get_security_warnings(plugin_id, current_version, warnings)
    for security_id in security_warnings:
        notes_list.append(f"Unresolved {security_id}")

    # Check if unmaintained
    unmaintained_status = get_unmaintained_status(plugin_data)
    if unmaintained_status:
        notes_list.append(unmaintained_status)

    return '\n'.join(notes_list) if notes_list else ''


def load_yaml_file(filename):
    """Load and parse a YAML file."""
    with open(filename, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json_file(filename):
    """Load and parse a JSON file."""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


def count_issues_without_release(plugin_id, issues_data):
    """Count findings in issues.yaml that don't have a 'release' key.
    Returns the count if plugin is found in the data, None otherwise."""
    for entry in issues_data:
        if entry.get('id') == plugin_id:
            count = 0
            findings = entry.get('findings', [])
            for finding in findings:
                if 'release' not in finding:
                    count += 1
            return count
    return None


def get_issue_details(plugin_id, issues_data):
    """Get detailed issue information for a plugin.
    Returns a list of issue details if plugin is found, None otherwise."""
    for entry in issues_data:
        if entry.get('id') == plugin_id:
            findings = entry.get('findings', [])
            issue_details = []
            for finding in findings:
                # Only include findings without a release
                if 'release' not in finding:
                    detail = {}
                    # Get issue URL (can be 'issue' or 'url' key)
                    if 'issue' in finding:
                        detail['issue'] = finding['issue']
                    elif 'url' in finding:
                        detail['issue'] = finding['url']

                    # Get fix URL (PR or commit)
                    if 'fix' in finding:
                        detail['fix'] = finding['fix']

                    # Only add if we have an issue URL
                    if 'issue' in detail:
                        issue_details.append(detail)

            return issue_details if issue_details else None
    return None


def build_repo_to_plugins_map(update_center_data):
    """Build a mapping from repository name to list of plugin IDs.
    Repository name is extracted from SCM URL (e.g., 'script-security-plugin' from
    'https://github.com/jenkinsci/script-security-plugin')."""
    repo_map = {}

    plugins = update_center_data.get('plugins', {})
    for plugin_id, plugin_info in plugins.items():
        scm_url = plugin_info.get('scm', '')
        if scm_url:
            # Extract repository name from SCM URL
            # Handle both https://github.com/jenkinsci/repo-name and
            # https://github.com/jenkinsci/repo-name.git
            parts = scm_url.rstrip('/').rstrip('.git').split('/')
            if len(parts) >= 2:
                repo_name = parts[-1]
                if repo_name not in repo_map:
                    repo_map[repo_name] = []
                repo_map[repo_name].append(plugin_id)

    return repo_map


def count_scanner_findings(plugin_id, scanner_data, repo_to_plugins_map, update_center_data):
    """Count findings in csp-scanner.yaml that don't have 'False Positive' assessment.
    csp-scanner.yaml uses repository names, not plugin IDs, so we need to map them.
    Returns the count if plugin is found in the data, None otherwise."""

    # Get the SCM URL for this plugin
    plugin_info = update_center_data.get('plugins', {}).get(plugin_id, {})
    scm_url = plugin_info.get('scm', '')

    if not scm_url:
        return None

    # Extract repository name from SCM URL
    parts = scm_url.rstrip('/').rstrip('.git').split('/')
    if len(parts) < 2:
        return None

    repo_name = parts[-1]

    # Look for this repository name in scanner data
    for entry in scanner_data:
        if entry.get('repo') == repo_name:
            count = 0
            findings = entry.get('findings') or []  # Handle None case
            for finding in findings:
                assessment = finding.get('assessment')
                if assessment != 'False Positive':
                    count += 1
            return count

    return None


def get_scanner_details(plugin_id, scanner_data, repo_to_plugins_map, update_center_data):
    """Get detailed scanner finding information for a plugin.
    Returns a list of scanner finding URLs with type if plugin is found, None otherwise."""

    # Get the SCM URL for this plugin
    plugin_info = update_center_data.get('plugins', {}).get(plugin_id, {})
    scm_url = plugin_info.get('scm', '')

    if not scm_url:
        return None

    # Extract repository name from SCM URL
    parts = scm_url.rstrip('/').rstrip('.git').split('/')
    if len(parts) < 2:
        return None

    repo_name = parts[-1]

    # Look for this repository name in scanner data
    for entry in scanner_data:
        if entry.get('repo') == repo_name:
            findings = entry.get('findings') or []  # Handle None case
            scanner_details = []
            for finding in findings:
                assessment = finding.get('assessment')
                # Only include findings that are not marked as False Positive
                if assessment != 'False Positive':
                    url = finding.get('url')
                    finding_type = finding.get('type', 'Unknown')
                    if url:
                        scanner_details.append({
                            'url': url,
                            'type': finding_type
                        })

            return scanner_details if scanner_details else None

    return None


def main():
    """Main function to generate the plugin report."""
    print("Loading input files...")

    # Load input files
    issues_data = load_yaml_file('resources/issues.yaml')
    scanner_data = load_yaml_file('resources/csp-scanner.yaml')
    plugin_notes_data = load_yaml_file('resources/plugin-notes.yaml')

    # Download update center data
    update_center_data = download_update_center()

    print(f"Loaded {len(issues_data)} entries from issues.yaml")
    print(f"Loaded {len(scanner_data)} entries from csp-scanner.yaml")

    # Extract plugins, deprecations, and warnings from update center
    plugins = update_center_data.get('plugins', {})
    deprecations = update_center_data.get('deprecations', {})
    warnings = update_center_data.get('warnings', {})
    print(f"Found {len(plugins)} plugins in update center")

    # Build repository to plugin ID mapping for scanner data
    repo_to_plugins_map = build_repo_to_plugins_map(update_center_data)
    print(f"Built mapping for {len(repo_to_plugins_map)} repositories")

    # Generate the output list
    output_list = []

    for plugin_id, plugin_info in plugins.items():
        # Extract required fields
        popularity = plugin_info.get('popularity', 0)
        release_timestamp = plugin_info.get('releaseTimestamp', '')
        scm_url = plugin_info.get('scm', '')
        display_name = plugin_info.get('title', '')

        # Count issues and scanner findings (None if not in source file)
        issues_count = count_issues_without_release(plugin_id, issues_data)
        scanner_count = count_scanner_findings(plugin_id, scanner_data, repo_to_plugins_map, update_center_data)
        issue_details = get_issue_details(plugin_id, issues_data)
        scanner_details = get_scanner_details(plugin_id, scanner_data, repo_to_plugins_map, update_center_data)

        # Compute notes
        notes_str = compute_notes(plugin_id, plugin_info, deprecations, warnings, plugin_notes_data)

        # Create entry - only include issues/scanner if they exist in source files
        entry = {
            'id': plugin_id,
            'displayName': display_name,
            'popularity': popularity,
            'date': release_timestamp,
            'notes': notes_str,
            'scm': scm_url
        }

        # Add issues/scanner only if present in source data
        if issues_count is not None:
            entry['issues'] = issues_count
        if scanner_count is not None:
            entry['scanner'] = scanner_count
        # Add issue details if present
        if issue_details is not None:
            entry['issueDetails'] = issue_details
        # Add scanner details if present
        if scanner_details is not None:
            entry['scannerDetails'] = scanner_details

        output_list.append(entry)

    # Sort by popularity (descending) for better readability
    output_list.sort(key=lambda x: x['popularity'], reverse=True)

    # Write to output file
    output_filename = 'output/plugin_report.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output_list, f, indent=2, ensure_ascii=False)

    print(f"\nGenerated {output_filename} with {len(output_list)} entries")

    # Print some statistics
    total_issues = sum(e.get('issues', 0) for e in output_list)
    total_scanner = sum(e.get('scanner', 0) for e in output_list)
    plugins_with_notes = sum(1 for e in output_list if e['notes'])
    plugins_with_issues = sum(1 for e in output_list if 'issues' in e)
    plugins_with_scanner = sum(1 for e in output_list if 'scanner' in e)

    print(f"\nStatistics:")
    print(f"  Total plugins: {len(output_list)}")
    print(f"  Plugins in issues file: {plugins_with_issues}")
    print(f"  Plugins in scanner file: {plugins_with_scanner}")
    print(f"  Total unresolved issues: {total_issues}")
    print(f"  Total scanner findings: {total_scanner}")
    print(f"  Plugins with notes: {plugins_with_notes}")


if __name__ == '__main__':
    main()
