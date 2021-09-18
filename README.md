# SourceMod Install / Upgrade Script

A Python 3.8+ script to install and upgrade SourceMod.  This script is able to:

- Automatically download the latest revision of a SourceMod branch of your choosing, for any
  supported platform (by default picking the one for the current host OS).
- Install from a manually-defined URL, or from an already downloaded archive or folder.
- Smartly upgrade plugins anywhere within the plugin directory and its subdirectories.
- Not touch or overwrite your configuration files.

## Instructions

1. Download the `sourcemod_installer.pyz` zipapp file from the Releases section.
(This is just the module packaged in a ZIP archive.  Just like Java and their JARs.)
2. Run the zipapp:

    python3 sourcemod_installer.pyz /path/to/gamedir

(The path is the directory that will contain the `addons/` subdirectory.)
You will need to agree to SourceMod's license on first install.

There's a number of other configuration options visible via `--help`.

## Building

Requires Python.

```
python -m zipapp sourcemod_installer -p "/usr/bin/env python3" -o build/sourcemod_installer.pyz -c
```

## License

There isn't anything particularly novel about this tool, so feel free to use and modify it under
the conditions of the [BSD Zero Clause License](https://spdx.org/licenses/0BSD.html).
