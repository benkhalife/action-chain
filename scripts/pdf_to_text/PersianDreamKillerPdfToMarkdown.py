import pypdfium2 as pdfium
import re
import os
from pathlib import Path

def create_directory(directory_path):
    try:
        os.makedirs(directory_path, exist_ok=True)
        print(f"Directory created successfully: {directory_path}")
        return True
    except Exception as e:
        print(f"Error creating directory: {e}")
        return False



def extract_persian_pages_to_markdown():
    try:
        # Read PDF file path from input.txt
        with open('input.txt', 'r', encoding='utf-8') as f:
            pdf_path = f.read().strip()
        
        with open('output.txt', 'r', encoding='utf-8') as f:
            pdf_output_path = f.read().strip()

        if not os.path.exists(pdf_path):
            print(f"PDF file not found: {pdf_path}")
            return False
        
        # Create output directory
        pdf_name = Path(pdf_path).stem
        output_dir = Path("output") / pdf_name 
        output_dir.mkdir(parents=True, exist_ok=True)

        if not create_directory(output_dir / "pages"):
            return False
        
        # Extract text from PDF
        pdf = pdfium.PdfDocument(pdf_path)
        total_pages = len(pdf)
        
        print(f"Processing PDF: {pdf_path}")
        print(f"Total pages: {total_pages}")
        
        for i in range(total_pages):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            
            # Process text for better Markdown formatting
            processed_text = process_text_for_markdown(text)
            
            # File name for current page
            filename = f"page_{i+1}.md"
            file_path = output_dir / "pages" / filename
            
            # Save to Markdown file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Page {i+1}\n\n")
                f.write(processed_text)
            
            textpage.close()
            page.close()
            
            print(f"Page {i+1} extracted successfully: {file_path}")

        # Create a combined markdown file with all pages
        combined_filename = f"book.md"
        combined_file_path = output_dir / combined_filename

        with open(combined_file_path, 'w', encoding='utf-8') as combined_f:
            for i in range(total_pages):
                page_filename = f"page_{i+1}.md"
                page_file_path = output_dir / "pages" / page_filename
                
                # Read content of each page file
                with open(page_file_path, 'r', encoding='utf-8') as page_f:
                    page_content = page_f.read()
                
                # Write to combined file
                combined_f.write(page_content)
                combined_f.write("\n\n---\n\n")  # Add separator between pages

        print(f"Combined file created: {combined_file_path}")
        
        print(f"Extraction completed. Files saved in: {output_dir}")
        return True
        
    except FileNotFoundError:
        print("Error: input.txt file not found")
        return False
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

def process_text_for_markdown(text):
    # Detect and format headings (based on common patterns)
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        # Remove empty lines
        if not line.strip():
            continue
            
        # Detect main headings (lines that start with Persian characters/numbers and are short)
        if len(line.strip()) < 50 and re.match(r'^[\u0600-\u06FF\s\d]+$', line.strip()):
            processed_lines.append(f"## {line.strip()}")
        else:
            processed_lines.append(line.strip())
    
    return '\n\n'.join(processed_lines)

# Run the function
if __name__ == "__main__":
    success = extract_persian_pages_to_markdown()
    if not success:
        print("Extraction failed. Please check the error messages.")