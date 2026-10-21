"""VST3 presets (.vstpreset, Steinberg's format) for a JUCE plugin, the way Live saves them: the header with the
plugin's class id, the processor state ("Comp": JUCE's XML of the parameters, then the VST3 wrapper's private data),
an empty controller state ("Cont"), Live's meta info ("Info") and the chunk list.

Worked out from a preset Live 12 saved for 2sl filter (2sl-filter plugin/references/live-saved.vstpreset), which
`preset_file` rebuilds byte for byte (the kit's tests): the class id is JUCE's (its VST3 component id from the
manufacturer and plugin codes), the private data is JUCE's VST3 wrapper's (bypass off), the meta info Live's.
"""
import re
import struct
from xml.sax.saxutils import quoteattr

from m4l_dev.build_error import BuildError

JUCE_XML_MAGIC = b"VC2!"
# JUCE's VST3 wrapper's private data after the processor state, bypass off: 8 NULs (after the XML's own), then the
# ValueTree "JUCEPrivateData" {Bypass: false} as JUCE writes it, its size and its name again
JUCE_PRIVATE_DATA = (b"\x00" * 9 + b"JUCEPrivateData\x00\x01\x01Bypass\x00\x01\x01\x03\x00"
                     + struct.pack("<q", 29) + b"JUCEPrivateData")


def class_id(manufacturer_code, plugin_code):
    """JUCE's VST3 component id (its JucePluginFactory: 'ABCDEF01', '9182FAEB', then the two four-character codes),
    as the 32 ASCII hex digits a .vstpreset carries."""
    for code in (manufacturer_code, plugin_code):
        if len(code) != 4:
            raise BuildError(f"vstpreset: plugin codes are four characters, got {code!r}")
    return ("ABCDEF019182FAEB" + manufacturer_code.encode().hex().upper() + plugin_code.encode().hex().upper()).encode()


def meta_info(plugin_name, vendor, category):
    """Live's Info chunk."""
    attributes = [("MediaType", "VstPreset"), ("PlugInCategory", category), ("plugtype", category),
                  ("PlugInName", plugin_name), ("plugname", plugin_name), ("PlugInVendor", vendor)]
    body = "".join(f"<Attribute id='{name}' value={quoteattr(value).replace(chr(34), chr(39))} type='string' "
                   f"flags='writeProtected'></Attribute>" for name, value in attributes)
    return ("<?xml version='1.0' encoding='utf-8'?>\n<MetaInfo>" + body + "</MetaInfo>").encode()


def read(data):
    """(class id, {chunk id: bytes}) of a .vstpreset."""
    if data[:4] != b"VST3" or struct.unpack("<i", data[4:8])[0] != 1:
        raise BuildError("vstpreset: not a version 1 .vstpreset")
    list_offset = struct.unpack("<q", data[40:48])[0]
    if data[list_offset:list_offset + 4] != b"List":
        raise BuildError("vstpreset: no chunk list where the header says")
    chunks = {}
    for index in range(struct.unpack("<i", data[list_offset + 4:list_offset + 8])[0]):
        entry = data[list_offset + 8 + 20 * index:list_offset + 28 + 20 * index]
        offset, size = struct.unpack("<qq", entry[4:])
        chunks[entry[:4]] = data[offset:offset + size]
    return data[8:40], chunks


def split_state(component_state):
    """(JUCE's XML, what the VST3 wrapper put after it) of a processor state."""
    if component_state[:4] != JUCE_XML_MAGIC:
        raise BuildError("vstpreset: the processor state isn't JUCE's XML")
    length = struct.unpack("<I", component_state[4:8])[0]
    return component_state[8:8 + length], component_state[8 + length:]


def preset_file(class_id_bytes, xml, info, private_data=JUCE_PRIVATE_DATA):
    """A .vstpreset's bytes, the layout Live writes."""
    component_state = JUCE_XML_MAGIC + struct.pack("<I", len(xml)) + xml + private_data
    body = b"VST3" + struct.pack("<i", 1) + class_id_bytes
    offset = len(body) + 8
    entries = [(b"Comp", offset, len(component_state)), (b"Cont", offset + len(component_state), 0),
               (b"Info", offset + len(component_state), len(info))]
    list_offset = offset + len(component_state) + len(info)
    chunk_list = b"List" + struct.pack("<i", len(entries)) + b"".join(
        chunk + struct.pack("<qq", chunk_offset, size) for chunk, chunk_offset, size in entries)
    return body + struct.pack("<q", list_offset) + component_state + info + chunk_list


def state_xml(state_tag, parameter_values, program, extra=()):
    """The plugin's state as its processor writes it (JUCE's single-line XML): the root `state_tag` with version,
    program and any `extra` [(name, value)] attributes, then a PARAM per parameter, by id. The tag must be an XML
    name: JUCE writes any tag but can't read back one that isn't (a plugin name like "2sl stab"), and the plugin then
    loads every preset and saved set as its defaults (architecture/plugins.md, "The saved state")."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", state_tag):
        raise BuildError(f"vstpreset: the state tag {state_tag!r} isn't an XML name, so the plugin couldn't read its "
                         "presets or saved sets back: use one like 'TwoSlStab', the processor's too")
    attributes = "".join(f" {name}={quoteattr(str(value))}" for name, value in extra)
    params = "".join(f'<PARAM id="{pid}" value="{value!r}"/>' for pid, value in sorted(parameter_values))
    return (f'<?xml version="1.0" encoding="UTF-8"?> <{state_tag} version="1" program="{program}"{attributes}>'
            f"{params}</{state_tag}>").encode("utf-8")


def preset_files(presets, parameters, stored, class_id_bytes, info, state_tag):
    """{"presets/<group>/<name>.vstpreset": bytes} for each of `presets` [(title, held, stored values)]. A Stored
    value goes in as an attribute of the state, named by its id."""
    files = {}
    for program, (title, held, kept) in enumerate(presets):
        group, _, name = title.rpartition(": ")
        path = "/".join(["presets"] + ([group] if group else []) + [f"{name}.vstpreset"])
        xml = state_xml(state_tag, [(p["id"], value) for p, value in zip(parameters, held)], program,
                        [(s["id"], repr(value)) for s, value in zip(stored, kept)])
        files[path] = preset_file(class_id_bytes, xml, info)
    return files
