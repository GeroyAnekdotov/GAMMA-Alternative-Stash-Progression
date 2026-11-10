"""Validate and build the installable GAMMA Alternative Stash Progression ZIP."""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "gamma_alternative_stash_progression"
XML = f"st_{SCRIPT}.xml"
FILES = {
    f"gamedata/scripts/{SCRIPT}.script",
    f"gamedata/scripts/{SCRIPT}_mcm.script",
    "gamedata/scripts/gamma_alternative_stash_backend.script",
    "gamedata/scripts/gamma_alternative_stash_debug.script",
    f"gamedata/configs/text/eng/{XML}",
    f"gamedata/configs/text/rus/{XML}",
}
STRINGS = {
    f"ui_mcm_menu_{SCRIPT}",
    f"ui_mcm_{SCRIPT}_progression_info",
    f"ui_mcm_{SCRIPT}_mechanics_info",
    *(f"ui_mcm_{SCRIPT}_{key}{suffix}"
      for key in ("enabled", "include_zombified_stalkers", "debug_mode", "preset", "stash_chance", "yellow_chance")
      for suffix in ("", "_desc", "_hint")),
    *(f"{SCRIPT}_preset_lst_gasp_preset_{key}"
      for key in ("slow", "medium", "fast", "very_fast", "custom")),
}


def read_payload():
    paths = {
        path.relative_to(ROOT).as_posix(): path
        for path in (ROOT / "gamedata").rglob("*")
        if path.is_file()
    }
    if paths.keys() != FILES:
        raise ValueError(f"Unexpected or missing payload files: {paths.keys() ^ FILES}")
    payload = {}
    for name, path in sorted(paths.items()):
        data = path.read_bytes()
        if path.suffix == ".xml":
            if not data.startswith(b'<?xml version="1.0" encoding="windows-1251"?>'):
                raise ValueError(f"Expected Windows-1251 declaration in {name}")
            text = data.decode("cp1251")
            if "/rus/" in name and ("Учитывать зомбированных сталкеров" not in text):
                raise ValueError(f"Invalid Russian label or encoding in {name}")
            root = ElementTree.fromstring(text)
            ids = [entry.get("id") for entry in root]
            if (
                root.tag != "string_table"
                or sorted(ids) != sorted(STRINGS)
                or any(entry.tag != "string" or not entry.findtext("text") for entry in root)
                or any("warfare" in entry.findtext("text").lower() for entry in root)
            ):
                raise ValueError(f"Invalid MCM localization in {name}")
        payload[name] = data
    return payload


def verify_zip(path, payload):
    with ZipFile(path) as archive:
        if sorted(archive.namelist()) != sorted(payload) or archive.testzip() is not None:
            raise ValueError(f"ZIP structure or CRC check failed for {path.name}")
        if any(archive.read(name) != data for name, data in payload.items()):
            raise ValueError(f"Payload differs in {path.name}. Assign a new version.")


def build(payload, *, test=False):
    metadata = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    version = metadata["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Expected a three-part release version")
    name = metadata["project"].replace(" ", "_")
    package_type = "TEST_MO2" if test else metadata["package_type"]
    output = ROOT / "dist" / f"{name}_v{version}_{package_type}.zip"
    output.parent.mkdir(exist_ok=True)

    if not output.exists():
        with tempfile.TemporaryDirectory(dir=output.parent) as staging:
            candidate = Path(staging) / output.name
            with ZipFile(candidate, "w") as archive:
                for name, data in payload.items():
                    archive.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)
            verify_zip(candidate, payload)
            try:
                os.link(candidate, output)
            except FileExistsError:
                pass  # A concurrent builder wrote this version. Verify its payload.

    verify_zip(output, payload)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(
        f"{checksum}  {output.name}\n", encoding="ascii", newline="\n"
    )
    print(f"Verified {output} (SHA-256 {checksum})")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without building or delivering")
    parser.add_argument("--test", action="store_true", help="build an installable TEST_MO2 ZIP")
    args = parser.parse_args()
    payload = read_payload()
    if args.check:
        print(f"Validated {len(payload)} payload files")
        return

    output = build(payload, test=args.test)
    shared_tools = ROOT.parent / "_tools"
    if not (shared_tools / "deliver_mo2.py").is_file():
        print("MO2 delivery skipped: shared helper unavailable")
        return

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(shared_tools))
    from deliver_mo2 import deliver_mo2_zip

    deliver_mo2_zip(output)


if __name__ == "__main__":
    main()
