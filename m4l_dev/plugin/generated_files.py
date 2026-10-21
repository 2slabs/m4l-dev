"""A plugin's generated folder (plugin/generated/): written from the device's sources by its plugin/generate.py, and
checked to be what they make (a test runs `--check`, so a changed device can't silently leave its plugin behind)."""
import os

from m4l_dev.generated_numbers import check_generated_text, literals_held_by_the_lock


def as_bytes(content):
    return content if isinstance(content, bytes) else content.encode("utf-8")


def files_in(folder):
    found = set()
    for directory, _, names in os.walk(folder):
        for name in names:
            found.add(os.path.relpath(os.path.join(directory, name), folder).replace(os.sep, "/"))
    return found


def stale(folder, files):
    """The paths in `folder` that aren't `files` ({relative path: text or bytes}): changed, missing or left over."""
    changed = sorted(name for name, content in files.items()
                     if not os.path.exists(os.path.join(folder, name))
                     or open(os.path.join(folder, name), "rb").read() != as_bytes(content))
    return changed + sorted(files_in(folder) - set(files)) if os.path.isdir(folder) else sorted(files)


def write(folder, files):
    """Makes `folder` hold exactly `files`."""
    if os.path.isdir(folder):
        for name in files_in(folder) - set(files):
            os.remove(os.path.join(folder, name))
    for name, content in files.items():
        path = os.path.join(folder, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(as_bytes(content))


def check_numbers(files, label, lock_path):
    """Every file's numbers went through generated_number (m4l_dev/generated_numbers.py) or are held by the Live
    parameter lock at `lock_path`, so every machine generates the same bytes (a binary file, a .vstpreset, read for
    the text it carries: its state XML)."""
    with open(lock_path, encoding="utf-8") as handle:
        held_by_the_lock = literals_held_by_the_lock(handle.read())
    for name, content in sorted(files.items()):
        check_generated_text(content if isinstance(content, str) else content.decode("latin-1"), f"{label}{name}",
                             held_by_the_lock)


def main(folder, files, argv, label, lock_path):
    """The generator's command line: write, or with --check say what's stale and fail. `lock_path`: the device's Live
    parameter lock (src/live-parameters.lock.json), whose numbers the files may hold as they are."""
    check_numbers(files, label, lock_path)
    if "--check" in argv:
        out_of_date = stale(folder, files)
        if out_of_date:
            print(f"{label} is out of date ({', '.join(out_of_date[:6])}{' ...' if len(out_of_date) > 6 else ''}): "
                  "run python3 plugin/generate.py")
            return 1
        print(f"{label} is up to date")
        return 0
    write(folder, files)
    presets = sum(1 for name in files if name.startswith("presets/"))
    print(f"wrote {label}: {len(files) - presets} sources and {presets} presets")
    return 0
