from pathlib import Path

from rapidocr_onnxruntime import RapidOCR


def main() -> None:
    image_dir = Path("tmp_deng_docx_images")
    images = sorted(image_dir.glob("*.jpeg"), key=lambda p: int(p.stem.replace("image", "")))
    print(f"images={len(images)}")

    ocr = RapidOCR()
    out_lines: list[str] = []

    for idx, image_path in enumerate(images, 1):
        print(f"OCR {idx}/{len(images)} {image_path.name}", flush=True)
        result, _ = ocr(str(image_path))
        texts = [item[1] for item in (result or [])]
        out_lines.append(f"\n\n===== {image_path.name} =====\n")
        out_lines.extend(texts)

    out_path = Path("backend/wxcloudrun/data/deng_chengzizhen_ocr_raw.txt")
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"written={out_path}")


if __name__ == "__main__":
    main()
