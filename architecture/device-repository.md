# The device repository contract

Every 2sl Max for Live device has its own repository, with the kit as a git submodule:

```
<device repo>/
  build.py                     the entry point: python3 build.py [--accept-live-parameter-changes]
  2sl-dsp/                     this kit (git submodule add https://github.com/2slabs/2sl-dsp.git 2sl-dsp)
  src/                         hand-written sources only: the device's Python, its script templates, its preset
                               book, and live-parameters.lock.json (written by the build, reviewed by hand)
  devices/<script name>/       the development build, written by the build and committed: <name>.maxpat,
                               <name>.amxd, its scripts, its .adv presets. Add devices/ to Live's browser to use it.
  dist/                        the release, written by the build, not committed (.gitignore): <name>-<version>/
                               (the frozen device and its presets) and <name>-<version>.zip
  tests/  references/  architecture/  README.md  LICENSE  SHORTCUTS.md
```

`build.py` puts `2sl-dsp/` and `src/` on `sys.path`, then `DeviceRepository.of_build_script(__file__)` finds the
root from the entry point and fails loudly unless `src/` exists, `2sl-dsp/` is an initialised submodule, and the kit
running is that submodule (not another checkout that happened to be on the path).

Why:
- **One kit, many devices, each pinned.** The submodule commit is the kit version a device was built with; a kit
  change reaches a device only when its repository moves the pointer, and its own tests (the committed build is what
  the sources build) say whether anything changed.
- **The kit is never written by a build.** Every path a build writes goes through `DeviceRepository.check_writable`,
  which refuses the kit's folder and anything outside the repository.
- **Generated output is committed, so it can be reviewed.** `devices/` is what Live loads in development and what a
  diff shows; it must be exactly what the sources build (a device's tests check it byte for byte).
- **src/ is hand-written only.** Nothing the build writes goes in src/ except the parameter lock, which is the
  reviewed record of what Live knows the parameters by (live-parameter-identity.md).
- **The tests compare the build exactly and sound as sound.** A device's tests hold devices/ and every generated file
  to the byte, and compare any two renders (presets before and after, plugin vs device) with the kit's
  `render_comparison`, never `==` (testing.md); they report "within tolerance: residual X dB".
