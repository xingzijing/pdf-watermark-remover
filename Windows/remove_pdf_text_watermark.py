#!/usr/bin/env python
"""
PDF text-watermark remover.

Run without arguments to open the GUI. The .bat file is only a launcher; all
matching and safety rules live in this Python file.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


try:
    import fitz  # PyMuPDF classic import name
except Exception as first_exc:  # pragma: no cover
    try:
        import pymupdf as fitz  # PyMuPDF newer import name
    except Exception as second_exc:  # pragma: no cover
        fitz = None
        FITZ_IMPORT_ERROR = f"{first_exc}; {second_exc}"
    else:
        FITZ_IMPORT_ERROR = None
else:
    FITZ_IMPORT_ERROR = None


@dataclass
class RemovalResult:
    input_pdf: Path
    output_pdf: Path
    page_count: int
    touched_pages: int
    matches: int


def split_input_paths(value: str) -> list[Path]:
    parts = [part.strip().strip('"') for part in re.split(r"[|]", value or "") if part.strip()]
    return [Path(part) for part in parts]


def parse_page_ranges(value: str, page_count: int) -> list[int]:
    value = (value or "all").strip().lower()
    if value in {"all", "*"}:
        return list(range(page_count))

    pages: set[int] = set()
    for raw_part in re.split(r"[,;\s]+", value):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = [x.strip() for x in part.split("-", 1)]
            start = int(start_text) if start_text else 1
            end = int(end_text) if end_text else page_count
            if start > end:
                start, end = end, start
            for page in range(start, end + 1):
                if 1 <= page <= page_count:
                    pages.add(page - 1)
        else:
            page = int(part)
            if 1 <= page <= page_count:
                pages.add(page - 1)

    if not pages:
        raise ValueError("Page range did not match any pages. Use all, 1-5, 3,8,10-12, or 10-.")
    return sorted(pages)


def default_output_path(input_pdf: Path) -> Path:
    return input_pdf.with_name(f"{input_pdf.stem}_no_watermark{input_pdf.suffix}")


def _inflate_rect(rect, padding: float):
    if padding <= 0:
        return fitz.Rect(rect)
    inflated = fitz.Rect(rect)
    inflated.x0 -= padding
    inflated.y0 -= padding
    inflated.x1 += padding
    inflated.y1 += padding
    return inflated


def _find_exact_matches(page, text: str, padding: float):
    matches = []
    for quad in page.search_for(text, quads=True):
        matches.append(_inflate_rect(quad.rect, padding))
    return matches


def _find_span_matches(page, text: str, padding: float, case_sensitive: bool):
    needle = text if case_sensitive else text.lower()
    matches = []
    page_dict = page.get_text("dict")
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            line_text = "".join(span.get("text", "") for span in line.get("spans", []))
            haystack = line_text if case_sensitive else line_text.lower()
            if needle and needle in haystack:
                for span in line.get("spans", []):
                    bbox = span.get("bbox")
                    if bbox:
                        matches.append(_inflate_rect(fitz.Rect(bbox), padding))
    return matches


def _add_delete_redaction(page, rect):
    # fill=False is supported by newer PyMuPDF and avoids drawing a white cover box.
    try:
        page.add_redact_annot(rect, fill=False)
    except TypeError:
        try:
            page.add_redact_annot(rect, fill=None)
        except TypeError:
            page.add_redact_annot(rect)


def _rect_center(rect) -> tuple[float, float]:
    return (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2


def _cluster_repeated_rects(matches_by_page: dict[int, list], min_repeats: int, tolerance: float):
    if min_repeats <= 1:
        return matches_by_page

    clusters: list[dict] = []
    for page_index, rects in matches_by_page.items():
        for rect in rects:
            cx, cy = _rect_center(rect)
            chosen = None
            for cluster in clusters:
                if abs(cluster["cx"] - cx) <= tolerance and abs(cluster["cy"] - cy) <= tolerance:
                    chosen = cluster
                    break
            if chosen is None:
                clusters.append({"cx": cx, "cy": cy, "items": [(page_index, rect)]})
            else:
                chosen["items"].append((page_index, rect))
                count = len(chosen["items"])
                chosen["cx"] += (cx - chosen["cx"]) / count
                chosen["cy"] += (cy - chosen["cy"]) / count

    kept: dict[int, list] = {page_index: [] for page_index in matches_by_page}
    for cluster in clusters:
        pages = {page_index for page_index, _ in cluster["items"]}
        if len(pages) >= min_repeats:
            for page_index, rect in cluster["items"]:
                kept[page_index].append(rect)
    return kept


def _area_rect(page_rect, area: str, custom_box: str | None):
    width = page_rect.width
    height = page_rect.height
    area = (area or "full").strip().lower()

    if area == "full":
        return fitz.Rect(page_rect)
    if area == "center":
        return fitz.Rect(page_rect.x0 + width * 0.20, page_rect.y0 + height * 0.20, page_rect.x1 - width * 0.20, page_rect.y1 - height * 0.20)
    if area == "top/header":
        return fitz.Rect(page_rect.x0, page_rect.y0, page_rect.x1, page_rect.y0 + height * 0.25)
    if area == "bottom/footer":
        return fitz.Rect(page_rect.x0, page_rect.y1 - height * 0.25, page_rect.x1, page_rect.y1)
    if area == "left":
        return fitz.Rect(page_rect.x0, page_rect.y0, page_rect.x0 + width * 0.25, page_rect.y1)
    if area == "right":
        return fitz.Rect(page_rect.x1 - width * 0.25, page_rect.y0, page_rect.x1, page_rect.y1)
    if area == "custom %":
        nums = [float(x) for x in re.split(r"[,;\s]+", custom_box or "") if x.strip()]
        if len(nums) != 4:
            raise ValueError("Custom area needs four percentages: left top right bottom, for example 20 20 80 80.")
        left, top, right, bottom = nums
        if not (0 <= left < right <= 100 and 0 <= top < bottom <= 100):
            raise ValueError("Custom area percentages must satisfy 0 <= left < right <= 100 and 0 <= top < bottom <= 100.")
        return fitz.Rect(
            page_rect.x0 + width * left / 100,
            page_rect.y0 + height * top / 100,
            page_rect.x0 + width * right / 100,
            page_rect.y0 + height * bottom / 100,
        )
    raise ValueError(f"Unknown area option: {area}")


def _filter_rects_by_area(page, rects: list, area: str, custom_box: str | None):
    allowed = _area_rect(page.rect, area, custom_box)
    kept = []
    for rect in rects:
        cx, cy = _rect_center(rect)
        if allowed.contains(fitz.Point(cx, cy)):
            kept.append(rect)
    return kept


def remove_text_watermark(
    input_pdf: str | os.PathLike[str],
    watermark_text: str,
    output_pdf: str | os.PathLike[str] | None = None,
    pages: str = "all",
    padding: float = 0.5,
    case_sensitive: bool = True,
    repeated_position_only: bool = True,
    repeat_tolerance: float = 8.0,
    limit_to_area: bool = False,
    area: str = "center",
    custom_area: str | None = None,
) -> RemovalResult:
    if fitz is None:
        raise RuntimeError(f"PyMuPDF import failed: {FITZ_IMPORT_ERROR}")

    input_path = Path(input_pdf).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_path}")
    if not watermark_text.strip():
        raise ValueError("Please enter the watermark text to remove.")

    output_path = Path(output_pdf).expanduser().resolve() if output_pdf else default_output_path(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(input_path)
    page_count = doc.page_count
    try:
        page_indexes = parse_page_ranges(pages, page_count)
        matches_by_page: dict[int, list] = {}

        for page_index in page_indexes:
            page = doc[page_index]
            rects = _find_exact_matches(page, watermark_text, padding)
            if not rects:
                rects = _find_span_matches(page, watermark_text, padding, case_sensitive)
            if not rects and not case_sensitive:
                rects = _find_span_matches(page, watermark_text, padding, case_sensitive=False)
            if limit_to_area:
                rects = _filter_rects_by_area(page, rects, area, custom_area)
            matches_by_page[page_index] = rects

        if repeated_position_only and len(page_indexes) > 1:
            matches_by_page = _cluster_repeated_rects(
                matches_by_page,
                min_repeats=min(2, len(page_indexes)),
                tolerance=repeat_tolerance,
            )

        total_matches = 0
        touched_pages = 0
        for page_index, rects in matches_by_page.items():
            if rects:
                page = doc[page_index]
                touched_pages += 1
                total_matches += len(rects)
                for rect in rects:
                    _add_delete_redaction(page, rect)
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        if total_matches == 0:
            raise ValueError("No matching watermark text was found after applying the selected filters.")

        doc.save(output_path, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()

    return RemovalResult(input_path, output_path, page_count, touched_pages, total_matches)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remove repeated text watermarks from PDFs.")
    parser.add_argument("input", nargs="?", help="Input PDF path. Use | between paths for batch mode.")
    parser.add_argument("-t", "--text", help="Watermark text to remove.")
    parser.add_argument("-o", "--output", help="Output PDF path, or output folder in batch mode.")
    parser.add_argument("-p", "--pages", default="all", help="Page range: all, 1-5, 3,8,10-12, 10-.")
    parser.add_argument("--padding", type=float, default=0.5, help="Inflate matched area by this many points.")
    parser.add_argument("--ignore-case", action="store_true", help="Use case-insensitive fallback search.")
    parser.add_argument("--allow-body-matches", action="store_true", help="Remove all text matches without same-position filtering.")
    parser.add_argument("--limit-to-area", action="store_true", help="Only remove matches inside the selected page area.")
    parser.add_argument("--area", default="center", help="Area: center, top/header, bottom/footer, left, right, custom %.")
    parser.add_argument("--custom-area", help="Custom area percentages: left top right bottom, e.g. 20 20 80 80.")
    return parser


def run_cli(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input:
        return run_gui()
    if not args.text:
        parser.error("CLI mode requires -t/--text.")

    try:
        inputs = split_input_paths(args.input)
        if not inputs:
            inputs = [Path(args.input)]
        results = []
        for input_path in inputs:
            output = args.output
            if output and len(inputs) > 1:
                output = str(Path(output) / default_output_path(input_path).name)
            results.append(
                remove_text_watermark(
                    input_path,
                    args.text,
                    output_pdf=output,
                    pages=args.pages,
                    padding=args.padding,
                    case_sensitive=not args.ignore_case,
                    repeated_position_only=not args.allow_body_matches,
                    limit_to_area=args.limit_to_area,
                    area=args.area,
                    custom_area=args.custom_area,
                )
            )
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        return 1

    for result in results:
        print(f"Done: {result.output_pdf}")
        print(f"Pages touched: {result.touched_pages}/{result.page_count}; matches removed: {result.matches}")
    return 0


def run_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:
        print(f"Cannot open GUI: {exc}", file=sys.stderr)
        return 1

    root = tk.Tk()
    root.title("PDF Text Watermark Remover")
    root.geometry("780x500")
    root.minsize(720, 460)

    input_var = tk.StringVar()
    output_var = tk.StringVar()
    text_var = tk.StringVar()
    pages_var = tk.StringVar(value="all")
    padding_var = tk.StringVar(value="0.5")
    ignore_case_var = tk.BooleanVar(value=False)
    repeated_only_var = tk.BooleanVar(value=True)
    limit_area_var = tk.BooleanVar(value=True)
    area_var = tk.StringVar(value="center")
    custom_area_var = tk.StringVar(value="20 20 80 80")
    status_var = tk.StringVar(value="Select one or more PDFs, enter watermark text, then start.")

    def choose_input():
        paths = filedialog.askopenfilenames(title="Select PDFs - multiple files allowed", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if paths:
            input_var.set("|".join(paths))
            if len(paths) == 1:
                output_var.set(str(default_output_path(Path(paths[0]))))
            else:
                output_var.set(str(Path(paths[0]).parent))

    def choose_output():
        inputs = split_input_paths(input_var.get())
        if len(inputs) > 1:
            path = filedialog.askdirectory(title="Select batch output folder")
            if path:
                output_var.set(path)
            return
        path = filedialog.asksaveasfilename(
            title="Save as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=Path(output_var.get() or "no_watermark.pdf").name,
        )
        if path:
            output_var.set(path)

    def process():
        try:
            inputs = split_input_paths(input_var.get())
            if not inputs:
                raise ValueError("Please select at least one PDF.")
            results = []
            for input_path in inputs:
                output = output_var.get() or None
                if output and len(inputs) > 1:
                    output = str(Path(output) / default_output_path(input_path).name)
                results.append(
                    remove_text_watermark(
                        input_path,
                        text_var.get(),
                        output_pdf=output,
                        pages=pages_var.get() or "all",
                        padding=float(padding_var.get() or "0.5"),
                        case_sensitive=not ignore_case_var.get(),
                        repeated_position_only=repeated_only_var.get(),
                        limit_to_area=limit_area_var.get(),
                        area=area_var.get(),
                        custom_area=custom_area_var.get(),
                    )
                )
        except Exception as exc:
            messagebox.showerror("Failed", str(exc))
            status_var.set("Failed. Check text, page range, area filters, or PDF type.")
            return

        total_matches = sum(result.matches for result in results)
        status_var.set(f"Done. Files: {len(results)}; matches removed: {total_matches}.")
        saved = "\n".join(str(result.output_pdf) for result in results[:8])
        if len(results) > 8:
            saved += f"\n... plus {len(results) - 8} more files"
        messagebox.showinfo("Done", f"Saved:\n{saved}")

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="Input PDFs").grid(row=0, column=0, sticky="w", pady=5)
    ttk.Entry(frame, textvariable=input_var).grid(row=0, column=1, sticky="ew", padx=8)
    ttk.Button(frame, text="Select", command=choose_input).grid(row=0, column=2)

    ttk.Label(frame, text="Output").grid(row=1, column=0, sticky="w", pady=5)
    ttk.Entry(frame, textvariable=output_var).grid(row=1, column=1, sticky="ew", padx=8)
    ttk.Button(frame, text="Browse", command=choose_output).grid(row=1, column=2)

    ttk.Label(frame, text="Watermark text").grid(row=2, column=0, sticky="w", pady=5)
    ttk.Entry(frame, textvariable=text_var).grid(row=2, column=1, columnspan=2, sticky="ew", padx=8)

    ttk.Label(frame, text="Pages").grid(row=3, column=0, sticky="w", pady=5)
    ttk.Entry(frame, textvariable=pages_var).grid(row=3, column=1, sticky="ew", padx=8)
    ttk.Label(frame, text="all / 1-5 / 3,8 / 10-").grid(row=3, column=2, sticky="w")

    ttk.Label(frame, text="Padding").grid(row=4, column=0, sticky="w", pady=5)
    ttk.Entry(frame, textvariable=padding_var, width=10).grid(row=4, column=1, sticky="w", padx=8)

    ttk.Checkbutton(frame, text="Ignore case fallback search", variable=ignore_case_var).grid(row=5, column=1, columnspan=2, sticky="w", padx=8, pady=4)
    ttk.Checkbutton(frame, text="Only remove text repeated at the same position across pages", variable=repeated_only_var).grid(row=6, column=1, columnspan=2, sticky="w", padx=8, pady=4)

    ttk.Checkbutton(frame, text="Only remove text inside selected page area", variable=limit_area_var).grid(row=7, column=1, columnspan=2, sticky="w", padx=8, pady=4)
    area_frame = ttk.Frame(frame)
    area_frame.grid(row=8, column=1, columnspan=2, sticky="ew", padx=8, pady=4)
    ttk.Label(area_frame, text="Area").grid(row=0, column=0, sticky="w")
    ttk.Combobox(
        area_frame,
        textvariable=area_var,
        values=["center", "top/header", "bottom/footer", "left", "right", "custom %"],
        width=18,
        state="readonly",
    ).grid(row=0, column=1, sticky="w", padx=8)
    ttk.Label(area_frame, text="Custom %").grid(row=0, column=2, sticky="w", padx=(16, 0))
    ttk.Entry(area_frame, textvariable=custom_area_var, width=18).grid(row=0, column=3, sticky="w", padx=8)

    ttk.Button(frame, text="Remove Watermark", command=process).grid(row=9, column=1, sticky="e", padx=8, pady=16)
    ttk.Label(frame, text="Default safety: same-position filter ON and area filter ON. Use center for diagonal page-center watermarks.", foreground="#555").grid(row=10, column=0, columnspan=3, sticky="ew")
    ttk.Label(frame, textvariable=status_var, foreground="#444").grid(row=11, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
