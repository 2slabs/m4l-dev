#!/usr/bin/env python3
"""Convert between Max patcher JSON (.maxpat) and Max for Live devices (.amxd); the format is twosl_dsp/amxd.py's.

  amxd.py pack   foo.maxpat foo.amxd --type audio|midi|instrument
  amxd.py freeze foo.maxpat foo-1.0.0.amxd --type instrument --embed a.js b.js
  amxd.py unpack foo.amxd foo.maxpat
  amxd.py list   foo-1.0.0.amxd          # what a frozen device contains
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import amxd  # noqa: E402


def main(argument_list):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("pack")
    pack.add_argument("source")
    pack.add_argument("destination")
    pack.add_argument("--type", choices=sorted(amxd.DEVICE_TYPE_CODES), required=True)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("source")
    freeze.add_argument("destination")
    freeze.add_argument("--type", choices=sorted(amxd.DEVICE_TYPE_CODES), required=True)
    freeze.add_argument("--embed", nargs="*", default=[])
    unpack = commands.add_parser("unpack")
    unpack.add_argument("source")
    unpack.add_argument("destination")
    listing = commands.add_parser("list")
    listing.add_argument("source")
    arguments = parser.parse_args(argument_list)

    if arguments.command in ("pack", "freeze"):
        with open(arguments.source, encoding="utf-8") as patch_file:
            patch = json.load(patch_file)
        if arguments.command == "pack":
            device_bytes = amxd.unfrozen_device_bytes(patch, arguments.type)
        else:
            embedded = []
            for path in arguments.embed:
                with open(path, "rb") as embedded_file:
                    embedded.append((os.path.basename(path), embedded_file.read()))
            device_bytes = amxd.frozen_device_bytes(patch, arguments.type, os.path.basename(arguments.destination),
                                                    embedded)
        with open(arguments.destination, "wb") as device_file:
            device_file.write(device_bytes)
        return 0
    with open(arguments.source, "rb") as device_file:
        device = amxd.read_device(device_file.read(), arguments.source)
    if arguments.command == "list":
        if device["frozen_files"] is None:
            print(f"{arguments.source}: not frozen ({device['device_type']})")
        for entry in device["frozen_files"] or []:
            print(f"{entry['type']}  {entry['sz32']:>8}  flag {entry['flag']:>2}  {entry['fnam']}")
        return 0
    if device["patch"] is None:
        sys.exit(f"{arguments.source} is frozen; unfreeze it in Max, save, then unpack")
    with open(arguments.destination, "w", encoding="utf-8") as patch_file:
        json.dump(device["patch"], patch_file, indent="\t")
    print(device["device_type"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
