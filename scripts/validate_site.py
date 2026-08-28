#!/usr/bin/env python3
"""Integrity checks for the exercises.axolingua.com catalog and taxonomy.

Every failure this catches is one that Jekyll will NOT catch: a missing taxonomy
key renders as an empty string, a catalog entry pointing at a nonexistent file
renders as a broken iframe. The site builds clean either way.

Usage:
    python3 validate_site.py [path-to-site-repo]   # defaults to cwd

Exits 0 if everything checks out, 1 otherwise.
"""

import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required:  pip install pyyaml --break-system-packages")

# catalog field -> taxonomy group that must define its value
TAXONOMY_GROUPS = {
    "skill": "skills",
    "grammar": "grammar",
    "level": "levels",
    "theme": "themes",
    "target_lang": "target_langs",
}

REQUIRED_FIELDS = ["slug", "file", "skill", "grammar", "target_lang", "level", "theme"]
LANGS = ["es", "en"]


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def render(self):
        for w in self.warnings:
            print(f"  WARN   {w}")
        for e in self.errors:
            print(f"  FAIL   {e}")
        print()
        if self.errors:
            print(f"{len(self.errors)} error(s), {len(self.warnings)} warning(s).")
            return 1
        if self.warnings:
            print(f"All checks passed, with {len(self.warnings)} warning(s).")
        else:
            print("All checks passed.")
        return 0


def load_yaml(path, rep):
    if not os.path.isfile(path):
        rep.error(f"missing file: {path}")
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        rep.error(f"{os.path.basename(path)} is not valid YAML: {exc}")
        return None


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    root = os.path.abspath(root)

    catalog_path = os.path.join(root, "_data", "exercise_catalog.yml")
    taxonomy_path = os.path.join(root, "_data", "exercise_taxonomy.yml")
    exercises_dir = os.path.join(root, "exercises")

    print(f"Validating {root}\n")
    rep = Report()

    catalog = load_yaml(catalog_path, rep)
    taxonomy = load_yaml(taxonomy_path, rep)
    if catalog is None or taxonomy is None:
        return rep.render()

    if not isinstance(catalog, list):
        rep.error("exercise_catalog.yml should be a list of entries")
        return rep.render()

    if not os.path.isdir(exercises_dir):
        rep.error(f"missing directory: {exercises_dir}")
        return rep.render()

    on_disk = {f for f in os.listdir(exercises_dir) if f.endswith(".html")}
    referenced = set()
    seen_slugs = {}

    for idx, entry in enumerate(catalog):
        if not isinstance(entry, dict):
            rep.error(f"entry #{idx} is not a mapping")
            continue

        label = entry.get("slug") or entry.get("file") or f"entry #{idx}"

        for field in REQUIRED_FIELDS:
            if not entry.get(field):
                rep.error(f"{label}: missing required field '{field}'")

        slug = entry.get("slug")
        if slug:
            if slug in seen_slugs:
                rep.error(f"duplicate slug '{slug}' (also entry #{seen_slugs[slug]})")
            seen_slugs[slug] = idx

        fname = entry.get("file")
        if fname:
            if fname in referenced:
                rep.error(f"{label}: file '{fname}' is referenced by more than one entry")
            referenced.add(fname)
            if not os.path.isfile(os.path.join(exercises_dir, fname)):
                rep.error(f"{label}: file not found in exercises/: {fname}")
            if fname != fname.lower():
                rep.error(f"{label}: filename should be all lowercase: {fname}")
            try:
                fname.encode("ascii")
            except UnicodeEncodeError:
                rep.error(f"{label}: filename must be ASCII (strip accents): {fname}")

        # every classification value must have a bilingual label
        for field, group in TAXONOMY_GROUPS.items():
            value = entry.get(field)
            if not value:
                continue
            defined = taxonomy.get(group) or {}
            if value not in defined:
                rep.error(
                    f"{label}: '{value}' is not defined under '{group}' in "
                    f"exercise_taxonomy.yml (renders as a blank tag/pill)"
                )
            else:
                for lang in LANGS:
                    if not (defined[value] or {}).get(lang):
                        rep.error(f"taxonomy {group}.{value} is missing the '{lang}' label")

        for field in ("title", "description"):
            block = entry.get(field)
            if not isinstance(block, dict):
                rep.error(f"{label}: '{field}' should have 'es' and 'en' keys")
                continue
            for lang in LANGS:
                if not block.get(lang):
                    rep.error(f"{label}: missing {field}.{lang}")

        # filename should agree with the metadata it claims
        if fname and entry.get("target_lang") and entry.get("level"):
            stem = fname[:-5]
            parts = stem.split("_")
            if entry["target_lang"] not in parts:
                rep.warn(
                    f"{label}: target_lang '{entry['target_lang']}' does not appear "
                    f"in the filename '{fname}'"
                )
            if entry["level"] not in parts:
                rep.warn(
                    f"{label}: level '{entry['level']}' does not appear in the "
                    f"filename '{fname}'"
                )
            theme = entry.get("theme")
            # theme keys can themselves contain underscores (e.g. "bienes_raices"),
            # so check for the whole key as a contiguous run of parts rather than
            # requiring it to be a single element of `parts` (which would never
            # match a multi-word theme, since the filename convention also uses
            # "_" to separate segments).
            if theme and theme != "general" and theme not in parts and theme not in stem:
                rep.warn(
                    f"{label}: theme '{theme}' does not appear in the filename '{fname}'"
                )
            if theme == "general" and "general" in parts:
                rep.warn(
                    f"{label}: filename contains '_general' — the convention omits the "
                    f"theme segment for generic exercises"
                )

    for orphan in sorted(on_disk - referenced):
        rep.warn(f"exercises/{orphan} exists but has no catalog entry (won't be listed)")

    # unused taxonomy keys are harmless but produce empty filter pills
    for field, group in TAXONOMY_GROUPS.items():
        used = {e.get(field) for e in catalog if isinstance(e, dict)}
        for key in (taxonomy.get(group) or {}):
            if key not in used:
                rep.warn(f"taxonomy {group}.{key} is unused (filter pill matches nothing)")

    print(f"  Checked {len(catalog)} catalog entries against {len(on_disk)} files in exercises/")
    return rep.render()


if __name__ == "__main__":
    sys.exit(main())
