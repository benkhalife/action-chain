import fitz  # PyMuPDF
import os
import re
from bidi.algorithm import get_display
import arabic_reshaper

# -------- Settings --------
IMAGE_FORMAT = "jpg"  # "jpg" (safe) or "png"
OUTPUT_DIR = "output"
INPUT_FILE = "input.txt"
INDEX_FILE = "bookpages.txt"
# --------------------------

def normalize_persian_text(text: str) -> str:
    """Normalize Persian text for better readability."""
    if not text or not text.strip():
        return ""
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"\s+", " ", text).strip()
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
        return text

def ensure_rgb_pixmap(pix: fitz.Pixmap) -> fitz.Pixmap:
    """Ensure the pixmap is RGB without alpha channel."""
    is_gray = pix.colorspace and pix.colorspace.n == 1
    is_rgb = pix.colorspace and pix.colorspace.n == 3
    if (is_gray or is_rgb) and not pix.alpha:
        return pix
    return fitz.Pixmap(fitz.csRGB, pix)

def save_image_pixmap(pix: fitz.Pixmap, out_path: str, img_format: str = "jpg") -> str:
    """Save pixmap robustly as JPG or PNG."""
    img_format = img_format.lower()
    if img_format not in ("jpg", "jpeg", "png"):
        img_format = "jpg"

    rgb_pix = ensure_rgb_pixmap(pix)
    base, _ = os.path.splitext(out_path)

    if img_format in ("jpg", "jpeg"):
        out_file = f"{base}.jpg"
        data = rgb_pix.tobytes("jpeg")
        with open(out_file, "wb") as f:
            f.write(data)
    else:
        out_file = f"{base}.png"
        rgb_pix.save(out_file)

    if rgb_pix is not pix:
        rgb_pix = None

    return os.path.basename(out_file)

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ '{INPUT_FILE}' not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        pdf_filename = f.read().strip()

    if not pdf_filename or not os.path.exists(pdf_filename):
        print(f"❌ File '{pdf_filename}' not found.")
        return

    pdf_name = os.path.splitext(os.path.basename(pdf_filename))[0]
    book_output_dir = os.path.join(OUTPUT_DIR, pdf_name)
    os.makedirs(book_output_dir, exist_ok=True)

    try:
        doc = fitz.open(pdf_filename)
    except Exception as e:
        print(f"❌ Failed to open PDF: {e}")
        return

    index_lines = []
    print(f"➡️ Processing PDF: {pdf_filename} ({len(doc)} pages)")

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_index = page_num + 1

        # --- Extract text ---
        text = page.get_text("text")
        text = normalize_persian_text(text)
        text_filename = os.path.join(book_output_dir, f"{page_index}.txt")
        with open(text_filename, "w", encoding="utf-8") as f:
            f.write(text or "")

        # --- Extract images ---
        image_files = []
        # images = page.get_images(full=True)
        # for img_index, img in enumerate(images, start=1):
        #     try:
        #         xref = img[0]
        #         pix = fitz.Pixmap(doc, xref)
        #         out_stub = os.path.join(book_output_dir, f"{page_index}_{img_index}")
        #         saved_name = save_image_pixmap(pix, out_stub, IMAGE_FORMAT)
        #         image_files.append(saved_name)
        #         pix = None
        #     except Exception as e:
        #         print(f"⚠️ Page {page_index}, image {img_index}: {e}")

        files_list = [os.path.basename(text_filename)] + image_files
        index_lines.append(" ".join(files_list))

    # --- Write index file in same folder ---
    index_path = os.path.join(book_output_dir, INDEX_FILE)
    with open(index_path, "w", encoding="utf-8") as f:
        for line in index_lines:
            f.write(line + "\n")

    print(f"✅ Done. Files saved in '{book_output_dir}'. Index written to '{index_path}'.")

if __name__ == "__main__":
    main()
