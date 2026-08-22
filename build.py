#!/usr/bin/env python3
"""Inspect and package a Unity OBB with an APK using REapk 0.1.1.

By default this command refuses to emit an APK because REapk 0.1.1 does not
provide a supported operation for declaring a new Application/Activity hook
or adding a method/class to class_data. Use --no-inject only for the explicit
non-standalone packaging operation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

from reapk import Apk
from reapk.sign import apk_sign_v2
from reapk.zipalign import read_zip_entries, stored_entry, write_aligned_zip

OBB_RE = re.compile(r"^(main|patch)\.(?P<code>[^.]+)\.(?P<pkg>.+)\.obb$", re.I)
APK_RE = re.compile(r"(^|/)[^/]+\.apk$", re.I)


def log(label: str, value: object) -> None:
    print(f"[+] {label}: {value}")


def read_input(path: Path) -> tuple[bytes, str, list[tuple[str, bytes]], dict]:
    """Return base APK bytes, label, candidate OBBs, and optional XAPK metadata."""
    if path.suffix.lower() == ".apk":
        return path.read_bytes(), str(path), [], {}
    if path.suffix.lower() not in {".xapk", ".zip", ".apks"}:
        raise ValueError("input must be an APK, XAPK, APKS, or ZIP bundle")
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        meta = {}
        if "manifest.json" in names:
            try:
                meta = json.loads(zf.read("manifest.json").decode("utf-8"))
            except Exception as exc:
                raise ValueError(f"invalid manifest.json: {exc}") from exc
        apk_names = [n for n in names if APK_RE.search(n)]
        if not apk_names:
            raise ValueError("bundle contains no APK")
        # REapk's load_base_apk() chooses the base split; reproduce the same
        # policy while rejecting multiple APKs that look like split packages.
        if len(apk_names) > 1:
            split_like = [n for n in apk_names if n.lower() not in {"base.apk", "manifest.apk"}]
            if split_like:
                raise ValueError("bundle contains multiple APKs; split/configuration merging is not supported")
        base_name = next((n for n in apk_names if n.lower().endswith("base.apk")), apk_names[0])
        obbs = [(n, zf.read(n)) for n in names if n.lower().endswith(".obb")]
        return zf.read(base_name), f"{path}!{base_name}", obbs, meta


def choose_obb(candidates: list[tuple[str, bytes]], package: str, version_code: str,
               explicit: Path | None) -> tuple[str, bytes]:
    if explicit is not None:
        return explicit.name, explicit.read_bytes()
    wanted = {f"main.{version_code}.{package}.obb", f"patch.{version_code}.{package}.obb"}
    matches = [(n, b) for n, b in candidates if Path(n).name in wanted]
    if not matches:
        for n, b in candidates:
            m = OBB_RE.match(Path(n).name)
            if m and m.group("code") == version_code and m.group("pkg") == package:
                matches.append((n, b))
    if not matches:
        raise ValueError(f"no OBB named main/patch.{version_code}.{package}.obb was found")
    mains = [x for x in matches if Path(x[0]).name.startswith("main.")]
    return (mains or matches)[0]


def validate_obb(name: str, data: bytes, package: str, version_code: str) -> None:
    m = OBB_RE.match(Path(name).name)
    if not m:
        raise ValueError(f"OBB filename is not standard: {name}")
    if m.group("code") != version_code or m.group("pkg") != package:
        raise ValueError(f"OBB {name} does not match package={package}, versionCode={version_code}")
    if not data:
        raise ValueError("OBB is empty")


def package_apk(apk_bytes: bytes, obb_name: str, obb_data: bytes, output: Path) -> None:
    asset_name = f"assets/obb/{Path(obb_name).name}".encode()
    entries = []
    for entry in read_zip_entries(apk_bytes):
        name = entry["name"]
        if name == asset_name:
            continue
        if name.startswith(b"META-INF/") and name.upper().endswith((b".RSA", b".DSA", b".EC", b".SF", b".MF")):
            continue
        entries.append(entry)
    entries.append(stored_entry(asset_name.decode(), obb_data))
    unsigned = write_aligned_zip(entries)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(apk_sign_v2(unsigned))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--obb", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--no-inject", action="store_true", help="emit a packaged APK without startup extraction (not standalone)")
    args = ap.parse_args()
    try:
        raw, label, candidates, xmeta = read_input(args.input)
        apk = Apk.from_bytes(raw, label)
        info = apk.manifest.info
        package = info["package"]
        version_code = str(info["versionCode"])
        if not package or not version_code:
            raise ValueError("manifest package/versionCode is missing")
        log("Input", label)
        log("Package", package)
        log("Version code", version_code)
        log("Version name", info["versionName"] or "(none)")
        name, obb = choose_obb(candidates, package, version_code, args.obb)
        validate_obb(name, obb, package, version_code)
        log("OBB", name)
        log("OBB size", len(obb))
        if not args.no_inject:
            raise RuntimeError(
                "REapk 0.1.1 can replace existing method bodies but cannot add a declared "
                "startup hook/class or update class_data. Refusing to emit a falsely standalone APK. "
                "Use --no-inject only to test the packaging step."
            )
        output = args.output or Path("output") / f"{args.input.stem}-standalone.apk"
        log("Embedding OBB", f"assets/obb/{Path(name).name}")
        package_apk(raw, name, obb, output)
        log("Signing", "REapk native APK v2+v3")
        log("Output", output)
        print("[!] WARNING: startup extraction was not injected; this artifact is not standalone.")
        return 0
    except Exception as exc:
        print(f"[!] ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
