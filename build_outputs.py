#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_outputs.py — one-command export pipeline for KiCad 9 projects
===================================================================

Overview
--------
This script standardizes all the “project outputs” you usually need from a KiCad 9
project—3D models, pretty renders, documentation PDFs, and fabrication files—into a
fixed folder structure at the repository root. It works on Windows (tested) and also
macOS/Linux if `kicad-cli` is on PATH.

What it produces
----------------
- 3D models → 3D_MODEL/<project>.step  [optionally: <project>.glb with --glb]
- Renders   → PICTURES/<project>_{top|bottom|side}[,_iso].png  (transparent background)
- Docs      → DOCUMENTATION/<project>_schematic.pdf,
              DOCUMENTATION/<project>_erc.rpt,
              DOCUMENTATION/<project>_board_prints.pdf (multi-page selected layers)
- Fab       → PRODUCTION/<timestamp>_<project>/{gerbers,drill,...} plus:
              - <project>_pos.csv (placement/PNP)
              - <project>_bom.csv (grouped BOM)
              - optional ZIP of gerbers with --zip
- README    → If README.md is missing, generate it from README.template.md (if present)
              or from a built-in template. Images use *_iso.png when available.

Folder expectations (repo root)
-------------------------------
3D_MODEL/
CAD/
CODE/
DOCUMENTATION/
PICTURES/
PRODUCTION/

Your KiCad project files typically live under CAD/<something>/<project>.kicad_{pro,sch,pcb}.
You pass the `.kicad_pro` (or stem) to --project.

Requirements
------------
- KiCad 9 with `kicad-cli` available.
  *Windows default path tried:* C:\\Program Files\\KiCad\\9.0\\bin\\kicad-cli.exe
- (Optional) KiKit on PATH if you want vendor ZIPs via `--kikit jlcpcb`, etc.

Key behavior and notes
----------------------
- STEP export is **fail-soft**: if KiCad returns exit code 2 due to missing 3D models,
  the script still continues as long as the STEP file is produced (uses --subst-models).
- ERC/DRC reports are saved under DOCUMENTATION/ for easy review; DRC is optional
  (use --skip-drc to omit it).
- Board prints PDF is multi-page across common layers; tweak the layer list in code.
- README generation happens **only if README.md does not exist**. It auto-picks
  <project>_iso.png as header if present, otherwise <project>_top.png.
- The production run goes to a timestamped folder, e.g. PRODUCTION/20250115_1342_<project>/

Usage (PowerShell / CMD on Windows)
-----------------------------------
# From repo root — basic run
python .\\build_outputs.py --project .\\CAD\\esp-motioncontroller\\esp-motioncontroller.kicad_pro

# Add a nice isometric render and zip the gerbers
python .\\build_outputs.py --project .\\CAD\\esp-motioncontroller\\esp-motioncontroller.kicad_pro --iso --zip

# Create a vendor-ready ZIP with KiKit (example: JLCPCB)
python .\\build_outputs.py --project .\\CAD\\esp-motioncontroller\\esp-motioncontroller.kicad_pro --kikit jlcpcb

# Use a different production folder (e.g., your CAD-specific production dir)
python .\\build_outputs.py --project .\\CAD\\esp-motioncontroller\\esp-motioncontroller.kicad_pro --prod-dir CAD\\esp-motioncontroller\\production

Usage (Bash / macOS / Linux)
----------------------------
python3 ./build_outputs.py --project ./CAD/esp-motioncontroller/esp-motioncontroller.kicad_pro --iso --zip

Command-line options
--------------------
--project   Path to the .kicad_pro (or the stem) of the project (required)
--root      Repo root containing 3D_MODEL, PICTURES, DOCUMENTATION, PRODUCTION (default: ".")
--prod-dir  Production folder (relative to --root). Default: PRODUCTION
--iso       Also render an isometric PNG
--glb       Also export a GLB 3D model
--zip       Create a ZIP of the gerbers
--kikit     Run 'kikit fab <vendor>' into the production run folder (e.g., 'jlcpcb')
--skip-drc  Skip generating the DRC report

Troubleshooting
---------------
- "Could not add 3D model ..." / exit code 2:
  The script already accepts {0,2} on STEP export and continues. Check KiCad's
  Preferences → Configure Paths (e.g., KICAD9_3DMODEL_DIR) or add models to packages3D.
- README template encoding errors:
  The script tries UTF-8/UTF-8-SIG/UTF-16/CP1252. If needed, re-save the template
  as UTF-8. See read_text_flexible() for details.
- Renders look odd:
  Adjust the camera in export_pictures() (e.g., change --side or the --rotate for ISO).
- Board prints content:
  Edit the 'layers' list in export_docs() to suit your documentation style.

"""

import argparse
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime
import zipfile
from string import Template
from pathlib import Path
import shutil
import re

def clear_dir(path: Path):
    """
    Remove all contents of `path` but keep the directory itself.
    Guardrails: refuses to clear drives or very shallow paths accidentally.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    # Guardrails: require at least 2 levels deep (e.g., PRODUCTION/<project>)
    parts = path.resolve().parts
    if len(parts) < 3:
        raise RuntimeError(f"Refusing to clear very shallow path: {path}")

    for entry in path.iterdir():
        try:
            if entry.is_file() or entry.is_symlink():
                entry.unlink(missing_ok=True)
            else:
                shutil.rmtree(entry)
        except Exception as e:
            print(f"Warning: couldn't remove {entry}: {e}")

DEFAULT_README_TEMPLATE = """# ${PROJECT_NAME}

![HEADER](./PICTURES/${HEADER_IMAGE}) <!-- 3D rendered pretty view -->

INFO INFO

[PCB layout](./DOCUMENTATION/${PCBLAYOUT_PDF}) <!-- PDFs of boards -->
[SCHEMATIC](./DOCUMENTATION/${SCHEMATIC_PDF}) <!-- Schematic PDFs -->

## FRONT
![Front](./PICTURES/${PICTURE_FRONT})

## BACK
![Back](./PICTURES/${PICTURE_BACK})

## SIDE
![Side](./PICTURES/${PICTURE_SIDE})

# Before major commmits
Remember to run generate_outputs.bat/sh
to update the outputs and pictures.
"""

def read_text_flexible(path: Path) -> str:
    """
    Read text trying common encodings. Prints which one worked.
    Avoids 'utf-8' codec errors when files are saved as UTF-16/Windows-1252.
    """
    data = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252"):
        try:
            s = data.decode(enc)
            print(f"Loaded {path.name} using {enc}")
            return s
        except UnicodeDecodeError:
            continue
    # Last resort: replace undecodable chars
    print(f"Loaded {path.name} using utf-8 with replacement chars")
    return data.decode("utf-8", errors="replace")

def render_readme_if_missing(root: Path, project_name: str) -> Path:
    """
    Create README.md only if it doesn't already exist.
    Uses README.template.md if present, otherwise a built-in default.
    Chooses header/extra images based on whether <proj>_iso.png exists.
    """
    out_path = root / "README.md"
    if out_path.exists():
        print("README.md already exists — leaving it untouched.")
        return out_path
    else:
        print("Generating README.md")

    tpl_path = root / "README.template.md"
    if tpl_path.exists():
        tpl_text = read_text_flexible(tpl_path)   # <-- changed line
    else:
        tpl_text = DEFAULT_README_TEMPLATE

    pics_dir = root / "PICTURES"
    iso_name = f"{project_name}_iso.png"
    top_name = f"{project_name}_top.png"
    bottom_name = f"{project_name}_bottom.png"
    side_name = f"{project_name}_side.png"

    header_image = iso_name if (pics_dir / iso_name).exists() else top_name

    subs = {
        "PROJECT_NAME": project_name,
        "HEADER_IMAGE": header_image,
        "PCBLAYOUT_PDF": f"{project_name}_board_prints.pdf",
        "SCHEMATIC_PDF": f"{project_name}_schematic.pdf",
        "PICTURE_FRONT": top_name,
        "PICTURE_BACK": bottom_name,
        "PICTURE_SIDE": side_name,
        "EXTRA_IMAGE": header_image,
    }

    rendered = Template(tpl_text).safe_substitute(subs)
    out_path.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Wrote {out_path}")
    return out_path

# ---------- Helpers ----------

def which_kicad_cli():
    # Prefer environment override
    env = Path(str(Path.cwd()))
    exe = shutil.which("kicad-cli")
    if exe:
        return exe
    # Windows default install path for KiCad 9
    win_default = Path(r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe")
    if win_default.exists():
        return str(win_default)
    raise FileNotFoundError(
        "kicad-cli not found on PATH and not at default KiCad 9 location.\n"
        "Add KiCad to PATH or set KICAD_CLI env var / adjust this script."
    )

def find_kicad_python_from_kicad_cli(kicad_cli_path: str) -> str:
    """
    Locate KiCad's Python next to kicad-cli so we can run 'python -m kikit'.
    Works on Windows/macOS/Linux. Falls back to system Python if needed.
    """
    kcli = Path(kicad_cli_path)
    # Windows: ...\KiCad\9.0\bin\python.exe
    cand = kcli.with_name("python.exe")
    if cand.exists():
        return str(cand)
    # macOS/Linux: .../bin/python
    cand2 = kcli.with_name("python")
    if cand2.exists():
        return str(cand2)
    # Fallback to system python
    py = shutil.which("python") or shutil.which("python3")
    if py:
        return py
    raise FileNotFoundError("Could not locate a Python interpreter to run KiKit.")

def run(cmd, cwd=None, ok_codes={0}):
    print(">>", " ".join(map(str, cmd)))
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode not in ok_codes:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed with code {res.returncode}")
    return res

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    return p

def timestamp_tag():
    return datetime.now().strftime("%Y%m%d_%H%M")

def project_paths(project_file: Path):
    """
    Accepts a .kicad_pro, base name, or path stem.
    Returns (proj_stem, sch_path, pcb_path).
    """
    if project_file.suffix.lower() == ".kicad_pro":
        stem = project_file.with_suffix("")  # same base name
        sch = stem.with_suffix(".kicad_sch")
        pcb = stem.with_suffix(".kicad_pcb")
    else:
        # if user passed without extension, try both
        stem = project_file
        sch = stem.with_suffix(".kicad_sch")
        pcb = stem.with_suffix(".kicad_pcb")
    if not sch.exists():
        raise FileNotFoundError(f"Schematic not found: {sch}")
    if not pcb.exists():
        raise FileNotFoundError(f"Board not found: {pcb}")
    return stem.name, sch, pcb

def zip_dir(src_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in src_dir.rglob("*"):
            zf.write(p, arcname=p.relative_to(src_dir))

# ---------- Export steps ----------

def export_3d(kicad, pcb_path: Path, out_dir: Path, make_glb: bool):
    ensure_dir(out_dir)
    step_out = out_dir / f"{pcb_path.stem}.step"
    # --subst-models reduces 3D issues; accept {0,2} and verify file
    run([kicad, "pcb", "export", "step", "--subst-models", "-o", str(step_out), str(pcb_path)],
        ok_codes={0, 2})
    if not step_out.exists():
        raise RuntimeError("STEP export did not produce a file.")
    if make_glb:
        glb_out = out_dir / f"{pcb_path.stem}.glb"
        run([kicad, "pcb", "export", "glb", "--subst-models", "-o", str(glb_out), str(pcb_path)],
            ok_codes={0, 2})
    return step_out

def export_pictures(kicad, pcb_path: Path, out_dir: Path, iso: bool):
    ensure_dir(out_dir)
    top = out_dir / f"{pcb_path.stem}_top.png"
    bot = out_dir / f"{pcb_path.stem}_bottom.png"
    side = out_dir / f"{pcb_path.stem}_side.png"

    run([kicad, "pcb", "render", "-o", str(top), "--side", "top", "--background", "transparent", str(pcb_path)])
    run([kicad, "pcb", "render", "-o", str(bot), "--side", "bottom", "--background", "transparent", str(pcb_path)])
    # "side" = orthographic left view; change to 'right/front/back' if preferred
    run([kicad, "pcb", "render", "-o", str(side), "--side", "left", "--background", "transparent", str(pcb_path)])

    iso_out = None
    if iso:
        iso_out = out_dir / f"{pcb_path.stem}_iso.png"
        run([
            kicad, "pcb", "render", "-o", str(iso_out),
            "--background", "transparent", "--perspective",
            "--rotate", "'-45,0,45'", "--zoom", "1", str(pcb_path)
        ])
    return [top, bot, side] + ([iso_out] if iso_out else [])

def export_docs(kicad, sch_path: Path, pcb_path: Path, out_dir: Path, include_drc: bool):
    ensure_dir(out_dir)
    # Schematic PDF
    sch_pdf = out_dir / f"{sch_path.stem}_schematic.pdf"
    run([kicad, "sch", "export", "pdf", "-o", str(sch_pdf), str(sch_path)])

    # ERC report
    erc_rpt = out_dir / f"{sch_path.stem}_erc.rpt"
    run([kicad, "sch", "erc", "-o", str(erc_rpt), str(sch_path)])

    # Board prints PDF (multi-page: common layers)
    board_pdf = out_dir / f"{pcb_path.stem}_board_prints.pdf"
    layers = ",".join([
        "F.Cu","B.Cu","F.SilkS","B.SilkS",
        "F.Mask","B.Mask","Edge.Cuts","F.Fab","B.Fab","User.Drawings"
    ])
    run([
        kicad, "pcb", "export", "pdf",
        "-o", str(board_pdf),
        "--layers", layers,
        "--mode-multipage",
        str(pcb_path)
    ])

    # Optional DRC (report lives with docs so it’s easy to review)
    drc_rpt = None
    if include_drc:
        drc_rpt = out_dir / f"{pcb_path.stem}_drc.rpt"
        run([kicad, "pcb", "drc", "-o", str(drc_rpt), "--format", "report", str(pcb_path)])

    return sch_pdf, erc_rpt, board_pdf, drc_rpt

def export_fab(kicad, sch_path: Path, pcb_path: Path, out_dir: Path, zip_outputs: bool):
    """
    Fabrication outputs into `out_dir`, which is assumed to be clean if --no-timestamp was used.
    - Gerbers → out_dir/gerbers
    - Drill   → out_dir/drill
    - POS/PNP → out_dir/<project>_pos.csv
    - BOM     → out_dir/<project>_bom.csv
    - ZIP     → out_dir/<project>_gerbers.zip (overwrites each run when requested)
    """
    root = ensure_dir(out_dir)
    gerb_dir = ensure_dir(root / "gerbers")
    drill_dir = ensure_dir(root / "drill")

    # Gerbers: use saved board plot params for repeatability
    run([kicad, "pcb", "export", "gerbers", "-o", str(gerb_dir), "--board-plot-params", str(pcb_path)])

    # Drill (Excellon) + map
    run([kicad, "pcb", "export", "drill", "-o", str(drill_dir), "--format", "excellon", "--generate-map", str(pcb_path)])

    # POS/PNP (CSV, both sides, mm)
    pos_csv = root / f"{pcb_path.stem}_pos.csv"
    run([kicad, "pcb", "export", "pos", "-o", str(pos_csv), "--format", "csv", "--units", "mm", "--side", "both", str(pcb_path)])

    # BOM (CSV) – include common fields if present
    bom_csv = root / f"{sch_path.stem}_bom.csv"
    fields = "Reference,Value,Footprint,${QUANTITY},Manufacturer,MPN,Datasheet,${DNP}"
    labels = "Refs,Value,Footprint,Qty,Manufacturer,MPN,Datasheet,DNP"
    run([
        kicad, "sch", "export", "bom", "-o", str(bom_csv),
        "--fields", fields, "--labels", labels, "--group-by", "Value,Footprint,MPN",
        str(sch_path)
    ])

    zip_path = None
    if zip_outputs:
        # Stable zip name that overwrites each run
        zip_path = root / f"{pcb_path.stem}_gerbers.zip"
        # If it exists from a prior run, remove first to avoid stale entries
        try:
            if zip_path.exists():
                zip_path.unlink()
        except Exception:
            pass
        zip_dir(gerb_dir, zip_path)

    return gerb_dir, drill_dir, pos_csv, bom_csv, zip_path


def _sanitize_vendor(v: str) -> str:
    # lower, replace spaces/odd chars with '-', keep alnum/._-
    return re.sub(r'[^A-Za-z0-9_.-]+', '-', v.strip().lower())

def run_kikit_fab(vendor: str, pcb_path: Path, sch_path: Path, out_dir: Path,
                  order_field: str = None, clean: bool = True):
    """
    Use KiKit to make a vendor-ready ZIP in a subfolder: <out_dir>/<vendor>_production
    Returns the path to the ZIP (typically 'gerbers.zip').

    Example:
      run_kikit_fab("jlcpcb", Path("board.kicad_pcb"), Path("board.kicad_sch"), "MPN", Path("PRODUCTION"))
      -> PRODUCTION/jlcpcb_production/gerbers.zip
    """
    if order_field == None:
        if vendor.lower() == "jlcpcb":
            order_field = "LCSC"
        else:
            order_field = "MPN"

    python = shutil.which("python")

    if not python:
        raise FileNotFoundError("Python interpreter not found on PATH.")
    vendor_root = ensure_dir(out_dir / f"{vendor.lower()}_production")

    if clean:
        for e in vendor_root.iterdir():
            (e.unlink if e.is_file() or e.is_symlink() else shutil.rmtree)(e)

    cmd = [python, "-m", "kikit.ui", "fab", vendor,
           "--assembly", "--schematic", str(sch_path)]
    
    if order_field:
        cmd += ["--field", order_field]
    cmd += [str(pcb_path), str(vendor_root)]

    run(cmd)
    return vendor_root / "gerbers.zip"
# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description="Standardize KiCad 9 outputs into your folder structure.")
    parser.add_argument("--project", required=True, help="Path to .kicad_pro (or base path) of the project.")
    parser.add_argument("--root", default=".", help="Repo root containing 3D_MODEL, PICTURES, DOCUMENTATION, PRODUCTION.")
    parser.add_argument("--prod-dir", default="PRODUCTION", help="Production folder relative to root (default: PRODUCTION).")
    parser.add_argument("--iso", action="store_true", help="Also render an isometric image.")
    parser.add_argument("--glb", action="store_true", help="Also export .glb 3D model.")
    parser.add_argument("--zip", action="store_true", help="Zip gerbers into <proj>_gerbers_<timestamp>.zip.")
    parser.add_argument("--kikit", default=None, help="Optional: vendor for KiKit 'fab' (e.g., 'jlcpcb').")
    parser.add_argument("--skip-drc", action="store_true", help="Skip DRC report.")
    parser.add_argument("--no-timestamp",action="store_true",
                        help="Write to PRODUCTION/<project> (cleared each run) instead of timestamped folders."
    )
    args = parser.parse_args()

    kicad = which_kicad_cli()
    proj_stem, sch_path, pcb_path = project_paths(Path(args.project))

    root = Path(args.root).resolve()
    three_d_dir = ensure_dir(root / "3D_MODEL")
    pics_dir = ensure_dir(root / "PICTURES")
    docs_dir = ensure_dir(root / "DOCUMENTATION")

    # Production output location
    if args.no_timestamp:
        # Stable path per project; clear it on each run
        prod_root = ensure_dir(root / args.prod_dir / proj_stem)
        clear_dir(prod_root)  # destructive inside this folder (by design)
    else:
        # Keep old behavior: timestamped per run
        prod_root = ensure_dir(root / args.prod_dir / f"{timestamp_tag()}_{proj_stem}")

    print(f"Project: {proj_stem}")
    print(f"SCH:     {sch_path}")
    print(f"PCB:     {pcb_path}")
    print(f"Root:    {root}")

    # 1) 3D model(s)
    export_3d(kicad, pcb_path, three_d_dir, args.glb)

    # 2) Renders
    export_pictures(kicad, pcb_path, pics_dir, args.iso)

    # 3) Documentation (schematic PDF, ERC, board prints PDF [+ optional DRC])
    export_docs(kicad, sch_path, pcb_path, docs_dir, include_drc=not args.skip_drc)

    # 4) Fabrication (Gerbers, drill, PNP, BOM [+ ZIP])
    export_fab(kicad, sch_path, pcb_path, prod_root, zip_outputs=args.zip)

    # 5) Optional vendor-specific fab package via KiKit (e.g., jlcpcb)
    if args.kikit:
        print(f"Running KiKit fab for vendor: {args.kikit}")
        vendor_zip = run_kikit_fab(args.kikit, pcb_path, sch_path, prod_root)
        print(f"KiKit vendor ZIP: {vendor_zip}")

    render_readme_if_missing(root, proj_stem)
    

    print("\nAll done ✅")
    print(f"- 3D models:       {three_d_dir}")
    print(f"- Pictures:        {pics_dir}")
    print(f"- Documentation:   {docs_dir}")
    print(f"- Production run:  {prod_root}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
