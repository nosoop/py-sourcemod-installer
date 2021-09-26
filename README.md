# SourceMod Install / Upgrade Script

A Python 3.8+ script to install and upgrade SourceMod.  This script is able to:

- Automatically download the latest revision of a SourceMod branch of your choosing, for any
  supported platform (by default picking the one for the current host OS).
- Install from a manually-defined URL, or from an already downloaded archive or folder.
- Smartly upgrade plugins anywhere within the plugin directory and its subdirectories.
- Not touch or overwrite your configuration files.

## Instructions

Install the script either by downloading a zipapp (the module packaged as a ZIP file, similar
to a Java JAR) from the Releases section, or by installing the package via `pip`.

    # via pip
    python -m pip install --user git+https://github.com/nosoop/py-sourcemod-installer.git
    sourcemod_installer /path/to/gamedir
    
    # via zipapp
    python3 /path/to/sourcemod_installer.pyz /path/to/gamedir

(The path is the directory that will contain the `addons/` subdirectory.)
You will need to agree to SourceMod's license on first install.

There's a number of other configuration options available via `--help`.

## License

There isn't anything particularly novel about this tool, so feel free to use and modify it under
the conditions of the [BSD Zero Clause License](https://spdx.org/licenses/0BSD.html).
