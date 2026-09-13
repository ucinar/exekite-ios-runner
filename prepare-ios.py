"""Apply current Ship identity to the disposable iOS source tree before import."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import sys


def rewrite_section(text: str, section: str, values: dict[str, str]) -> str:
    lines = text.splitlines()
    header = "[" + section + "]"
    begin = next((i for i, line in enumerate(lines) if line.strip() == header), None)
    if begin is None:
        return text.rstrip("\n") + "\n\n" + header + "\n" + "\n".join(k + "=" + v for k, v in values.items()) + "\n"
    end = next((i for i in range(begin + 1, len(lines)) if lines[i].startswith("[")), len(lines))
    kept = [line for line in lines[begin + 1:end] if line.split("=", 1)[0].strip() not in values]
    lines[begin + 1:end] = [k + "=" + v for k, v in values.items()] + kept
    return "\n".join(lines) + "\n"


project = Path(sys.argv[1])
manifest = json.loads((project / ".exekite/launch_manifest.json").read_text(encoding="utf-8"))
info = manifest["info"]
title = info["title"].strip()
version = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?", info["version"].strip())
if not title or version is None:
    raise ValueError("Ship title and semantic version are required")
# Apple native version fields are numeric; full SemVer remains in the bundle.
numeric_version = ".".join(str(int(part)) for part in version.groups())
project_id = re.sub(r"[^a-z0-9]", "", os.environ.get("EXEKITE_PROJECT_ID", project.name).lower())
bundle_id = info.get("bundle_identifier") or ("com.exekite." + project_id)
if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+", bundle_id):
    raise ValueError("Invalid iOS bundle identifier")
icon = manifest["assets"]["icon"]
if icon.get("status") != "ready" or icon.get("path") != "marketing/icon.png":
    raise ValueError("A ready canonical Ship icon is required")
# marketing is .gdignore'd; this importable copy is the actual app icon.
shutil.copyfile(project / "marketing/icon.png", project / "ios_icon.png")

cfg = project / "export_presets.cfg"
text = cfg.read_text(encoding="utf-8") if cfg.is_file() else ""
sections = list(re.finditer(r"^\[preset\.(\d+)\]\s*$", text, re.MULTILINE))
index = None
for pos, section in enumerate(sections):
    end = sections[pos + 1].start() if pos + 1 < len(sections) else len(text)
    if re.search(r'^platform="iOS"\s*$', text[section.end():end], re.MULTILINE):
        index = int(section.group(1))
        break
if index is None:
    index = max((int(section.group(1)) for section in sections), default=-1) + 1
    text = rewrite_section(text, "preset." + str(index), {
        "platform": '"iOS"', "runnable": "true", "advanced_options": "false",
        "dedicated_server": "false", "custom_features": '""',
        "export_filter": '"all_resources"', "include_filter": '""', "exclude_filter": '""',
        "export_path": '"build/ios/game.ipa"', "encryption_include_filters": '""',
        "encryption_exclude_filters": '""', "seed": "0", "encrypt_pck": "false",
        "encrypt_directory": "false", "script_export_mode": "2",
    })
    text = rewrite_section(text, "preset." + str(index) + ".options", {
        # Required by Godot project validation; the Xcode build remains unsigned.
        "application/app_store_team_id": json.dumps(os.environ.get("EXEKITE_IOS_TEAM_ID", "0000000000")),
        "application/signature": '""', "application/min_ios_version": '"12.0"',
        "application/targeted_device_family": "2", "application/export_project_only": "true",
        "application/delete_old_export_files_unconditionally": "true", "application/icon_interpolation": "4",
        "texture_format/etc2_astc": "true", "texture_format/s3tc_bptc": "false",
    })
text = rewrite_section(text, "preset." + str(index), {"name": '"iOS"'})
text = rewrite_section(text, "preset." + str(index) + ".options", {
    "application/bundle_identifier": json.dumps(bundle_id),
    "application/short_version": json.dumps(numeric_version),
    "application/version": json.dumps(numeric_version),
    "icons/icon_1024x1024": '"res://ios_icon.png"',
})
cfg.write_text(text, encoding="utf-8")

pg = project / "project.godot"
text = rewrite_section(pg.read_text(encoding="utf-8"), "application", {"config/name": json.dumps(title, ensure_ascii=False)})
text = rewrite_section(text, "rendering", {"textures/vram_compression/import_etc2_astc": "true"})
pg.write_text(text, encoding="utf-8")
print("Current Ship title, native version, bundle id and app icon applied")
