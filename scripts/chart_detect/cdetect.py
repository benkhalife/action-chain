import cv2
import numpy as np
import os
from sklearn.cluster import KMeans

def detect_charts_in_image(image_path, output_dir, min_contour_area=1000):
    """
    تشخیص نمودارها در یک تصویر و ذخیره آنها
    """
    # خواندن تصویر
    img = cv2.imread(image_path)
    if img is None:
        print(f"خطا در خواندن تصویر: {image_path}")
        return []
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # اعمال فیلترها برای بهبود تشخیص
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # پیدا کردن کانتورها
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    chart_images = []
    
    for i, contour in enumerate(contours):
        # فیلتر بر اساس مساحت
        area = cv2.contourArea(contour)
        if area < min_contour_area:
            continue
        
        # گرفتن مستطیل محدود کننده
        x, y, w, h = cv2.boundingRect(contour)
        
        # استخراج ناحیه نمودار
        chart_region = img[y:y+h, x:x+w]
        
        # ذخیره نمودار
        filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_chart_{i}.png"
        output_path = os.path.join(output_dir, filename)
        cv2.imwrite(output_path, chart_region)
        chart_images.append(output_path)
    
    return chart_images

def process_all_images(input_dir, output_dir):
    """
    پردازش تمام تصاویر در دایرکتوری
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # لیست تمام فایلهای تصویری
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    image_files = [f for f in os.listdir(input_dir) 
                  if os.path.splitext(f)[1].lower() in image_extensions]
    
    total_charts = 0
    
    for image_file in image_files:
        image_path = os.path.join(input_dir, image_file)
        print(f"پردازش: {image_file}")
        
        charts = detect_charts_in_image(image_path, output_dir)
        total_charts += len(charts)
        print(f"  {len(charts)} نمودار پیدا شد")
    
    print(f"در مجموع {total_charts} نمودار ذخیره شد")

# اجرای کد
if __name__ == "__main__":
    input_directory = "/var/www/html/benchain/scripts/pdf_to_text/output/WORK PSYCHOLOGY/images/pages"  # مسیر تصاویر ورودی
    output_directory = "/var/www/html/benchain/scripts/pdf_to_text/output/WORK PSYCHOLOGY/images/charts"  # مسیر خروجی نمودارها
    
    process_all_images(input_directory, output_directory)