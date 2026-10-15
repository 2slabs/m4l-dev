#!/usr/bin/env python3
"""Convert between Max patcher JSON (.maxpat) and Max for Live devices (.amxd).

  amxd.py pack   src/foo.maxpat devices/foo.amxd --type audio|midi|instrument
  amxd.py freeze src/foo.maxpat dist/foo.amxd --type instrument --embed devices/foo/a.js devices/foo/b.js
  amxd.py unpack devices/foo.amxd src/foo.maxpat
  amxd.py list   dist/foo.amxd          # what a frozen device contains

Unfrozen .amxd = 32-byte header ('ampf', device type, 'meta', 'ptch' + length) + patcher JSON.
Frozen .amxd   = the same header, then an 'mx@c' container holding the patch and every file it needs
(js, abstractions...) plus a 'dlst' directory of them, the layout Max's Freeze button writes
(worked out from frozen devices that ship with Live). A frozen device is one self-contained file.
"""
import argparse, json, os, struct, sys, time

TYPES = {"audio": b"aaaa", "midi": b"mmmm", "instrument": b"iiii"}

def pack(src, dst, kind):
    patch = json.load(open(src))
    body = (json.dumps(patch, indent="\t") + "\n").encode() + b"\0"
    header = (b"ampf" + struct.pack("<I", 4) + TYPES[kind]
              + b"meta" + struct.pack("<I", 4) + b"\0\0\0\0"
              + b"ptch" + struct.pack("<I", len(body)))
    open(dst, "wb").write(header + body)

MAC_EPOCH = 2082844800  # seconds from 1904-01-01 (Max's timestamps) to 1970-01-01


def _field(tag, data):
    return tag + struct.pack(">I", 8 + len(data)) + data


def _name(fn):
    raw = fn.encode("utf-8") + b"\0"
    return raw + b"\0" * (-len(raw) % 4)


def freeze(src, dst, kind, embed):
    """Write a frozen device: the patch plus `embed` files inside one .amxd."""
    patch = json.load(open(src))
    names = [os.path.basename(f) for f in embed]
    # Max lists embedded files in the patch's dependency cache
    patch["patcher"]["dependency_cache"] = [
        {"name": n, "bootpath": "~/Documents/Max 9/Max for Live Devices", "type": "TEXT" if n.endswith(".js") else "JSON",
         "implicit": 1} for n in names]
    main_name = os.path.basename(dst)
    files = [("JSON", main_name, (json.dumps(patch, indent="\t") + "\n").encode() + b"\0", 17)]
    for f, n in zip(embed, names):
        files.append(("TEXT" if n.endswith(".js") else "JSON", n, open(f, "rb").read(), 0))
    stamp = int(time.time()) + MAC_EPOCH
    data, entries, offset = b"", b"", 16
    for typ, name, blob, flag in files:
        entries += _field(b"dire", _field(b"type", typ.encode()) + _field(b"fnam", _name(name))
                          + _field(b"sz32", struct.pack(">I", len(blob))) + _field(b"of32", struct.pack(">I", offset))
                          + _field(b"vers", struct.pack(">I", 0)) + _field(b"flag", struct.pack(">I", flag))
                          + _field(b"mdat", struct.pack(">I", stamp & 0xFFFFFFFF)))
        data += blob
        offset += len(blob)
    dlst = _field(b"dlst", entries)
    container = b"mx@c" + struct.pack(">III", 16, 0, 16 + len(data)) + data + dlst
    header = (b"ampf" + struct.pack("<I", 4) + TYPES[kind]
              + b"meta" + struct.pack("<I", 4) + struct.pack("<I", 7)
              + b"ptch" + struct.pack("<I", len(container)))
    open(dst, "wb").write(header + container)


def contents(path):
    """The files inside a frozen device: [{type, fnam, sz32, of32, vers, flag, mdat}, ...]."""
    d = open(path, "rb").read()
    body = d[32:32 + struct.unpack("<I", d[28:32])[0]]
    if body[:4] != b"mx@c":
        return None
    off = struct.unpack(">I", body[12:16])[0]
    assert body[off:off + 4] == b"dlst", "no dlst directory"
    end, p, out = off + struct.unpack(">I", body[off + 4:off + 8])[0], off + 8, []
    while p < end:
        size = struct.unpack(">I", body[p + 4:p + 8])[0]
        entry, q, e = body[p + 8:p + size], 0, {}
        while q < len(entry):
            tag, n = entry[q:q + 4].decode(), struct.unpack(">I", entry[q + 4:q + 8])[0]
            v = entry[q + 8:q + n]
            e[tag] = v.rstrip(b"\0").decode("utf-8") if tag in ("type", "fnam") else struct.unpack(">I", v)[0]
            q += n
        e["data"] = body[e["of32"]:e["of32"] + e["sz32"]]
        out.append(e)
        p += size
    return out


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
    f = sub.add_parser("freeze"); f.add_argument("src"); f.add_argument("dst")
    f.add_argument("--type", choices=TYPES, default="audio"); f.add_argument("--embed", nargs="*", default=[])
    u = sub.add_parser("unpack"); u.add_argument("src"); u.add_argument("dst")
    l = sub.add_parser("list"); l.add_argument("src")
    a = ap.parse_args()
    if a.cmd == "pack":
        pack(a.src, a.dst, a.type)
    elif a.cmd == "freeze":
        freeze(a.src, a.dst, a.type, a.embed)
    elif a.cmd == "list":
        for e in contents(a.src) or []:
            print(f"{e['type']}  {e['sz32']:>8}  flag {e['flag']:>2}  {e['fnam']}")
    else:
        unpack(a.src, a.dst)
