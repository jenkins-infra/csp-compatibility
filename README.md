# CSP Compatibility

Access the current Jenkins Plugins CSP Compatibility report [here](https://daniel-beck.github.io/csp-compatibility/).

## Overview

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
