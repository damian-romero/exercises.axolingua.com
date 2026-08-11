#!/usr/bin/env python3
"""Find brand-color drift in a standalone Axolingua exercise file.

Exercise files redeclare the brand palette inline so they stay portable, which
means the hex values are hand-typed and quietly drift -- #2F6B5C where the token
is #2A6B5F. Invisible alone, obvious when two exercises sit side by side.

This compares every hex in the file against _sass/_tokens.scss and sorts them
into exact matches, near-misses (drift you should fix), and off-palette values
(possibly a deliberate one-off -- judge, don't blindly replace).

Usage:
    python3 check_brand_tokens.py <exercise.html> [path-to/_tokens.scss]
    python3 check_brand_tokens.py <exercise.html> --near 12

If _tokens.scss isn't given, common relative locations are tried.
"""

import os
import re
import sys

HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
TOKEN_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\s*;", re.IGNORECASE)

# Distance under which two colors are almost certainly the same intent.
# Roughly: a few points per channel. Tuned so real drift lands inside and
# genuinely different palette colors land outside.
NEAR_THRESHOLD = 14.0

# Neutrals that are legitimate in exercise files and shouldn't be reported.
ALLOWED = {
    "#FFFFFF",  # --paper, card and panel surfaces
    "#FFF",
    "#000",
    "#000000",
}

GUESSES = [
    "_sass/_tokens.scss",
    "../_sass/_tokens.scss",
    "../../_sass/_tokens.scss",
    "../../../_sass/_tokens.scss",
]


def norm(h):
    h = h.upper()
    if len(h) == 4:  # #ABC -> #AABBCC
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def rgb(h):
    h = norm(h)
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def distance(a, b):
    """Weighted RGB distance. Approximates perceptual difference well enough
    to separate 'typo' from 'different color' without pulling in a color lib."""
    r1, g1, b1 = rgb(a)
    r2, g2, b2 = rgb(b)
    rmean = (r1 + r2) / 2
    dr, dg, db = r1 - r2, g1 - g2, b1 - b2
    return (
        (2 + rmean / 256) * dr * dr
        + 4 * dg * dg
        + (2 + (255 - rmean) / 256) * db * db
    ) ** 0.5


def find_tokens_file(explicit, html_path):
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        sys.exit(f"tokens file not found: {explicit}")
    base = os.path.dirname(os.path.abspath(html_path))
    for rel in GUESSES:
        cand = os.path.normpath(os.path.join(base, rel))
        if os.path.isfile(cand):
            return cand
    sys.exit(
        "Could not locate _tokens.scss. Pass it explicitly:\n"
        "  python3 check_brand_tokens.py <exercise.html> <path/to/_tokens.scss>"
    )


def main():
    args = [a for a in sys.argv[1:]]
    threshold = NEAR_THRESHOLD
    if "--near" in args:
        i = args.index("--near")
        threshold = float(args[i + 1])
        del args[i:i + 2]

    if not args:
        sys.exit(__doc__)

    html_path = args[0]
    tokens_path = find_tokens_file(args[1] if len(args) > 1 else None, html_path)

    if not os.path.isfile(html_path):
        sys.exit(f"exercise file not found: {html_path}")

    tokens = {}  # normalized hex -> [token names]
    with open(tokens_path, encoding="utf-8") as fh:
        for name, hexval in TOKEN_RE.findall(fh.read()):
            tokens.setdefault(norm(hexval), []).append(name)

    if not tokens:
        sys.exit(f"no color tokens parsed from {tokens_path}")

    with open(html_path, encoding="utf-8") as fh:
        source = fh.read()

    # dedupe while remembering how often each appears
    counts = {}
    for m in HEX_RE.finditer(source):
        h = norm(m.group(0))
        counts[h] = counts.get(h, 0) + 1

    exact, near, off = [], [], []
    for h, n in sorted(counts.items()):
        if h in ALLOWED:
            continue
        if h in tokens:
            exact.append((h, n, tokens[h]))
            continue
        best, best_d = None, None
        for th in tokens:
            d = distance(h, th)
            if best_d is None or d < best_d:
                best, best_d = th, d
        if best_d is not None and best_d <= threshold:
            near.append((h, n, best, tokens[best], best_d))
        else:
            off.append((h, n, best, tokens[best], best_d))

    print(f"Exercise: {html_path}")
    print(f"Tokens:   {tokens_path}")
    print(f"Found {len(counts)} distinct hex values\n")

    if near:
        print("DRIFT — almost certainly meant to be a token, fix these:")
        for h, n, best, names, d in sorted(near, key=lambda x: x[4]):
            uses = f"{n} use{'s' if n > 1 else ''}"
            print(f"  {h}  ->  {best}  (--{'/--'.join(names)})   [{uses}, dist {d:.1f}]")
        print()

    if off:
        print("OFF-PALETTE — not close to any token. May be deliberate; review each:")
        for h, n, best, names, d in sorted(off, key=lambda x: x[4]):
            uses = f"{n} use{'s' if n > 1 else ''}"
            print(f"  {h}   [{uses}]  nearest: {best} (--{'/--'.join(names)}, dist {d:.1f})")
        print()

    if exact:
        print(f"OK — {len(exact)} value(s) match tokens exactly:")
        for h, n, names in exact:
            print(f"  {h}  --{'/--'.join(names)}")
        print()

    if not near and not off:
        print("No drift found. Every color in this file is an exact token value.")

    # Fonts are the other half of "is this branded" and are cheap to check here.
    missing = [f for f in ("Fraunces", "Outfit", "DM Mono")
               if f not in source and f.replace(" ", "+") not in source]
    if missing:
        print(f"FONTS — not referenced anywhere in the file: {', '.join(missing)}")
        if "fonts.googleapis.com" not in source and "_files/" not in source:
            print("        No Google Fonts <link> either — the file is falling back to "
                  "system fonts.")
    else:
        print("FONTS — Fraunces, Outfit, and DM Mono are all referenced.")

    return 1 if near else 0


if __name__ == "__main__":
    sys.exit(main())
