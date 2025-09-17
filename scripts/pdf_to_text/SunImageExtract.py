#!/usr/bin/env python3
"""
PDF Image Extractor
Extracts images from PDF files with high quality results.
Reads PDF path from input.txt and saves images to output directory.
"""

import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io
import hashlib
import logging

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

def create_output_directory(pdf_path):
    """Create output directory structure"""
    pdf_name = pdf_path.stem  # filename without extension
    output_dir = Path("output") / pdf_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def get_image_hash(image_data):
    """Generate hash for image data to detect duplicates"""
    return hashlib.md5(image_data).hexdigest()

def extract_images_pymupdf(pdf_path, output_dir):
    """Extract images using PyMuPDF - best for most PDFs"""
    logger.info("Extracting images using PyMuPDF...")
    
    doc = fitz.open(pdf_path)
    image_count = 0
    extracted_hashes = set()
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                # Skip if image is too small (likely icons or decorative elements)
                if pix.width < 50 or pix.height < 50:
                    pix = None
                    continue
                
                # Convert CMYK to RGB if necessary
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = pix.tobytes("png")
                else:  # CMYK: convert to RGB first
                    pix1 = fitz.Pixmap(fitz.csRGB, pix)
                    img_data = pix1.tobytes("png")
                    pix1 = None
                
                # Check for duplicates
                img_hash = get_image_hash(img_data)
                if img_hash in extracted_hashes:
                    pix = None
                    continue
                
                extracted_hashes.add(img_hash)
                
                # Save image
                img_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
                img_path = output_dir / img_filename
                
                with open(img_path, "wb") as img_file:
                    img_file.write(img_data)
                
                image_count += 1
                logger.info(f"Extracted: {img_filename} ({pix.width}x{pix.height})")
                
                pix = None
                
            except Exception as e:
                logger.warning(f"Failed to extract image {img_index + 1} from page {page_num + 1}: {e}")
    
    doc.close()
    return image_count

def extract_images_advanced(pdf_path, output_dir):
    """Advanced extraction for edge cases and better quality"""
    logger.info("Performing advanced image extraction...")
    
    doc = fitz.open(pdf_path)
    image_count = 0
    extracted_hashes = set()
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Method 1: Extract images with better quality settings
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Check image size
                try:
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    if pil_image.width < 50 or pil_image.height < 50:
                        continue
                except:
                    continue
                
                # Check for duplicates
                img_hash = get_image_hash(image_bytes)
                if img_hash in extracted_hashes:
                    continue
                
                extracted_hashes.add(img_hash)
                
                # Save with original format when possible
                img_filename = f"advanced_page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                img_path = output_dir / img_filename
                
                with open(img_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                image_count += 1
                logger.info(f"Advanced extracted: {img_filename} ({pil_image.width}x{pil_image.height})")
                
            except Exception as e:
                logger.warning(f"Advanced extraction failed for image {img_index + 1} from page {page_num + 1}: {e}")
        
        # Method 2: Render page as image and extract (for complex layouts)
        try:
            # High resolution rendering
            mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            if pix.width > 100 and pix.height > 100:  # Only save if reasonable size
                img_data = pix.tobytes("png")
                img_hash = get_image_hash(img_data)
                
                if img_hash not in extracted_hashes:
                    extracted_hashes.add(img_hash)
                    img_filename = f"rendered_page_{page_num + 1}.png"
                    img_path = output_dir / img_filename
                    
                    with open(img_path, "wb") as img_file:
                        img_file.write(img_data)
                    
                    image_count += 1
                    logger.info(f"Rendered page: {img_filename} ({pix.width}x{pix.height})")
            
            pix = None
            
        except Exception as e:
            logger.warning(f"Page rendering failed for page {page_num + 1}: {e}")
    
    doc.close()
    return image_count

def optimize_images(output_dir):
    """Optimize extracted images for better quality and size"""
    logger.info("Optimizing extracted images...")
    
    for img_path in output_dir.glob("*.png"):
        try:
            with Image.open(img_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # Save optimized version
                img.save(img_path, 'PNG', optimize=True, quality=95)
                
        except Exception as e:
            logger.warning(f"Failed to optimize {img_path.name}: {e}")

def main():
    """Main extraction process"""
    try:
        # Read PDF path from input.txt
        pdf_path = read_pdf_path()
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Create output directory
        output_dir = create_output_directory(pdf_path)
        logger.info(f"Output directory: {output_dir}")
        
        # Extract images using multiple methods
        total_images = 0
        
        # Method 1: Standard PyMuPDF extraction
        total_images += extract_images_pymupdf(pdf_path, output_dir)
        
        # Method 2: Advanced extraction for edge cases
        total_images += extract_images_advanced(pdf_path, output_dir)
        
        # Optimize extracted images
        optimize_images(output_dir)
        
        # Final report
        actual_files = len(list(output_dir.glob("*.png"))) + len(list(output_dir.glob("*.jpg"))) + len(list(output_dir.glob("*.jpeg")))
        
        logger.info(f"Extraction complete!")
        logger.info(f"Total images processed: {total_images}")
        logger.info(f"Unique images saved: {actual_files}")
        logger.info(f"Images saved to: {output_dir}")
        
        if actual_files == 0:
            logger.warning("No images were extracted. The PDF might not contain extractable images.")
        
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Required packages check
    try:
        import fitz
        from PIL import Image
    except ImportError as e:
        print("Missing required packages. Please install:")
        print("pip install PyMuPDF Pillow")
        sys.exit(1)
    
    main()