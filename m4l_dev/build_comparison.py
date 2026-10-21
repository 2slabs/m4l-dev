"""Two builds of a device compared the way a device's tests compare them: everything exactly, except that numbers only
have to be close.

Floating point isn't the same to the last digit on every machine: math.exp, math.log and pow can round differently in
the last bit between maths libraries, so a value computed in Python (a filter's coefficients, say) can print as
0.6095243148961883 on one machine and 0.6095243148961881 on another. Nobody hears one part in 10^15, so a committed
build made on one machine has to pass the test on another. Integers, text and structure still have to match exactly,
and numbers to RELATIVE (or ABSOLUTE near zero), so a real change still fails.

    from m4l_dev.build_comparison import build_differences
    problems = build_differences(built_folder, committed_folder)    # [] when they're the same build

What is compared, by file:
  .maxpat, .json  the JSON, value by value; a string's numbers are compared as numbers (gen~ code is one string)
  .amxd           its device type and patch (unfrozen), or each frozen file by name and contents (frozen); sizes and
                  offsets in the container follow the contents' lengths and aren't compared
  .adv            the preset's XML, tag by tag and attribute by attribute, except OriginalFileSize and OriginalCrc,
                  which are the .amxd's exact bytes and follow its last digits
  anything else   as UTF-8 text with numbers compared as numbers; bytes exactly if it isn't text
"""
import gzip
import json
import math
import os
import re
import xml.etree.ElementTree as ElementTree

from m4l_dev.amxd import read_device

RELATIVE = 1e-9
ABSOLUTE = 1e-12
# what a preset file says about the device file's exact bytes
ADV_ELEMENTS_OF_THE_DEVICE_BYTES = ("OriginalFileSize", "OriginalCrc")
NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def close(a, b):
    return math.isclose(a, b, rel_tol=RELATIVE, abs_tol=ABSOLUTE)


def text_difference(a, b, where):
    """None when two texts are the same apart from their numbers' last digits, else what differs."""
    if a == b:
        return None
    parts_a, parts_b = NUMBER.split(a), NUMBER.split(b)
    numbers_a, numbers_b = NUMBER.findall(a), NUMBER.findall(b)
    if parts_a != parts_b or len(numbers_a) != len(numbers_b):
        for index, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return f"{where}: the text differs at character {index}: {a[max(0, index - 30):index + 30]!r} vs " \
                       f"{b[max(0, index - 30):index + 30]!r}"
        return f"{where}: one text is longer ({len(a)} vs {len(b)} characters)"
    for x, y in zip(numbers_a, numbers_b):
        if x != y and not close(float(x), float(y)):
            return f"{where}: {x} vs {y}"
    return None


def json_difference(a, b, where):
    """None when two JSON values are the same apart from numbers' last digits, else what differs."""
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return None if a == b else f"{where}: {a!r} vs {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, int) and isinstance(b, int):
            return None if a == b else f"{where}: {a} vs {b}"
        return None if close(a, b) else f"{where}: {a!r} vs {b!r}"
    if isinstance(a, str) and isinstance(b, str):
        return text_difference(a, b, where)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{where}: {len(a)} items vs {len(b)}"
        for index, (x, y) in enumerate(zip(a, b)):
            found = json_difference(x, y, f"{where}[{index}]")
            if found:
                return found
        return None
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return f"{where}: keys {sorted(set(a) ^ set(b))} are in one and not the other"
        for key in a:
            found = json_difference(a[key], b[key], f"{where}.{key}")
            if found:
                return found
        return None
    return f"{where}: a {type(a).__name__} vs a {type(b).__name__}"


def xml_difference(a, b, where):
    if a.tag != b.tag:
        return f"{where}: <{a.tag}> vs <{b.tag}>"
    here = f"{where}/{a.tag}"
    if a.tag in ADV_ELEMENTS_OF_THE_DEVICE_BYTES:
        return None
    if set(a.attrib) != set(b.attrib):
        return f"{here}: attributes {sorted(set(a.attrib) ^ set(b.attrib))} are in one and not the other"
    for name in a.attrib:
        found = text_difference(a.attrib[name], b.attrib[name], f"{here}@{name}")
        if found:
            return found
    found = text_difference((a.text or "").strip(), (b.text or "").strip(), here)
    if found:
        return found
    if len(a) != len(b):
        return f"{here}: {len(a)} children vs {len(b)}"
    for x, y in zip(a, b):
        found = xml_difference(x, y, here)
        if found:
            return found
    return None


def file_difference(name, a, b):
    """None when two builds of the file `name` (bytes) are the same build, else what differs."""
    if a == b:
        return None
    extension = os.path.splitext(name)[1]
    if extension == ".amxd":
        device_a, device_b = read_device(a, name), read_device(b, name)
        if device_a["device_type"] != device_b["device_type"]:
            return f"{name}: a {device_a['device_type']} device vs a {device_b['device_type']} one"
        if device_a["patch"] is not None or device_b["patch"] is not None:
            return json_difference(device_a["patch"], device_b["patch"], name)
        files_a, files_b = device_a["frozen_files"], device_b["frozen_files"]
        if [f["fnam"] for f in files_a] != [f["fnam"] for f in files_b]:
            return f"{name}: frozen files {[f['fnam'] for f in files_a]} vs {[f['fnam'] for f in files_b]}"
        for x, y in zip(files_a, files_b):
            found = file_difference(f"{name}/{x['fnam']}", x["data"].rstrip(b"\0"), y["data"].rstrip(b"\0"))
            if found:
                return found
        return None
    if extension in (".maxpat", ".json"):
        return json_difference(json.loads(a), json.loads(b), name)
    if extension == ".adv":
        return xml_difference(ElementTree.fromstring(gzip.decompress(a)), ElementTree.fromstring(gzip.decompress(b)), name)
    try:
        return text_difference(a.decode("utf-8"), b.decode("utf-8"), name)
    except UnicodeDecodeError:
        return f"{name}: the bytes differ"


def build_differences(built_folder, committed_folder):
    """What differs between two builds of a device (two folders): [] when they're the same build, numbers' last
    digits aside."""
    built, committed = sorted(os.listdir(built_folder)), sorted(os.listdir(committed_folder))
    if built != committed:
        return [f"the files differ: {sorted(set(built) ^ set(committed))} are in one build and not the other"]
    problems = []
    for name in built:
        with open(os.path.join(built_folder, name), "rb") as a, open(os.path.join(committed_folder, name), "rb") as b:
            found = file_difference(name, a.read(), b.read())
        if found:
            problems.append(found)
    return problems
