import json
import subprocess
import sys
import os
from pathlib import Path

def run_chain(workflow_file):
    """
    فایل workflow.json را خوانده و دستورات chain را اجرا می‌کند
    """
    try:
        # خواندن فایل workflow.json
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        # بررسی ساختار فایل
        if 'chain' not in workflow:
            print("Error: 'chain' key not found in workflow file")
            return False
        
        chain = workflow['chain']
        
        # اجرای هر مرحله از chain
        for i, step in enumerate(chain):
            print(f"\n=== Executing Step {i+1} ===")
            
            # بررسی وجود کلیدهای ضروری
            required_keys = ['app', 'path', 'input_file', 'output_file']
            for key in required_keys:
                if key not in step:
                    print(f"Error: Missing '{key}' in step {i+1}")
                    return False
            
            app_name = step['app']
            app_path = step['path']
            input_file = step['input_file']
            output_path = step['output_file']
            
            # ساخت مسیر کامل به اسکریپت
            script_path = os.path.join(app_path, app_name)
            
            # بررسی وجود فایل اسکریپت
            if not os.path.exists(script_path):
                print(f"Error: Script not found at {script_path}")
                return False
            
            print(f"Script: {script_path}")
            print(f"Input: {input_file}")
            print(f"Output: {output_path}")
            
            # اجرای اسکریپت با subprocess
            try:
                # ساخت دستور اجرا
                command = [
                    'python3',
                    script_path,
                    '--input', input_file,
                    '--output_path', output_path
                ]
                
                print(f"Command: {' '.join(command)}")
                
                # اجرای دستور
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                print("Output:")
                print(result.stdout)
                if result.stderr:
                    print("Errors:")
                    print(result.stderr)
                
                print(f"Step {i+1} completed successfully")
                
            except subprocess.CalledProcessError as e:
                print(f"Error executing step {i+1}: {e}")
                print(f"STDERR: {e.stderr}")
                return False
            except Exception as e:
                print(f"Unexpected error in step {i+1}: {e}")
                return False
        
        print("\n=== All steps completed successfully! ===")
        return True
        
    except FileNotFoundError:
        print(f"Error: Workflow file '{workflow_file}' not found")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in workflow file: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def main():
    """
    تابع اصلی برای اجرای برنامه
    """
    # مسیر پیش‌فرض فایل workflow
    workflow_file = "workflow.json"
    
    # اگر آرگومان خط فرمان داده شده باشد
    if len(sys.argv) > 1:
        workflow_file = sys.argv[1]
    
    print(f"Running chain from: {workflow_file}")
    
    # اجرای chain
    success = run_chain(workflow_file)
    
    if not success:
        print("Chain execution failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()