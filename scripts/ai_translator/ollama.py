#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import requests
import json
import time
from pathlib import Path

class OllamaTranslator:
    def __init__(self, model_name="gemma3:4b", base_url="http://192.168.1.115:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        
    def create_translation_prompt(self, text):
        """Create appropriate prompt for book translation"""
        prompt = f"""
        You are a professional text translator. Please translate the following text to Persian (Farsi) following these guidelines:
        
        1. Translation should be fluent, natural and understandable
        2. Preserve the sentence and paragraph structure
        3. Translate technical terms accurately and precisely
        4. Maintain the tone and style of the original text
        5. Avoid literal translation
        6. Properly transfer numbers, dates, and proper names
        
        Text to translate:
        {text}
        
        Persian translation:
        """
        return prompt
    
    def translate_text(self, text, max_retries=3):
        """Translate text using Ollama API"""
        prompt = self.create_translation_prompt(text)
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 4000
            }
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    print(f"Error connecting to Ollama (code {response.status_code}): {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Connection error attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Waiting for {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        raise Exception("Translation failed after multiple attempts")
    
    def process_file(self, input_file, output_file):
        """Process and translate a single file"""
        try:
            print(f"Processing: {input_file}")
            
            # Read file content
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                print(f"Empty file: {input_file}")
                return False
            
            # Translate content
            translated_text = self.translate_text(content)
            
            # Save result
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(translated_text)
            
            print(f"Translation saved: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error processing file {input_file}: {e}")
            return False
    
    def process_directory(self, input_dir, output_dir):
        """Process all files in a directory"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find text files
        text_files = list(input_path.glob("*.txt")) + list(input_path.glob("*.text"))+ list(input_path.glob("*.md"))
        
        if not text_files:
            print(f"No text files found in directory: {input_dir}")
            return
        
        print(f"Files to translate: {len(text_files)}")
        
        successful = 0
        for input_file in text_files:
            output_file = output_path / f"{input_file.stem}_translated.txt"
            
            if self.process_file(input_file, output_file):
                successful += 1
            
            # Short pause between file processing
            time.sleep(1)
        
        print(f"\nProcessing completed! {successful} out of {len(text_files)} files translated successfully.")

def main():
    parser = argparse.ArgumentParser(description='Translate text files using Ollama and Gemma3:4b model')
    parser.add_argument('--input_chunks_dir', required=True, 
                       help='Path to directory containing text files for translation')
    parser.add_argument('--output_dir', required=True, 
                       help='Path to directory for saving translated files')
    parser.add_argument('--model', default='gemma3:4b',
                       help='Ollama model name (default: gemma3:4b)')
    parser.add_argument('--ollama_url', default='http://192.168.1.115:11434',
                       help='Ollama API URL (default: http://192.168.1.115:11434)')
    
    args = parser.parse_args()
    
    # Check if input directory exists
    if not os.path.exists(args.input_chunks_dir):
        print(f"Error: Input directory '{args.input_chunks_dir}' does not exist")
        return
    
    # Create translator instance
    translator = OllamaTranslator(
        model_name=args.model,
        base_url=args.ollama_url
    )
    
    # Start processing
    print("Starting translation process...")
    print(f"Model: {args.model}")
    print(f"Input: {args.input_chunks_dir}")
    print(f"Output: {args.output_dir}")
    print("-" * 50)
    
    translator.process_directory(args.input_chunks_dir, args.output_dir)

if __name__ == "__main__":
    main()