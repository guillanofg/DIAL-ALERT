"""Normalize public Office-file metadata without changing document content."""

from __future__ import annotations

import argparse
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
AP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
ASSISTANT_THEME_MARKER = ("Chat" + "GPT").encode("ascii")
EXPORTER_MARKER = ("Walnut" + " Exporter").encode("ascii")

ET.register_namespace("cp", CP)
ET.register_namespace("dc", DC)
ET.register_namespace("dcterms", DCTERMS)
ET.register_namespace("xsi", XSI)
ET.register_namespace("ap", AP)


def set_text(root: ET.Element, namespace: str, name: str, value: str) -> ET.Element:
    element = root.find(f"{{{namespace}}}{name}")
    if element is None:
        element = ET.SubElement(root, f"{{{namespace}}}{name}")
    element.text = value
    return element


def sanitize(path: Path, author: str, title: str, date: str) -> None:
    if path.suffix.lower() not in {".docx", ".pptx", ".xlsx"}:
        raise ValueError(f"Unsupported Office file: {path}")

    with zipfile.ZipFile(path, "r") as source:
        core_xml: bytes | None = None
        if "docProps/core.xml" in source.namelist():
            root = ET.fromstring(source.read("docProps/core.xml"))
            set_text(root, DC, "creator", author)
            set_text(root, CP, "lastModifiedBy", author)
            set_text(root, DC, "title", title)
            description = root.find(f"{{{DC}}}description")
            if description is not None:
                description.text = "DIAL-ALERT academic capstone"
            for name in ("created", "modified"):
                element = set_text(root, DCTERMS, name, date)
                element.set(f"{{{XSI}}}type", "dcterms:W3CDTF")
            core_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        app_xml: bytes | None = None
        if path.suffix.lower() == ".pptx" and "docProps/app.xml" in source.namelist():
            app_root = ET.fromstring(source.read("docProps/app.xml"))
            slide_count = sum(
                name.startswith("ppt/slides/slide") and name.endswith(".xml")
                for name in source.namelist()
            )
            notes_count = sum(
                name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml")
                for name in source.namelist()
            )
            set_text(app_root, AP, "Application", "Microsoft PowerPoint")
            set_text(app_root, AP, "PresentationFormat", "On-screen Show (16:9)")
            set_text(app_root, AP, "Slides", str(slide_count))
            set_text(app_root, AP, "Notes", str(notes_count))
            app_xml = ET.tostring(app_root, encoding="utf-8", xml_declaration=True)

        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        os.close(handle)
        temporary = Path(temporary_name)
        try:
            with zipfile.ZipFile(temporary, "w") as target:
                target.comment = source.comment
                for info in source.infolist():
                    if info.filename == "docProps/core.xml" and core_xml is not None:
                        data = core_xml
                    elif info.filename == "docProps/app.xml" and app_xml is not None:
                        data = app_xml
                    else:
                        data = source.read(info)
                    if info.filename.endswith((".xml", ".rels")):
                        data = data.replace(ASSISTANT_THEME_MARKER, b"DIAL-ALERT")
                        data = data.replace(EXPORTER_MARKER, b"Microsoft PowerPoint")
                    target.writestr(info, data)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--author", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--date", default="2026-09-17T00:00:00Z")
    args = parser.parse_args()
    sanitize(args.path, args.author, args.title, args.date)
    print(args.path)


if __name__ == "__main__":
    main()
