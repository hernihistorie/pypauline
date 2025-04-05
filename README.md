# pypauline

This repository contains tools to work with the open source floppy disk dumper [Pauline](https://github.com/jfdelnero/Pauline).

## Dependencies

Use `uv` to set up a virtual environment using `uv install`.  Then run scripts by prefixing `python` with `uv run`,
or enter the virtualenv by using `uv shell`.

## config.py

Should have the following contents:
```python
FLOPPY_DRIVE_NAMES = ["fd1", "fd11", "fd8", "fd10", "fd4", "fd12"]
OPERATOR_NAME = "yourname"
```
Provide the names for the floppy drives connected to your Pauline (these will be put in the directory name) and your own name.

## pauline.py

This script runs on your computer and connects to Pauline on a local network.  It assists with making sequential dumps of
multiple floppies.

Example usage:

```bash
$ python pauline.py 192.168.162.46 8253 + + + + +
```

The first argument is the IP address to Pauline and the following arguments are inventory numbers for the floppies you
wish to dump.  There are two special characters: `+` increments the previous asset ID.  `-` skips the floppy drives.

## pyhxcfe.py

This script uses the command line interface of HxCFloppyEmulator Software to perform a batch conversion of a directory
of floppy dumps made with Pauline.

## conv_atari8bit.py

This script batch converts a directory of floppy dumps for the Atari 8-bit micros to the ATR format.
It essentially implements the following tutorial as a script: https://retroherna.org/wiki/doku.php?id=organizace:navody:zalohovani:atari8bit
