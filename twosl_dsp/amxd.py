"""Max for Live device files (.amxd): unfrozen (the patch as JSON) and frozen (the patch and its files in one).

Unfrozen .amxd = a 32-byte header ('ampf', the device type, 'meta', 'ptch' + length) + the patcher JSON.
Frozen .amxd   = the same header, then an 'mx@c' container holding the patch and every file it needs (js,
abstractions...) plus a 'dlst' directory of them: the layout Max's Freeze button writes, worked out from frozen
devices that ship with Live. A frozen device is one self-contained file.

The bytes depend only on the inputs: every embedded file's modification date (mdat) is FROZEN_FILE_MODIFICATION_DATE,
not the clock, so two builds of the same sources freeze to the same file.
"""
import copy
import json
import struct

from twosl_dsp.build_error import BuildError

DEVICE_TYPE_CODES = {"audio": b"aaaa", "midi": b"mmmm", "instrument": b"iiii"}
MAC_EPOCH_OFFSET = 2082844800             # seconds from 1904-01-01 (Max's timestamps) to 1970-01-01
# 2026-01-01T00:00:00Z in Max's (Mac) seconds. No source says how Max uses mdat; a fixed date keeps freezing
# repeatable (SHORTCUTS.md, 2026-10-16).
FROZEN_FILE_MODIFICATION_DATE = 1767225600 + MAC_EPOCH_OFFSET
FROZEN_MAIN_PATCH_FLAG = 17
FROZEN_DEPENDENCY_SEARCH_PATH = "~/Documents/Max 9/Max for Live Devices"


def patch_json_bytes(patch):
    """A patch as an .amxd carries it: tab-indented JSON, a newline, a NUL."""
    return (json.dumps(patch, indent="\t") + "\n").encode() + b"\0"


def _header(device_type, meta_value, body_length):
    if device_type not in DEVICE_TYPE_CODES:
        raise BuildError(f"amxd: device type {device_type!r} isn't one of {sorted(DEVICE_TYPE_CODES)}")
    return (b"ampf" + struct.pack("<I", 4) + DEVICE_TYPE_CODES[device_type]
            + b"meta" + struct.pack("<I", 4) + struct.pack("<I", meta_value)
            + b"ptch" + struct.pack("<I", body_length))


def unfrozen_device_bytes(patch, device_type):
    """The development device: the patch, its scripts beside it on disk."""
    body = patch_json_bytes(patch)
    return _header(device_type, 0, len(body)) + body


def _field(tag, data):
    return tag + struct.pack(">I", 8 + len(data)) + data


def _file_name_field_value(file_name):
    raw = file_name.encode("utf-8") + b"\0"
    return raw + b"\0" * (-len(raw) % 4)


def _embedded_file_type(file_name):
    return "TEXT" if file_name.endswith(".js") else "JSON"


def frozen_device_bytes(patch, device_type, frozen_file_name, embedded_files):
    """The release: the patch and `embedded_files` ([(file name, bytes)]) in one file named `frozen_file_name`."""
    patch = copy.deepcopy(patch)
    # Max lists embedded files in the patch's dependency cache
    patch["patcher"]["dependency_cache"] = [
        {"name": name, "bootpath": FROZEN_DEPENDENCY_SEARCH_PATH, "type": _embedded_file_type(name), "implicit": 1}
        for name, _ in embedded_files]
    files = [("JSON", frozen_file_name, patch_json_bytes(patch), FROZEN_MAIN_PATCH_FLAG)]
    files += [(_embedded_file_type(name), name, data, 0) for name, data in embedded_files]
    data, entries, offset = b"", b"", 16
    for file_type, file_name, file_bytes, flag in files:
        entries += _field(b"dire", _field(b"type", file_type.encode()) + _field(b"fnam", _file_name_field_value(file_name))
                          + _field(b"sz32", struct.pack(">I", len(file_bytes))) + _field(b"of32", struct.pack(">I", offset))
                          + _field(b"vers", struct.pack(">I", 0)) + _field(b"flag", struct.pack(">I", flag))
                          + _field(b"mdat", struct.pack(">I", FROZEN_FILE_MODIFICATION_DATE & 0xFFFFFFFF)))
        data += file_bytes
        offset += len(file_bytes)
    container = b"mx@c" + struct.pack(">III", 16, 0, 16 + len(data)) + data + _field(b"dlst", entries)
    return _header(device_type, 7, len(container)) + container


def read_device(device_bytes, where):
    """An .amxd as {"device_type", "patch" (None when frozen), "frozen_files" (None when unfrozen: else [{type,
    fnam, sz32, of32, vers, flag, mdat, data}])}."""
    if device_bytes[:4] != b"ampf" or device_bytes[24:28] != b"ptch":
        raise BuildError(f"{where}: not an .amxd file (no ampf / ptch header)")
    type_names = {code: name for name, code in DEVICE_TYPE_CODES.items()}
    device_type = type_names.get(device_bytes[8:12], device_bytes[8:12].decode("latin-1"))
    body = device_bytes[32:32 + struct.unpack("<I", device_bytes[28:32])[0]]
    if body[:4] != b"mx@c":
        return {"device_type": device_type, "patch": json.loads(body.rstrip(b"\0")), "frozen_files": None}
    directory_offset = struct.unpack(">I", body[12:16])[0]
    if body[directory_offset:directory_offset + 4] != b"dlst":
        raise BuildError(f"{where}: frozen device has no dlst directory at {directory_offset}")
    directory_end = directory_offset + struct.unpack(">I", body[directory_offset + 4:directory_offset + 8])[0]
    position, frozen_files = directory_offset + 8, []
    while position < directory_end:
        entry_size = struct.unpack(">I", body[position + 4:position + 8])[0]
        entry_bytes, field_position, entry = body[position + 8:position + entry_size], 0, {}
        while field_position < len(entry_bytes):
            tag = entry_bytes[field_position:field_position + 4].decode()
            field_size = struct.unpack(">I", entry_bytes[field_position + 4:field_position + 8])[0]
            if field_size < 8:
                raise BuildError(f"{where}: frozen directory field {tag!r} has impossible size {field_size}")
            value = entry_bytes[field_position + 8:field_position + field_size]
            entry[tag] = value.rstrip(b"\0").decode("utf-8") if tag in ("type", "fnam") else struct.unpack(">I", value)[0]
            field_position += field_size
        entry["data"] = body[entry["of32"]:entry["of32"] + entry["sz32"]]
        frozen_files.append(entry)
        position += entry_size
    return {"device_type": device_type, "patch": None, "frozen_files": frozen_files}
