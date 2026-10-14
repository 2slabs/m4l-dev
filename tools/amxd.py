#!/usr/bin/env python3
"""Convert between Max patcher JSON (.maxpat) and Max for Live devices (.amxd).

  amxd.py pack   src/foo.maxpat devices/foo.amxd --type audio|midi|instrument
  amxd.py unpack devices/foo.amxd src/foo.maxpat

Unfrozen .amxd = 32-byte header ('ampf', device type, 'meta', 'ptch' + length) + patcher JSON.
Frozen devices (with embedded dependencies) can't be unpacked here; unfreeze in Max first.
"""
import argparse, json, struct, sys

TYPES = {"audio": b"aaaa", "midi": b"mmmm", "instrument": b"iiii"}

def pack(src, dst, kind):
    patch = json.load(open(src))
    body = (json.dumps(patch, indent="\t") + "\n").encode() + b"\0"
    header = (b"ampf" + struct.pack("<I", 4) + TYPES[kind]
              + b"meta" + struct.pack("<I", 4) + b"\0\0\0\0"
              + b"ptch" + struct.pack("<I", len(body)))
    open(dst, "wb").write(header + body)

def unpack(src, dst):
    d = open(src, "rb").read()
    if d[:4] != b"ampf" or d[24:28] != b"ptch":
        sys.exit("not an .amxd file")
    body = d[32:32 + struct.unpack("<I", d[28:32])[0]]
    if body[:4] == b"mx@c":
        sys.exit("device is frozen; unfreeze it in Max, save, then unpack")
    patch = json.loads(body.rstrip(b"\0"))
    json.dump(patch, open(dst, "w"), indent="\t")
    print({v: k for k, v in TYPES.items()}.get(d[8:12], d[8:12].decode()))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack"); p.add_argument("src"); p.add_argument("dst")
    p.add_argument("--type", choices=TYPES, default="audio")
    u = sub.add_parser("unpack"); u.add_argument("src"); u.add_argument("dst")
    a = ap.parse_args()
    pack(a.src, a.dst, a.type) if a.cmd == "pack" else unpack(a.src, a.dst)
