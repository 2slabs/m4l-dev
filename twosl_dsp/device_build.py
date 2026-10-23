"""build_device: check a device's patch, generate its scripts, and write the development build and the release.

    build_device(repository, patch, layout, views_code, device_scripts, live_preset_files=None,
                 command_line_arguments=())

In order, and nothing is written until every check has passed:
  1. the patch's checks (DevicePatchBuilder.check: Init values, presets, gen~ Params, layout with the chrome's
     labels, Info text, names, wires)
  2. the scripts: the UI and views scripts from the kit's templates, and the device's own (`device_scripts`,
     {file name: text}, already filled in), every one checked as ES5; every message a script sends straight into a
     gen~ names a Param of it (DevicePatchBuilder.check_script_messages_into_gen); no display draws text over text or
     off itself, first painted or driven through its inputs (DevicePatchBuilder.check_display_texts); the patch and every script hold only numbers
     that went through generated_number (twosl_dsp/generated_numbers.py)
  3. the Live parameter lock (src/live-parameters.lock.json): fails with a diff on any change, unless
     --accept-live-parameter-changes is among `command_line_arguments`
  4. devices/<script name>/: the patch (.maxpat), the development device (.amxd), the scripts, and the Live presets
     (.adv) when the device ships them (`live_preset_files`), stale .adv files removed
  5. dist/<script name>-<version>/: the frozen device (the scripts embedded) with Live presets made for it, and that
     folder zipped as dist/<script name>-<version>.zip

Every byte written depends only on the sources (no clock, no Python-version detail, no maths library's last digits),
so a rebuild of the same sources writes the same files on every machine.
"""
import argparse
import json
import os
import shutil
import zipfile

from twosl_dsp import amxd
from twosl_dsp import live_parameter_identity
from twosl_dsp.build_error import BuildError
from twosl_dsp.generated_numbers import check_generated_text, literals_held_by_the_lock
from twosl_dsp.generated_scripts import check_es5
from twosl_dsp.live_preset_files import remove_stale_live_presets, write_live_presets

ZIP_ENTRY_DATE = (1980, 1, 1, 0, 0, 0)      # the earliest a zip can hold: the archive doesn't depend on the clock


def log(message):
    print(message)


def parse_build_arguments(command_line_arguments):
    parser = argparse.ArgumentParser(description="Build the device: devices/ (committed) and dist/ (the release).")
    parser.add_argument(live_parameter_identity.ACCEPT_CHANGES_FLAG, dest="accept_live_parameter_changes",
                        action="store_true",
                        help=f"rewrite src/{live_parameter_identity.LOCK_FILE_NAME} to the parameters as built "
                             "(a change to what Live knows them by: say what it breaks in the release notes)")
    return parser.parse_args(list(command_line_arguments))


def write_bytes(repository, path, data):
    repository.check_writable(path)
    with open(path, "wb") as output_file:
        output_file.write(data)


def build_device(repository, patch, layout, views_code, device_scripts, live_preset_files=None,
                 command_line_arguments=()):
    """Check and write the device `patch` (a DevicePatchBuilder) into `repository` (a DeviceRepository).

    layout: the chrome's rules and labels per page (DevicePatchBuilder.views_script); views_code: the device's
    displays, ES5, inserted into the kit's views template; device_scripts: {file name: text}, the device's other
    generated scripts (its brain), written next to the device and embedded in the release; live_preset_files: a
    LivePresetFiles when the device ships its presets as Live preset files, else None."""
    arguments = parse_build_arguments(command_line_arguments)
    presets = patch.check(layout)
    patch_json = patch.patch()
    scripts = dict(device_scripts)
    for kit_script_name, kit_script_text in ((patch.ui_script_name(), patch.ui_script(presets)),
                                             (patch.views_script_name(), patch.views_script(layout, views_code))):
        if kit_script_name in scripts:
            raise BuildError(f"{patch.device_name}: the device's scripts include {kit_script_name}, which the kit writes")
        scripts[kit_script_name] = kit_script_text
    check_es5(scripts)
    patch.check_script_messages_into_gen(scripts)
    patch.check_display_texts(scripts[patch.views_script_name()])
    identity = live_parameter_identity.device_identity(patch_json, patch.device_type)
    held_by_the_lock = literals_held_by_the_lock(live_parameter_identity.lock_text(identity))
    maxpat_text = json.dumps(patch_json, indent="\t")
    for file_name, text in [(f"{patch.script_name}.maxpat", maxpat_text)] + sorted(scripts.items()):
        check_generated_text(text, f"{patch.device_name}: {file_name}", held_by_the_lock)
    lock_path = repository.source_path(live_parameter_identity.LOCK_FILE_NAME)
    log(live_parameter_identity.check_lock(lock_path, identity, arguments.accept_live_parameter_changes,
                                           repository.relative(lock_path)))

    # the development build: the device and its scripts side by side, in the repository
    device_directory = repository.device_directory(patch.script_name)
    os.makedirs(repository.check_writable(device_directory), exist_ok=True)
    maxpat_path = os.path.join(device_directory, f"{patch.script_name}.maxpat")
    write_bytes(repository, maxpat_path, maxpat_text.encode())
    device_path = os.path.join(device_directory, f"{patch.script_name}.amxd")
    write_bytes(repository, device_path, amxd.unfrozen_device_bytes(patch_json, patch.device_type))
    for script_name, script_text in sorted(scripts.items()):
        write_bytes(repository, os.path.join(device_directory, script_name), script_text.encode())
    log(f"wrote {repository.relative(device_directory)}/: {os.path.basename(maxpat_path)}, {os.path.basename(device_path)} "
        f"({len(patch.boxes)} boxes, {patch.device_width} px wide) and {', '.join(sorted(scripts))}")
    if live_preset_files is not None:
        write_live_presets(device_path, patch_json, patch.device_type, presets, live_preset_files, log)
    else:
        remove_stale_live_presets(device_directory, [], log)

    # The release: one folder, the frozen device (one self-contained file, the scripts embedded) with the presets
    # made for that file, and the folder zipped to download as one file. Made fresh every build (dist/ isn't in git).
    release_name = f"{patch.script_name}-{patch.version}"
    release_folder = os.path.join(repository.dist_directory, release_name)
    repository.check_writable(release_folder)
    if os.path.exists(release_folder):
        shutil.rmtree(release_folder)
    os.makedirs(release_folder)
    frozen_path = os.path.join(release_folder, f"{release_name}.amxd")
    # the device's scripts first, then the UI and views scripts (the order Max's dependency cache lists them in)
    embedded = [(script_name, script_text.encode()) for script_name, script_text in scripts.items()]
    write_bytes(repository, frozen_path, amxd.frozen_device_bytes(patch_json, patch.device_type,
                                                                  os.path.basename(frozen_path), embedded))
    log(f"froze {repository.relative(frozen_path)} ({os.path.getsize(frozen_path) // 1024} KB, scripts embedded)")
    release_files = [os.path.basename(frozen_path)]
    if live_preset_files is not None:
        release_files += sorted(write_live_presets(frozen_path, patch_json, patch.device_type, presets,
                                                   live_preset_files, log))
    release_zip = os.path.join(repository.dist_directory, f"{release_name}.zip")
    repository.check_writable(release_zip)
    with zipfile.ZipFile(release_zip, "w", zipfile.ZIP_DEFLATED) as release_archive:
        for file_name in release_files:
            entry = zipfile.ZipInfo(f"{release_name}/{file_name}", date_time=ZIP_ENTRY_DATE)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            with open(os.path.join(release_folder, file_name), "rb") as release_file:
                release_archive.writestr(entry, release_file.read())
    log(f"zipped {repository.relative(release_folder)} as {repository.relative(release_zip)} "
        f"({os.path.getsize(release_zip) // 1024} KB)")
    return presets
