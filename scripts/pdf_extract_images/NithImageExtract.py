#!/usr/bin/env python3
"""
PDF Single Image Extractor
Extracts only single images from PDF pages and saves them to 'main' directory.
Reads PDF path from command line arguments.
"""

import os
import sys
import argparse
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io
import hashlib
import logging

import warnings
warnings.filterwarnings("ignore", message=".*pixmap must be grayscale or rgb.*")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Extract single images from PDF pages')
    parser.add_argument('--input', required=True, help='Path to the input PDF file')
    parser.add_argument('--output_path', required=True, help='Path to the output directory')
    
    return parser.parse_args()

def create_main_directory(pdf_path, output_path):
    """Create main output directory"""
    pdf_name = pdf_path.stem  # filename without extension
    main_dir = Path(output_path) / pdf_name / "images/main"
    main_dir.mkdir(parents=True, exist_ok=True)
    return main_dir

def get_image_hash(image_data):
    """Generate hash for image data to detect duplicates"""
    return hashlib.md5(image_data).hexdigest()

def extract_single_images(pdf_path, main_dir):
    """Extract only single images from PDF pages"""
    logger.info("Extracting single images from PDF pages...")
    
    doc = fitz.open(pdf_path)
    image_count = 0
    extracted_hashes = set()
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        image_list = page.get_images(full=True)
        
        # Filter out small images first to get accurate count
        valid_images = []
        
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
                
                valid_images.append((img_data, pix.width, pix.height, img_hash))
                pix = None
                
            except Exception as e:
                logger.warning(f"Failed to process image {img_index + 1} from page {page_num + 1}: {e}")
        
        # Only save if there's exactly one valid image on the page
        if len(valid_images) == 1:
            img_data, width, height, img_hash = valid_images[0]
            extracted_hashes.add(img_hash)
            
            # Save to main directory
            img_filename = f"page_{page_num + 1}.png"
            img_path = main_dir / img_filename
            
            with open(img_path, "wb") as img_file:
                img_file.write(img_data)
            
            image_count += 1
            logger.info(f"Extracted single image: {img_filename} ({width}x{height})")
    
    doc.close()
    return image_count

def optimize_images(main_dir):
    """Optimize extracted images for better quality"""
    logger.info("Optimizing extracted images...")
    
    for img_path in main_dir.glob("*.png"):
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
        # Parse command line arguments
        args = parse_arguments()
        
        pdf_path = Path(args.input)
        output_path = Path(args.output_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Processing PDF: {pdf_path}")
        logger.info(f"Output path: {output_path}")
        
        # Create main directory
        main_dir = create_main_directory(pdf_path, output_path)
        logger.info(f"Main directory: {main_dir}")
        
        # Extract only single images from pages
        total_images = extract_single_images(pdf_path, main_dir)
        
        # Optimize extracted images
        optimize_images(main_dir)
        
        # Final report
        actual_files = len(list(main_dir.glob("*.png")))
        
        logger.info(f"Extraction complete!")
        logger.info(f"Single images found and saved: {actual_files}")
        logger.info(f"Images saved to: {main_dir}")
        
        if actual_files == 0:
            logger.warning("No single images were found. Pages either have multiple images or no extractable images.")
        
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