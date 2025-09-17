#!/usr/bin/env python3
"""
Enhanced PDF Persian Text Extractor
Advanced Persian/Farsi text extraction with proper character reconstruction.
Reads PDF path from input.txt and saves both page images and extracted text.
"""

import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import io
import logging
import re
import unicodedata
from bidi.algorithm import get_display
import arabic_reshaper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def read_pdf_path():
    """Read PDF file path from input.txt"""
    input_file = Path("input.txt")
    
    if not input_file.exists():
        raise FileNotFoundError("input.txt file not found. Please create it with the PDF file path.")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        pdf_path = f.read().strip()
    
    if not pdf_path:
        raise ValueError("input.txt is empty. Please add the PDF file path.")
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    return pdf_path

def create_output_directories(pdf_path):
    """Create output directories for images and text"""
    pdf_name = pdf_path.stem
    base_dir = Path("output") / pdf_name
    images_dir = base_dir / "images"
    text_dir = base_dir / "text"
    
    images_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    
    return base_dir, images_dir, text_dir

def reconstruct_persian_text(text_blocks):
    """Reconstruct Persian text from fragmented blocks"""
    if not text_blocks:
        return ""
    
    # Join blocks and clean excessive spaces
    reconstructed = " ".join(text_blocks)
    
    # Remove extra spaces
    reconstructed = re.sub(r'\s+', ' ', reconstructed)
    
    # Persian character mapping for common OCR/extraction errors
    char_fixes = {
        # Fix isolated forms to proper connected forms
        'ﺍ': 'ا', 'ﺎ': 'ا', 'ﺁ': 'آ', 'ﺂ': 'آ',
        'ﺏ': 'ب', 'ﺐ': 'ب', 'ﺑ': 'ب', 'ﺒ': 'ب',
        'ﭖ': 'پ', 'ﭗ': 'پ', 'ﭘ': 'پ', 'ﭙ': 'پ',
        'ﺕ': 'ت', 'ﺖ': 'ت', 'ﺗ': 'ت', 'ﺘ': 'ت',
        'ﺙ': 'ث', 'ﺚ': 'ث', 'ﺛ': 'ث', 'ﺜ': 'ث',
        'ﺝ': 'ج', 'ﺞ': 'ج', 'ﺟ': 'ج', 'ﺠ': 'ج',
        'ﭺ': 'چ', 'ﭻ': 'چ', 'ﭼ': 'چ', 'ﭽ': 'چ',
        'ﺡ': 'ح', 'ﺢ': 'ح', 'ﺣ': 'ح', 'ﺤ': 'ح',
        'ﺥ': 'خ', 'ﺦ': 'خ', 'ﺧ': 'خ', 'ﺨ': 'خ',
        'ﺩ': 'د', 'ﺪ': 'د',
        'ﺫ': 'ذ', 'ﺬ': 'ذ',
        'ﺭ': 'ر', 'ﺮ': 'ر',
        'ﺯ': 'ز', 'ﺰ': 'ز',
        'ﮊ': 'ژ', 'ﮋ': 'ژ',
        'ﺱ': 'س', 'ﺲ': 'س', 'ﺳ': 'س', 'ﺴ': 'س',
        'ﺵ': 'ش', 'ﺶ': 'ش', 'ﺷ': 'ش', 'ﺸ': 'ش',
        'ﺹ': 'ص', 'ﺺ': 'ص', 'ﺻ': 'ص', 'ﺼ': 'ص',
        'ﺽ': 'ض', 'ﺾ': 'ض', 'ﺿ': 'ض', 'ﻀ': 'ض',
        'ﻁ': 'ط', 'ﻂ': 'ط', 'ﻃ': 'ط', 'ﻄ': 'ط',
        'ﻅ': 'ظ', 'ﻆ': 'ظ', 'ﻇ': 'ظ', 'ﻈ': 'ظ',
        'ﻉ': 'ع', 'ﻊ': 'ع', 'ﻋ': 'ع', 'ﻌ': 'ع',
        'ﻍ': 'غ', 'ﻎ': 'غ', 'ﻏ': 'غ', 'ﻐ': 'غ',
        'ﻑ': 'ف', 'ﻒ': 'ف', 'ﻓ': 'ف', 'ﻔ': 'ف',
        'ﻕ': 'ق', 'ﻖ': 'ق', 'ﻗ': 'ق', 'ﻘ': 'ق',
        'ﮎ': 'ک', 'ﮏ': 'ک', 'ﮐ': 'ک', 'ﮑ': 'ک',
        'ﮒ': 'گ', 'ﮓ': 'گ', 'ﮔ': 'گ', 'ﮕ': 'گ',
        'ﻝ': 'ل', 'ﻞ': 'ل', 'ﻟ': 'ل', 'ﻠ': 'ل',
        'ﻡ': 'م', 'ﻢ': 'م', 'ﻣ': 'م', 'ﻤ': 'م',
        'ﻥ': 'ن', 'ﻦ': 'ن', 'ﻧ': 'ن', 'ﻨ': 'ن',
        'ﻭ': 'و', 'ﻮ': 'و',
        'ﻩ': 'ه', 'ﻪ': 'ه', 'ﻫ': 'ه', 'ﻬ': 'ه',
        'ﯼ': 'ی', 'ﯽ': 'ی', 'ﯾ': 'ی', 'ﯿ': 'ی',
        'ﻻ': 'لا', 'ﻼ': 'لا',
        # Fix Arabic characters to Persian equivalents
        'ي': 'ی', 'ك': 'ک', 'ء': 'ٔ',
        # Fix numbers
        '٠': '۰', '١': '۱', '٢': '۲', '٣': '۳', '٤': '۴',
        '٥': '۵', '٦': '۶', '٧': '۷', '٨': '۸', '٩': '۹'
    }
    
    # Apply character fixes
    for wrong, correct in char_fixes.items():
        reconstructed = reconstructed.replace(wrong, correct)
    
    return reconstructed.strip()

def extract_text_with_positions(page):
    """Extract text with positional information for better reconstruction"""
    try:
        text_dict = page.get_text("dict", flags=11)
        
        # Collect all text blocks with their positions
        text_blocks = []
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                block_bbox = block["bbox"]  # x0, y0, x1, y1
                block_texts = []
                
                for line in block["lines"]:
                    line_texts = []
                    for span in line["spans"]:
                        if span["text"].strip():
                            line_texts.append(span["text"])
                    
                    if line_texts:
                        line_text = "".join(line_texts)  # Don't add spaces between spans
                        block_texts.append(line_text)
                
                if block_texts:
                    block_text = " ".join(block_texts)
                    text_blocks.append({
                        'text': block_text,
                        'bbox': block_bbox,
                        'y': block_bbox[1]  # top y coordinate
                    })
        
        # Sort blocks by vertical position (top to bottom)
        text_blocks.sort(key=lambda x: x['y'])
        
        # Extract just the text in order
        ordered_texts = [block['text'] for block in text_blocks]
        
        return ordered_texts
        
    except Exception as e:
        logger.warning(f"Position-based extraction failed: {e}")
        return []

def extract_text_multiple_methods(page):
    """Try multiple extraction methods and return the best result"""
    methods_results = {}
    
    # Method 1: Position-based extraction (best for Persian)
    try:
        positioned_texts = extract_text_with_positions(page)
        if positioned_texts:
            reconstructed = reconstruct_persian_text(positioned_texts)
            if reconstructed and len(reconstructed) > 10:  # Must have meaningful content
                methods_results['positioned'] = reconstructed
    except Exception as e:
        logger.warning(f"Position-based method failed: {e}")
    
    # Method 2: Simple text extraction with character fixing
    try:
        simple_text = page.get_text()
        if simple_text:
            fixed_text = reconstruct_persian_text([simple_text])
            if fixed_text and len(fixed_text) > 10:
                methods_results['simple'] = fixed_text
    except Exception as e:
        logger.warning(f"Simple method failed: {e}")
    
    # Method 3: Raw text blocks extraction
    try:
        raw_blocks = []
        text_dict = page.get_text("dict")
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():
                            raw_blocks.append(span["text"])
        
        if raw_blocks:
            block_text = reconstruct_persian_text(raw_blocks)
            if block_text and len(block_text) > 10:
                methods_results['raw_blocks'] = block_text
    except Exception as e:
        logger.warning(f"Raw blocks method failed: {e}")
    
    # Method 4: Layout-preserved extraction
    try:
        layout_text = page.get_text("text", sort=True)
        if layout_text:
            layout_fixed = reconstruct_persian_text([layout_text])
            if layout_fixed and len(layout_fixed) > 10:
                methods_results['layout'] = layout_fixed
    except Exception as e:
        logger.warning(f"Layout method failed: {e}")
    
    # Choose the best result
    if not methods_results:
        return ""
    
    # Prefer positioned method, then longest text
    if 'positioned' in methods_results:
        best_result = methods_results['positioned']
        logger.info(f"Using positioned extraction method")
    else:
        # Choose the longest result
        best_result = max(methods_results.values(), key=len)
        best_method = [k for k, v in methods_results.items() if v == best_result][0]
        logger.info(f"Using {best_method} extraction method")
    
    return best_result

def clean_and_format_persian_text(text):
    """Final cleaning and formatting of Persian text"""
    if not text:
        return ""
    
    # Remove excessive spaces and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Fix common punctuation issues
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)  # Remove space before punctuation
    text = re.sub(r'([,.;:!?])\s*', r'\1 ', text)  # Add single space after punctuation
    
    # Remove standalone diacritics that got separated
    text = re.sub(r'\s+[\u064B-\u065F\u0670\u06D6-\u06ED]\s+', ' ', text)
    
    # Fix word boundaries
    text = re.sub(r'(\S)\s+(\S)', r'\1 \2', text)
    
    return text.strip()

def convert_page_to_image(page, dpi=300):
    """Convert PDF page to high-quality image"""
    try:
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        img_data = pix.tobytes("png")
        pil_image = Image.open(io.BytesIO(img_data))
        
        if pil_image.mode == 'RGBA':
            background = Image.new('RGB', pil_image.size, (255, 255, 255))
            background.paste(pil_image, mask=pil_image.split()[-1])
            pil_image = background
        elif pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')
        
        pix = None
        return pil_image
        
    except Exception as e:
        logger.error(f"Failed to convert page to image: {e}")
        return None

def save_text_files(text, text_dir, page_num):
    """Save extracted text in multiple formats"""
    try:
        if not text or len(text.strip()) < 3:
            return False
        
        # Clean and format the text
        cleaned_text = clean_and_format_persian_text(text)
        
        # Save raw extracted text
        raw_file = text_dir / f"page_{page_num:04d}_raw.txt"
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        # Save with proper RTL formatting for display
        try:
            formatted_text = get_display(arabic_reshaper.reshape(cleaned_text))
            formatted_file = text_dir / f"page_{page_num:04d}_display.txt"
            with open(formatted_file, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
        except:
            # If RTL formatting fails, save the cleaned version
            formatted_file = text_dir / f"page_{page_num:04d}_display.txt"
            with open(formatted_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
        
        # Save with BOM for Windows compatibility
        bom_file = text_dir / f"page_{page_num:04d}_bom.txt"
        with open(bom_file, 'w', encoding='utf-8-sig') as f:
            f.write(cleaned_text)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to save text for page {page_num}: {e}")
        return False

def process_pdf_pages(pdf_path, images_dir, text_dir):
    """Process PDF pages with enhanced Persian text extraction"""
    logger.info("Processing PDF with enhanced Persian text extraction...")
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    logger.info(f"Total pages to process: {total_pages}")
    
    successful_pages = 0
    pages_with_text = 0
    all_texts = []
    
    for page_num in range(total_pages):
        try:
            page = doc.load_page(page_num)
            page_number = page_num + 1
            
            logger.info(f"Processing page {page_number}/{total_pages}...")
            
            # Convert page to image
            pil_image = convert_page_to_image(page, dpi=300)
            if pil_image:
                img_filename = f"page_{page_number:04d}.png"
                img_path = images_dir / img_filename
                pil_image.save(img_path, 'PNG', optimize=True, compress_level=6)
                logger.info(f"  ✓ Image saved: {img_filename} ({pil_image.width}x{pil_image.height})")
            
            # Extract text using multiple methods
            extracted_text = extract_text_multiple_methods(page)
            
            if extracted_text and len(extracted_text.strip()) > 0:
                if save_text_files(extracted_text, text_dir, page_number):
                    pages_with_text += 1
                    all_texts.append(f"=== صفحه {page_number} ===\n{extracted_text}\n")
                    
                    # Show preview
                    preview = extracted_text[:100].replace('\n', ' ')
                    if len(extracted_text) > 100:
                        preview += "..."
                    logger.info(f"  ✓ Text extracted ({len(extracted_text)} chars): {preview}")
                else:
                    logger.warning(f"  ✗ Failed to save text for page {page_number}")
            else:
                logger.info(f"  ⚠ No readable text found on page {page_number}")
            
            successful_pages += 1
            
        except Exception as e:
            logger.error(f"Failed to process page {page_number}: {e}")
    
    # Save complete document text
    if all_texts:
        try:
            complete_text = "\n\n".join(all_texts)
            
            complete_file = text_dir / "complete_document.txt"
            with open(complete_file, 'w', encoding='utf-8-sig') as f:
                f.write(complete_text)
            
            logger.info(f"✓ Complete document text saved: {complete_file}")
            
        except Exception as e:
            logger.error(f"Failed to save complete document: {e}")
    
    doc.close()
    return successful_pages, total_pages, pages_with_text

def main():
    """Main processing function"""
    try:
        pdf_path = read_pdf_path()
        logger.info(f"Processing PDF: {pdf_path}")
        
        base_dir, images_dir, text_dir = create_output_directories(pdf_path)
        logger.info(f"Output directory: {base_dir}")
        
        successful_pages, total_pages, pages_with_text = process_pdf_pages(
            pdf_path, images_dir, text_dir
        )
        
        # Final report
        logger.info("\n" + "=" * 60)
        logger.info("EXTRACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Successfully processed: {successful_pages}/{total_pages} pages")
        logger.info(f"Pages with text: {pages_with_text}")
        logger.info(f"Output saved to: {base_dir}")
        
        if pages_with_text > 0:
            logger.info("\n✓ Enhanced Persian text extraction completed!")
            logger.info("Check files ending with '_raw.txt' for the best results")
        else:
            logger.warning("No readable text was extracted.")
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check required packages
    missing_packages = []
    
    try:
        import fitz
    except ImportError:
        missing_packages.append("PyMuPDF")
    
    try:
        from PIL import Image
    except ImportError:
        missing_packages.append("Pillow")
    
    try:
        import arabic_reshaper
    except ImportError:
        missing_packages.append("arabic-reshaper")
    
    try:
        from bidi.algorithm import get_display
    except ImportError:
        missing_packages.append("python-bidi")
    
    if missing_packages:
        print("Missing required packages. Please install:")
        print(f"pip install {' '.join(missing_packages)}")
        sys.exit(1)
    
    main()