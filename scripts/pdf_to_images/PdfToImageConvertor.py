#!/usr/bin/env python3
"""
PDF Pages to Images Converter
Converts each page of a PDF file into high-quality images.
Reads PDF path from command line arguments and saves images to output directory.
"""

import os
import sys
import argparse
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Convert PDF pages to images')
    parser.add_argument('--input', required=True, help='Path to the input PDF file')
    parser.add_argument('--output_path', required=True, help='Path to the output directory')
    parser.add_argument('--quality', choices=['1', '2', '3', '4'], default='1', 
                       help='Quality option: 1=High (300 DPI PNG), 2=Medium (200 DPI JPEG), 3=Web (150 DPI JPEG), 4=All qualities')
    
    return parser.parse_args()

def create_output_directory(pdf_path, output_path):
    """Create output directory for page images"""
    pdf_name = pdf_path.stem  # filename without extension
    output_dir = Path(output_path) / pdf_name / "images/pages"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def convert_pages_to_images(pdf_path, output_dir, dpi=300, image_format='PNG'):
    """Convert each PDF page to high-quality image"""
    logger.info(f"Converting PDF pages to {image_format} images at {dpi} DPI...")
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    logger.info(f"Total pages to convert: {total_pages}")
    
    converted_count = 0
    
    for page_num in range(total_pages):
        try:
            page = doc.load_page(page_num)
            
            # Calculate zoom factor for desired DPI
            # PyMuPDF default is 72 DPI, so zoom = desired_dpi / 72
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image for better quality control
            img_data = pix.tobytes("png")
            pil_image = Image.open(io.BytesIO(img_data))
            
            # Optimize image quality
            if pil_image.mode == 'RGBA':
                # Create white background for transparent areas
                background = Image.new('RGB', pil_image.size, (255, 255, 255))
                background.paste(pil_image, mask=pil_image.split()[-1])
                pil_image = background
            elif pil_image.mode not in ('RGB', 'L'):
                pil_image = pil_image.convert('RGB')
            
            # Generate filename
            page_filename = f"page_{page_num + 1:04d}.{image_format.lower()}"
            page_path = output_dir / page_filename
            
            # Save with high quality settings
            save_kwargs = {'optimize': True}
            if image_format.upper() == 'JPEG':
                save_kwargs['quality'] = 95
            elif image_format.upper() == 'PNG':
                save_kwargs['compress_level'] = 6  # Good balance of size and speed
            
            pil_image.save(page_path, image_format.upper(), **save_kwargs)
            
            converted_count += 1
            logger.info(f"Converted page {page_num + 1}/{total_pages}: {page_filename} ({pil_image.width}x{pil_image.height})")
            
            # Clean up
            pix = None
            
        except Exception as e:
            logger.error(f"Failed to convert page {page_num + 1}: {e}")
    
    doc.close()
    return converted_count, total_pages

def batch_convert_with_different_qualities(pdf_path, output_dir):
    """Convert pages with multiple quality options"""
    logger.info("Converting pages with multiple quality options...")
    
    # Different quality presets
    quality_presets = {
        'high': {'dpi': 300, 'format': 'PNG'},
        'medium': {'dpi': 200, 'format': 'JPEG'},
        'web': {'dpi': 150, 'format': 'JPEG'}
    }
    
    results = {}
    
    for quality_name, settings in quality_presets.items():
        quality_dir = output_dir / quality_name
        quality_dir.mkdir(exist_ok=True)
        
        logger.info(f"Converting to {quality_name} quality...")
        converted, total = convert_pages_to_images(
            pdf_path, 
            quality_dir, 
            dpi=settings['dpi'], 
            image_format=settings['format']
        )
        results[quality_name] = {'converted': converted, 'total': total, 'dir': quality_dir}
    
    return results

def get_pdf_info(pdf_path):
    """Get basic information about the PDF"""
    doc = fitz.open(pdf_path)
    info = {
        'pages': len(doc),
        'title': doc.metadata.get('title', 'Unknown'),
        'author': doc.metadata.get('author', 'Unknown'),
        'subject': doc.metadata.get('subject', 'Unknown'),
        'creator': doc.metadata.get('creator', 'Unknown')
    }
    
    # Get page dimensions (first page)
    if len(doc) > 0:
        page = doc.load_page(0)
        rect = page.rect
        info['page_width'] = rect.width
        info['page_height'] = rect.height
        info['page_size'] = f"{rect.width:.1f} x {rect.height:.1f} points"
    
    doc.close()
    return info

def main():
    """Main conversion process"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        pdf_path = Path(args.input)
        output_path = Path(args.output_path)
        quality_choice = args.quality
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Processing PDF: {pdf_path}")
        logger.info(f"Output path: {output_path}")
        
        # Get PDF information
        pdf_info = get_pdf_info(pdf_path)
        logger.info(f"PDF Info - Pages: {pdf_info['pages']}, Size: {pdf_info['page_size']}")
        if pdf_info['title'] != 'Unknown':
            logger.info(f"Title: {pdf_info['title']}")
        
        # Create output directory
        output_dir = create_output_directory(pdf_path, output_path)
        logger.info(f"Output directory: {output_dir}")
        
        if quality_choice == '4':
            # Convert with all quality presets
            results = batch_convert_with_different_qualities(pdf_path, output_dir)
            
            # Final report for batch conversion
            logger.info("\n" + "="*50)
            logger.info("BATCH CONVERSION COMPLETE")
            logger.info("="*50)
            for quality_name, result in results.items():
                logger.info(f"{quality_name.upper()}: {result['converted']}/{result['total']} pages → {result['dir']}")
        
        else:
            # Single quality conversion
            quality_settings = {
                '1': {'dpi': 300, 'format': 'PNG', 'name': 'High'},
                '2': {'dpi': 200, 'format': 'JPEG', 'name': 'Medium'},
                '3': {'dpi': 150, 'format': 'JPEG', 'name': 'Web'}
            }
            
            settings = quality_settings.get(quality_choice, quality_settings['1'])
            
            logger.info(f"Selected: {settings['name']} quality ({settings['dpi']} DPI {settings['format']})")
            
            converted_count, total_pages = convert_pages_to_images(
                pdf_path, 
                output_dir, 
                dpi=settings['dpi'], 
                image_format=settings['format']
            )
            
            # Final report
            logger.info("\n" + "="*50)
            logger.info("CONVERSION COMPLETE")
            logger.info("="*50)
            logger.info(f"Successfully converted: {converted_count}/{total_pages} pages")
            logger.info(f"Quality: {settings['name']} ({settings['dpi']} DPI {settings['format']})")
            logger.info(f"Images saved to: {output_dir}")
            
            if converted_count == 0:
                logger.warning("No pages were converted successfully.")
            elif converted_count < total_pages:
                logger.warning(f"Some pages failed to convert ({total_pages - converted_count} failures)")
        
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
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