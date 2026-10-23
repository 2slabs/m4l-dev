"""Two builds of a device compared the way a device's tests compare them: exactly, on every machine (every number a
build writes goes through twosl_dsp/generated_numbers.py, so no maths library's last digits reach a file), saying
where they differ.

    from twosl_dsp.build_comparison import build_differences
    problems = build_differences(built_folder, committed_folder)    # [] when they're the same build

What is compared, by file:
  .adv            the preset's XML (the gzip around it is zlib's, which may compress differently on another machine)
  anything else   its bytes
and where two differ, the first place: .maxpat and .json value by value, .amxd its device type and patch (unfrozen)
or each frozen file, .adv tag by tag, text by character.
"""
import gzip
import json
import os
import xml.etree.ElementTree as ElementTree

from twosl_dsp.amxd import read_device


def text_difference(a, b, where):
    """None when two texts are the same, else where they first differ."""
    if a == b:
        return None
    for index, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"{where}: the text differs at character {index}: {a[max(0, index - 30):index + 30]!r} vs " \
                   f"{b[max(0, index - 30):index + 30]!r}"
    return f"{where}: one text is longer ({len(a)} vs {len(b)} characters)"


def json_difference(a, b, where):
    """None when two JSON values are the same, else where they first differ."""
    if type(a) is not type(b):
        return f"{where}: a {type(a).__name__} vs a {type(b).__name__} ({a!r} vs {b!r})"
    if isinstance(a, str):
        return text_difference(a, b, where)
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{where}: {len(a)} items vs {len(b)}"
        for index, (x, y) in enumerate(zip(a, b)):
            found = json_difference(x, y, f"{where}[{index}]")
            if found:
                return found
        return None
    if isinstance(a, dict):
        if list(a) != list(b):
            return f"{where}: keys {sorted(set(a) ^ set(b)) or 'in another order'} are in one and not the other"
        for key in a:
            found = json_difference(a[key], b[key], f"{where}.{key}")
            if found:
                return found
        return None
    return None if repr(a) == repr(b) else f"{where}: {a!r} vs {b!r}"


def xml_difference(a, b, where):
    if a.tag != b.tag:
        return f"{where}: <{a.tag}> vs <{b.tag}>"
    here = f"{where}/{a.tag}"
    if a.attrib != b.attrib:
        names = sorted(set(a.attrib) | set(b.attrib))
        return f"{here}: " + "; ".join(f"@{name} {a.attrib.get(name)!r} vs {b.attrib.get(name)!r}" for name in names
                                       if a.attrib.get(name) != b.attrib.get(name))
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


def where_they_differ(name, a, b):
    """Where two different builds of the file `name` (bytes) first differ."""
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
        return xml_difference(ElementTree.fromstring(a), ElementTree.fromstring(b), name)
    try:
        return text_difference(a.decode("utf-8"), b.decode("utf-8"), name)
    except UnicodeDecodeError:
        return None


def file_difference(name, a, b):
    """None when two builds of the file `name` (bytes) are the same build, else what differs."""
    if os.path.splitext(name)[1] == ".adv":
        a, b = gzip.decompress(a), gzip.decompress(b)
    if a == b:
        return None
    return where_they_differ(name, a, b) or f"{name}: the bytes differ"


def build_differences(built_folder, committed_folder):
    """What differs between two builds of a device (two folders): [] when they're the same build."""
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
