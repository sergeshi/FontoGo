"""Command-line import/export entry point: python -m fontogo_core.cli."""
import argparse
from pathlib import Path
from .font_io import import_font, export_ttf

def main():
    parser=argparse.ArgumentParser(description="Import TTF/OTF into a FontoGo JSON project or compile a project to TTF.")
    parser.add_argument("input", help="Input .ttf, .otf, or .json file")
    parser.add_argument("output", help="Output .json or .ttf file")
    args=parser.parse_args()
    src,dst=Path(args.input),Path(args.output)
    if src.suffix.lower()==".json":
        import json
        from .model import Document
        doc=Document.from_dict(json.loads(src.read_text(encoding="utf-8")))
    else:
        doc=import_font(src)
    if dst.suffix.lower()==".json":
        dst.write_text(doc.to_json()+"\n",encoding="utf-8")
    elif dst.suffix.lower()==".ttf":
        export_ttf(doc,dst)
    else:
        parser.error("Output extension must be .json or .ttf (CFF OTF export is not implemented yet)")
    print(f"{src} -> {dst}: {len(doc.glyphs)} glyphs, {len(doc.cmap)} Unicode mappings")

if __name__=="__main__": main()
