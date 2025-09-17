from PIL import Image, ImageFilter, ImageDraw
import numpy as np
import os
from scipy import ndimage
import argparse

def detect_charts_with_pillow(image_path, output_dir, min_area=1500, min_width=50, min_height=50):
    """
    تشخیص نمودارها در تصویر با استفاده از Pillow و SciPy
    """
    try:
        print(f"در حال پردازش: {os.path.basename(image_path)}")
        
        # باز کردن تصویر
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_array = np.array(img)
        
        # تبدیل به grayscale
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2).astype(np.uint8)
        else:
            gray = img_array
        
        # اعمال فیلتر Gaussian برای کاهش نویز
        pil_gray = Image.fromarray(gray)
        filtered = pil_gray.filter(ImageFilter.GaussianBlur(radius=1))
        gray = np.array(filtered)
        
        # آستانه‌گذاری адаپتیو برای باینری کردن تصویر
        threshold = np.percentile(gray, 75)  # استفاده از صدک 75 به جای میانگین
        binary = (gray > threshold).astype(np.uint8) * 255
        
        # پیدا کردن مناطق متصل
        labeled_array, num_features = ndimage.label(binary)
        
        chart_images = []
        
        for i in range(1, num_features + 1):
            # پیدا کردن مختصات منطقه
            positions = np.where(labeled_array == i)
            if len(positions[0]) == 0:
                continue
                
            y_min, y_max = np.min(positions[0]), np.max(positions[0])
            x_min, x_max = np.min(positions[1]), np.max(positions[1])
            
            width = x_max - x_min
            height = y_max - y_min
            area = width * height
            
            # فیلتر بر اساس اندازه و نسبت ابعاد
            if (area < min_area or 
                width < min_width or 
                height < min_height or
                width > img.width * 0.9 or  # حذف مناطق خیلی بزرگ
                height > img.height * 0.9):
                continue
            
            # بررسی نسبت ابعاد (نمودارها معمولاً مربعی یا مستطیلی هستند)
            aspect_ratio = width / height
            if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                continue
            
            # استخراج منطقه با حاشیه کوچک
            margin = 5
            x_min = max(0, x_min - margin)
            y_min = max(0, y_min - margin)
            x_max = min(img.width, x_max + margin)
            y_max = min(img.height, y_max + margin)
            
            # استخراج منطقه
            chart_region = img.crop((x_min, y_min, x_max, y_max))
            
            # ذخیره با نام منحصر به فرد
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            filename = f"{base_name}_chart_{len(chart_images)+1:03d}.png"
            output_path = os.path.join(output_dir, filename)
            
            # اطمینان از کیفیت خوب
            chart_region.save(output_path, 'PNG', optimize=True, quality=95)
            chart_images.append(output_path)
            
            print(f"  نمودار پیدا شد: {filename} (سایز: {width}x{height})")
        
        return chart_images
    
    except Exception as e:
        print(f"خطا در پردازش {image_path}: {str(e)}")
        return []

def process_all_images(input_dir, output_dir, min_area=1500):
    """
    پردازش تمام تصاویر در دایرکتوری
    """
    if not os.path.exists(input_dir):
        print(f"خطا: دایرکتوری ورودی وجود ندارد: {input_dir}")
        return
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"دایرکتوری خروجی ایجاد شد: {output_dir}")
    
    # لیست تمام فایلهای تصویری
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
    image_files = [f for f in os.listdir(input_dir) 
                  if os.path.splitext(f)[1].lower() in image_extensions]
    
    if not image_files:
        print("هیچ فایل تصویری در دایرکتوری ورودی پیدا نشد")
        return
    
    print(f"تعداد تصاویر پیدا شده: {len(image_files)}")
    total_charts = 0
    
    for image_file in image_files:
        image_path = os.path.join(input_dir, image_file)
        charts = detect_charts_with_pillow(image_path, output_dir, min_area)
        total_charts += len(charts)
    
    print(f="\nنتایج پردازش:")
    print(f"تعداد کل تصاویر پردازش شده: {len(image_files)}")
    print(f"تعداد کل نمودارهای پیدا شده: {total_charts}")
    print(f"نمودارها در دایرکتوری ذخیره شدند: {output_dir}")

def analyze_image(image_path):
    """
    آنالیز تصویر برای تنظیم پارامترهای بهینه
    """
    try:
        img = Image.open(image_path)
        print(f"\nآنالیز تصویر: {os.path.basename(image_path)}")
        print(f"ابعاد تصویر: {img.width}x{img.height}")
        print(f"حالت رنگ: {img.mode}")
        
        # نمایش هیستوگرام برای تنظیم آستانه
        if img.mode != 'L':
            gray = img.convert('L')
        else:
            gray = img
        
        gray_array = np.array(gray)
        print(f"مقدار میانگین روشنایی: {np.mean(gray_array):.2f}")
        print(f"انحراف معیار روشنایی: {np.std(gray_array):.2f}")
        print(f"حداکثر روشنایی: {np.max(gray_array)}")
        print(f"حداقل روشنایی: {np.min(gray_array)}")
        
        return True
        
    except Exception as e:
        print(f"خطا در آنالیز تصویر: {str(e)}")
        return False

def main():
    """تابع اصلی"""
    parser = argparse.ArgumentParser(description='تشخیص و استخراج نمودارها از تصاویر')
    parser.add_argument('--input', '-i', required=True, help='دایرکتوری تصاویر ورودی')
    parser.add_argument('--output', '-o', required=True, help='دایرکتوری خروجی نمودارها')
    parser.add_argument('--min-area', '-a', type=int, default=1500, help='حداقل مساحت نمودار (پیکسل)')
    parser.add_argument('--analyze', action='store_true', help='آنالیز تصاویر قبل از پردازش')
    
    args = parser.parse_args()
    
    print("شروع پردازش تشخیص نمودارها...")
    print("=" * 50)
    
    if args.analyze:
        # آنالیز اولین تصویر برای تنظیم پارامترها
        image_files = [f for f in os.listdir(args.input) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
        if image_files:
            analyze_image(os.path.join(args.input, image_files[0]))
    
    # پردازش تمام تصاویر
    process_all_images(args.input, args.output, args.min_area)
    
    print("=" * 50)
    print("پردازش کامل شد!")

if __name__ == "__main__":
    # اگر می‌خواهید از آرگومان‌های خط فرمان استفاده کنید:
    # main()
    
    # یا مستقیماً مسیرها را تنظیم کنید:
    input_directory = "/var/www/html/benchain/scripts/pdf_to_text/output/WORK PSYCHOLOGY/images/pages"  # مسیر تصاویر ورودی
    output_directory = "/var/www/html/benchain/scripts/pdf_to_text/output/WORK PSYCHOLOGY/images/chartsx"  # مسیر خروجی نمودارها
    min_area_size = 1500  # حداقل مساحت نمودار
    
    print("شروع پردازش تشخیص نمودارها...")
    print("=" * 50)
    
    process_all_images(input_directory, output_directory, min_area_size)
    
    print("=" * 50)
    print("پردازش کامل شد!")