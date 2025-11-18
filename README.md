# hhfloppy

This repository contains tools for working with floppies developed at the [Czechoslovak Game Archive](https://herniarchiv.cz/).

Dumping at our archive is performed with the open source floppy disk dumper [Pauline](https://github.com/jfdelnero/Pauline).

## Dependencies

We use uv to manage Python versions and dependencies.  Please make sure you have [uv installed](https://docs.astral.sh/uv/getting-started/installation/).

Use `uv` to set up a virtual environment using `uv sync`.  Then run scripts by prefixing `python` with `uv run`,
or enter the virtualenv by using `./venv/bin/activate`.


## src/hhfloppy/pauline.py

This script runs on your computer and connects to Pauline on a local network.  It assists with making sequential dumps of
multiple floppies.

Example usage:

```bash
$ python src/hhfloppy/pauline.py 192.168.162.46 8253 + + + + +
```

The first argument is the IP address to Pauline and the following arguments are inventory numbers for the floppies you
wish to dump.  There are two special characters: `+` increments the previous asset ID.  `-` skips the floppy drives.

## src/hhfloppy/pyhxcfe.py

This script uses the command line interface of HxCFloppyEmulator Software to perform a batch conversion of a directory
of floppy dumps made with Pauline.

## src/hhfloppy/conv_atari8bit.py

This script batch converts a directory of floppy dumps for the Atari 8-bit micros to the ATR format.
It essentially implements the following tutorial as a script: https://retroherna.org/wiki/doku.php?id=organizace:navody:zalohovani:atari8bit
