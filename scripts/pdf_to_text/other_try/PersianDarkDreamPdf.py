#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_persian_pdf.py
----------------------
استخراج متن فارسیِ خوانا و نرمال‌شده از PDF با دو راهبرد:
1) pdfminer.six (متن منطقی)
2) فروکاست خودکار به OCR با Tesseract (fas+eng) اگر متن بی‌معنا/غیرقابل‌خواندن بود.

کارکردهای کلیدی نرمال‌سازی:
- یکسان‌سازی ی/ک فارسی، اعداد، فاصله‌ها، نیم‌فاصله‌های رایج، علائم نگارشی فارسی،
  حذف کشیده/اعراب/کاراکترهای صفرعرض، رفع هایفن‌خوردگی انتهای سطر، تعمیر BiDi در صورت نیاز.

کاربرد:
    python extract_persian_pdf.py input.pdf -o output.txt --digits persian --keep-diacritics false --no-ocr false

گزینه‌ها را با `-h` ببینید.
"""

from __future__ import annotations
import argparse
import io
import os
import sys
import re
import unicodedata
from typing import List, Tuple

# pdfminer.six
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:
    pdfminer_extract_text = None

# OCR fallback: PyMuPDF + pytesseract
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# BiDi & Arabic reshaping (برای مواقع خاصی که خروجی بصری/وارونه استخراج شده)
try:
    from bidi.algorithm import get_display
except Exception:
    get_display = None

try:
    import arabic_reshaper
except Exception:
    arabic_reshaper = None

import regex as reg  # بهتر از re برای محدوده‌های یونیکد

# ---------- تنظیمات پیش‌فرض ----------
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
LATIN_DIGITS   = "0123456789"

# محدوده‌ی حروف عربی/فارسی برای سنجش خوانایی
RE_ARABIC_LETTERS = reg.compile(r'\p{Arabic}')
# Private Use Areas (اغلب نشانه متن ناسازگار)
RE_PRIVATE_USE = reg.compile(r'[\uE000-\uF8FF]')

# علائم نگارشی و فاصله‌گذاری
PERSIAN_PUNCT_FIXES = [
    (r'\s+([،؛؟!:\.\)\]\}])', r'\1'),  # حذف فاصله قبل از علائم پایانی/بسته
    (r'([\(«\[\{])\s+', r'\1'),        # حذف فاصله بعد از علائم باز
    (r'([،؛؟!:\.])(?=\S)', r'\1 '),    # افزودن فاصله بعد از علائم در صورت نبود
    # یکسان‌سازی و تبدیل علائم انگلیسی در متن فارسی (اختیاری: اینجا موارد رایج)
]

# پسوندها/پیشوندهای رایج برای نیم‌فاصله
PERSIAN_SUFFIXES = ('ها', 'های', 'هایی', 'تر', 'ترین', 'ام', 'ات', 'اش', 'ایم', 'اید', 'اند', 'مان', 'تان', 'شان')
PERSIAN_PREFIXES = ('می', 'نمی')  # الگوهای رایج

def replace_digits(s: str, mode: str = "persian") -> str:
    """تبدیل اعداد به فارسی/لاتین/حفظ."""
    if mode == "persian":
        trans = str.maketrans(LATIN_DIGITS + ARABIC_DIGITS, PERSIAN_DIGITS + PERSIAN_DIGITS)
        return s.translate(trans)
    elif mode == "latin":
        trans = str.maketrans(PERSIAN_DIGITS + ARABIC_DIGITS, LATIN_DIGITS + LATIN_DIGITS)
        return s.translate(trans)
    elif mode == "keep":
        return s
    else:
        return s

def remove_diacritics(s: str) -> str:
    """حذف اعراب/نشانه‌های ترکیبی عربی؛ حفظ حروف پایه."""
    # محدوده‌های اعراب رایج عربی/فارسی
    return ''.join(ch for ch in s if not (
        '\u0610' <= ch <= '\u061A' or
        '\u064B' <= ch <= '\u065F' or
        '\u06D6' <= ch <= '\u06ED'
    ))

def normalize_arabic_persian_letters(s: str) -> str:
    """یکسان‌سازی ی/ک و حذف کشیده/کاراکترهای ارائه‌ی سازگارسازی‌شده."""
    s = unicodedata.normalize('NFC', s)
    # ی و ک عربی → فارسی
    s = s.replace('\u064A', '\u06CC')  # ي → ی
    s = s.replace('\u0643', '\u06A9')  # ك → ک
    # حذف کشیده (tatweel)
    s = s.replace('\u0640', '')
    # حذف کاراکترهای صفرعرض (بجز ZWNJ که ممکن است بخواهیم نگه داریم)
    s = s.replace('\u200B', '')  # ZWSP
    s = s.replace('\u200C\u200C', '\u200C')  # دوبل نیم‌فاصله
    s = s.replace('\uFEFF', '')  # BOM/ZWNBSP
    s = s.replace('\u00A0', ' ')  # NBSP → space
    return s

def fix_half_space(s: str) -> str:
    """افزودن نیم‌فاصله در الگوهای رایج فارسی (ساده و مبتنی بر قاعده)."""
    # پیشوندهای می/نمی
    # 'می ' + کلمه → 'می‌کلمه'  /  'نمی ' + کلمه → 'نمی‌کلمه'
    s = reg.sub(r'\b(می|نمی)\s+([^\s\d\W][\w\u0600-\u06FF]+)', r'\1\u200C\2', s)

    # پسوندهای رایج: «کلمه ها/تر/ترین/…» → «کلمه‌ها/تر/ترین/…»
    # توجه: الگوی ساده؛ برای همه استثناها کامل نیست اما در عمل کمک می‌کند.
    suf_pattern = r'([^\s\d\W\u200c][\w\u0600-\u06FF]+)\s+(' + '|'.join(PERSIAN_SUFFIXES) + r')\b'
    s = reg.sub(suf_pattern, r'\1\u200C\2', s, flags=reg.IGNORECASE)

    return s

def fix_punct_spaces(s: str) -> str:
    """تنظیم فاصله قبل/بعد از علائم رایج فارسی/لاتین."""
    # تبدیل ؟ ؛ ، انگلیسی به فارسی در صورت وجود حروف عربی در خط
    def _maybe_localize_punct(line: str) -> str:
        if RE_ARABIC_LETTERS.search(line):
            line = line.replace(';', '؛').replace(',', '،').replace('?', '؟')
        return line
    lines = s.splitlines()
    fixed_lines = []
    for line in lines:
        line = _maybe_localize_punct(line)
        for pat, rep in PERSIAN_PUNCT_FIXES:
            line = reg.sub(pat, rep, line)
        fixed_lines.append(line)
    return '\n'.join(fixed_lines)

def dehyphenate_linebreaks(s: str) -> str:
    """حذف هایفن‌خوردگی انتهای سطر: '…کلم-\n ه' → '…کلمه' و حذف soft hyphen."""
    s = s.replace('\u00AD', '')  # soft hyphen
    # اگر خط با - تمام شده و خط بعدی با حرف فارسی/لاتین شروع می‌شود → بچسبان
    s = reg.sub(r'-\n(?=[\p{L}\p{Nd}])', '', s)
    return s

def collapse_spaces(s: str) -> str:
    """کاهش فاصله‌های چندگانه، حفظ خطوط خالی."""
    # چند space → یک space (به‌جز داخل سطرها، خطوط خالی نگه داشته می‌شود)
    s = reg.sub(r'[ \t]{2,}', ' ', s)
    # حذف space در ابتدای/انتهای خطوط
    s = '\n'.join([ln.strip() for ln in s.splitlines()])
    # چند خط خالی پیاپی → حداکثر یک خط خالی
    s = reg.sub(r'\n{3,}', '\n\n', s)
    return s

def maybe_fix_bidi_visual_lines(s: str) -> str:
    """
    اگر استخراج بصری/وارونه بوده (بعضی PDFها)، با BiDi+reshaper سطر را «نمایشیِ درست» می‌کنیم.
    فقط وقتی کتابخانه‌ها در دسترس باشند و خط بیشترِ حروفش عربی باشد.
    """
    if get_display is None or arabic_reshaper is None:
        return s

    fixed_lines = []
    for line in s.splitlines():
        arabic_ratio = _arabic_ratio(line)
        # اگر فارسی/عربی غالب است، و ترتیب بصری مشکوک است، تلاش برای get_display
        if arabic_ratio > 0.3 and _looks_visually_reversed(line):
            try:
                reshaped = arabic_reshaper.reshape(line)
                line = get_display(reshaped)
            except Exception:
                pass
        fixed_lines.append(line)
    return '\n'.join(fixed_lines)

def _arabic_ratio(s: str) -> float:
    if not s:
        return 0.0
    letters = [ch for ch in s if ch.isalpha()]
    if not letters:
        return 0.0
    arab = sum(1 for ch in letters if RE_ARABIC_LETTERS.match(ch))
    return arab / max(1, len(letters))

def _looks_visually_reversed(line: str) -> bool:
    """
    هوریستیک ساده: وجود تعداد زیاد فاصله‌های درون‌کلمه‌ای یا ترتیب عجیب نقل‌قول/پرانتز در متن عربی.
    """
    if _arabic_ratio(line) < 0.3:
        return False
    # فاصله‌های تک‌حرفی متعدد
    if reg.search(r'(?:\b\w\b\s+){3,}', line):
        return True
    # پرانتز باز/بسته در جای ناصحیح نسبت به متن عربی
    if '([' in line or ')]' in line:
        return True
    return False

def normalize_persian_text(s: str,
                           digits: str = 'persian',
                           keep_diacritics: bool = False,
                           fix_halfspace_flag: bool = True,
                           apply_bidi_fix: bool = True) -> str:
    """زنجیره کامل نرمال‌سازی فارسی."""
    s = normalize_arabic_persian_letters(s)
    if not keep_diacritics:
        s = remove_diacritics(s)
    s = dehyphenate_linebreaks(s)
    s = fix_punct_spaces(s)
    if fix_halfspace_flag:
        s = fix_half_space(s)
    s = replace_digits(s, mode=digits)
    s = collapse_spaces(s)
    if apply_bidi_fix:
        s = maybe_fix_bidi_visual_lines(s)
    return s

def looks_unreadable_persian(s: str) -> bool:
    """
    سنجش کیفیت متن استخراج‌شده:
    - نسبت حروف عربی بسیار کم
    - وجود زیاد PUAs
    - طول متوسط واژه‌ها به‌شدت غیرطبیعی
    """
    if not s or s.strip() == '':
        return True
    arabic_ratio = _arabic_ratio(s)
    private_use = len(RE_PRIVATE_USE.findall(s))
    tokens = s.split()
    avg_len = (sum(len(t) for t in tokens) / max(1, len(tokens))) if tokens else 0

    # آستانه‌ها تجربی
    if arabic_ratio < 0.15:
        return True
    if private_use > len(s) * 0.02:
        return True
    if avg_len > 30:  # نشانه‌ی کاراکترهای به‌هم‌چسبیده/بی‌معنا
        return True
    return False

def extract_with_pdfminer(pdf_path: str) -> str:
    if pdfminer_extract_text is None:
        return ""
    try:
        text = pdfminer_extract_text(pdf_path)  # LAParams پیش‌فرض معمولاً خوب است
        return text or ""
    except Exception:
        return ""

def ocr_with_tesseract(pdf_path: str, dpi: int = 300) -> str:
    if fitz is None or pytesseract is None or Image is None:
        return ""

    text_pages: List[str] = []
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # رندر با DPI مناسب برای OCR
        mat = fitz.Matrix(dpi/72.0, dpi/72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        try:
            # نیازمند tesseract-lang: fas
            page_text = pytesseract.image_to_string(img, lang="fas+eng")
        except Exception:
            page_text = ""
        text_pages.append(page_text)
    return "\n\n".join(text_pages)

def extract_persian_text(pdf_path: str,
                         force_ocr: bool = False,
                         digits: str = 'persian',
                         keep_diacritics: bool = False,
                         fix_halfspace_flag: bool = True,
                         apply_bidi_fix: bool = True) -> Tuple[str, bool]:
    """
    خروجی: (متن نهایی نرمال‌شده، آیا OCR استفاده شد؟)
    """
    raw_text = ""
    used_ocr = False

    if not force_ocr:
        raw_text = extract_with_pdfminer(pdf_path)
        if looks_unreadable_persian(raw_text):
            # سقوط به OCR
            ocr_text = ocr_with_tesseract(pdf_path)
            if ocr_text.strip():
                raw_text = ocr_text
                used_ocr = True
    else:
        ocr_text = ocr_with_tesseract(pdf_path)
        if ocr_text.strip():
            raw_text = ocr_text
            used_ocr = True

    # اگر هنوز خالی است، هر چه pdfminer داد را می‌گیریم (حالا حتی اگر ضعیف)
    if not raw_text:
        raw_text = extract_with_pdfminer(pdf_path)

    norm = normalize_persian_text(raw_text,
                                  digits=digits,
                                  keep_diacritics=keep_diacritics,
                                  fix_halfspace_flag=fix_halfspace_flag,
                                  apply_bidi_fix=apply_bidi_fix)
    return norm, used_ocr

def main():
    ap = argparse.ArgumentParser(description="استخراج و نرمال‌سازی متن فارسی از PDF.")
    ap.add_argument("pdf", help="مسیر فایل PDF ورودی")
    ap.add_argument("-o", "--output", help="مسیر ذخیره متن (txt). اگر ندهید، در stdout چاپ می‌شود.")
    ap.add_argument("--force-ocr", action="store_true", default=False,
                    help="صرف‌نظر از pdfminer، مستقیماً از OCR استفاده کن.")
    ap.add_argument("--no-ocr", action="store_true", default=False,
                    help="OCR انجام نشود (حتی اگر متن ناخوانا بود).")
    ap.add_argument("--digits", choices=["persian", "latin", "keep"], default="persian",
                    help="تبدیل اعداد: persian (پیش‌فرض) / latin / keep")
    ap.add_argument("--keep-diacritics", action="store_true", default=False,
                    help="اعراب را حذف نکن (پیش‌فرض حذف می‌شود).")
    ap.add_argument("--no-halfspace-fix", action="store_true", default=False,
                    help="اصلاح نیم‌فاصله انجام نشود.")
    ap.add_argument("--no-bidi-fix", action="store_true", default=False,
                    help="درمان BiDi روی خطوط مشکوک انجام نشود.")
    args = ap.parse_args()

    if not os.path.exists(args.pdf):
        print(f"فایل یافت نشد: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    force_ocr = args.force_ocr
    if args.no_ocr:
        force_ocr = False
        # و همچنین در looks_unreadable، به OCR سقوط نکنیم:
        # اینجا ساده نگه می‌داریم؛ اگر no-ocr باشد، تنها pdfminer استفاده می‌شود.
        global looks_unreadable_persian
        def looks_unreadable_persian(_):  # type: ignore
            return False

    text, used_ocr = extract_persian_text(
        args.pdf,
        force_ocr=force_ocr,
        digits=args.digits,
        keep_diacritics=args.keep_diacritics,
        fix_halfspace_flag=not args.no_halfspace_fix,
        apply_bidi_fix=not args.no_bidi_fix
    )

    header = ""
    if used_ocr:
        header = "## [OCR فعال شد: متن با Tesseract استخراج گردید]\n\n"
    out = header + text

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"✅ متن نهایی در فایل ذخیره شد: {args.output}")
    else:
        # چاپ در خروجی استاندارد
        sys.stdout.write(out)

if __name__ == "__main__":
    main()
