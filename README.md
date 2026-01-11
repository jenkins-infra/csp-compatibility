# CSP Compatibility

## Usage

Access the current Jenkins Plugins CSP Compatibility report [here](https://daniel-beck.github.io/csp-compatibility/).

By default, this lists all plugins sorted by popularity.
You can filter this list in multiple ways:

* Filter by plugin ID
* Only show plugins with known unresolved issues.
* "Filter by JSON", providing the output of `…/pluginManager/api/json?tree=plugins[shortName]`.
  This makes it easy to check a specific Jenkins instance's readiness for CSP enforcement.

### Determining compatibility

#### Issue Column

This column lists known Jira or GH issues filed against the plugin, noting a (potential) incompatibility with CSP enforcement in some way.
Some issues note clear incompatibilities (e.g., inline JavaScript that gets rejected), others are the result of static checks of the source code, and others note inherent problems with some features.
The presence of an unresolved issue is a fairly reliable indicator that the plugin may have a problem, but as those need to be manually created, especially less popular plugins may not have had an issue filed, despite being incompatible.

If there have never been issues tracked in this repository for a plugin, the column shows `-`.
If there had been issues but they have been resolved and the fixes released, the column shows `0`.

If a plugin is compatible with CSP enforcement but there's an open issue listed, or a plugin is incompatible despite there not being an issue, please file a pull request updating `resources/issues.yaml` as appropriate.

#### Scanner Column

This column lists the findings from the output of [a simple utility](https://github.com/daniel-beck/csp-scanner/) that was used to quickly identify incompatibilities across the Jenkins plugin ecosystem.
There are several limitations with this tool:

* It is a snapshot in time and may be outdated.
  The output was most recently recorded in late 2025 for most plugins in the list.
* Some source code patterns are known to be false positives or false negatives.
* Some (few) plugins host their source code outside the `@jenkinsci` GitHub organization, or the source code may not be readily available.
  These are generally skipped.

Overall, the reliability of this column is moderate.
If a plugin works well but shows an issue in this column, please file a pull request marking the finding as _False Positive_ in `resources/csp-scanner.yaml`.

#### Notes

This column provides additional information for a given plugin, such as:

* the latest release containing fixes for findings;
* notes on remaining unresolved issues (e.g., affected features, whether it can be addressed by the plugin at all);
* noting that a plugin is deprecated, is looking for new maintainers, has unresolved security vulnerabilities, or appears unmaintained, all indicating a reduced chance for a plugin's incompatibilities to be fixed.

## Repository Overview

This repository combines a number of resource files to provide information about the compatibility of Jenkins plugins with Content Security Policy (CSP).
For details on those files, see the "Resource Files" section below.

Additionally, the scripts in this repository process update center metadata to identify unmaintained and deprecated plugins (which are unlikely to receive CSP compatibility fixes).

## Resource Files

### `resources/csp-scanner.yaml`

This file contains the output of the [csp-scanner](https://github.com/daniel-beck/csp-scanner) tool, which scans Jenkins plugins for CSP compatibility issues.
It includes an `assessment` field for each finding, which can be one of the following values:
* `True Positive`: The finding is a valid CSP compatibility issue.
* `False Positive`: The finding is not a valid CSP compatibility issue.
* `TODO`: The finding has not yet been assessed. Default value for new findings.

### `resources/issues.yaml`

A YAML file listing known issues with CSP compatibility for various Jenkins plugins.
Initially imported from a spreadsheet tracking the late 2024 CSP compatibility effort, it is now maintained semi-manually (manually adding issues as needed; automatically identifying fixes) to track ongoing issues and fixes.
It is not expected to be complete.
The file format is as follows:

* A top-level list of entries, each representing the status of a plugin. Each top-level list entry has a `id` field and a `findings` field.
  * `id`: A string representing the unique identifier of the plugin.
  * `findings`: A list of findings related to the plugin's CSP compatibility. If this list is empty, it indicates that there are no known issues for that plugin.
    * Each finding is represented as a dictionary with the following fields:
      * `url` denotes the GitHub URL of the code location where the issue was found. Optional, typically only if there is no `issue`.
      * `issue` is the GitHub or Jenkins Jira issue URL for a CSP incompatibility problem. This field is mandatory unless there is a `url`.
      * `fix` is the GitHub pull request or GitHub commit (on the default branch) that fixes the CSP incompatibility problem. Optional, only if a fix has been implemented.
      * `release` is the GitHub URL to a GitHub release or tag that first included the fix for the CSP incompatibility problem. Optional, only if the fix has been released.

### `resources/plugin-notes.yaml`

A set of key/value pairs where the key is a plugin ID and the value is a string containing additional about the plugin's CSP compatibility status.
This will be rendered alongside deprecation/unmaintained status in the Notes column.

## Development

The code in this repository was basically entirely vibecoded by an LLM.
It is as much of a utility for Jenkins administrators wishing to determine their readiness to enforce Content Security Policy on the instance as it is an experiment in AI-assisted software development.
The code is probably horrifyingly bad.
The author doesn't really care because it works well enough for the intended purpose, and the code is not intended to be maintained long-term.
