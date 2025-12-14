"""
Welcome to the Tokyo Ghoul Manga Compiler
Scrapes all images from chapters 1-145 and compiles them into a single PDF.
Uses Selenium to handle JavaScript-rendered content.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
BASE_URL = "https://tgmanga.com/manga/tokyo-ghoul-chapter-{chapter}/"
OUTPUT_DIR = "manga_images"
OUTPUT_PDF = "Tokyo_Ghoul_Complete.pdf"
START_CHAPTER = 1
END_CHAPTER = 145

# Request headers to mimic browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://tgmanga.com/",
}


def create_driver():
    """Create a Selenium WebDriver with appropriate options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    
    # Disable images loading in browser to speed up (we'll download them separately)
    prefs = {
        "profile.managed_default_content_settings.images": 1,  # 1=allow, 2=block
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver


def create_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def get_chapter_images(driver, chapter_num, max_retries=3):
    """
    Fetch a chapter page using Selenium and extract all image URLs.
    Returns a list of image URLs in order.
    """
    url = BASE_URL.format(chapter=chapter_num)
    
    for attempt in range(max_retries):
        try:
            driver.get(url)
            
            # Wait for the page to load - give time for lazy-loaded images
            time.sleep(3)
            
            # Scroll down to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            images = []
            
            # Strategy 1: Look for images with Tokyo Ghoul in alt text (most reliable)
            all_imgs = soup.find_all("img")
            
            for img in all_imgs:
                alt = img.get("alt", "").lower()
                
                # Check if alt text indicates it's a manga page
                # Handle various formats: "Tokyo Ghoul, Chapter X - IMAGE Y", ".tokyo ghoul chapter", etc.
                if "tokyo ghoul" in alt or "tokyoghoul" in alt:
                    src = (
                        img.get("src") or 
                        img.get("data-src") or 
                        img.get("data-lazy-src") or
                        img.get("data-original")
                    )
                    
                    if src and src.strip():
                        # Skip donation/external images
                        if "ko-fi" in src.lower() or "storage.ko-fi" in src.lower():
                            continue
                        
                        # Clean up URL
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = "https://tgmanga.com" + src
                        
                        # Skip non-image URLs
                        if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                            images.append(src)
            
            # Strategy 2: If alt-based search failed, look for images with specific URL patterns
            if not images:
                for img in all_imgs:
                    src = (
                        img.get("src") or 
                        img.get("data-src") or 
                        img.get("data-lazy-src") or
                        img.get("data-original")
                    )
                    
                    if not src:
                        continue
                    
                    src_lower = src.lower()
                    
                    # Check if it's a manga image by URL patterns
                    if any(pattern in src_lower for pattern in [
                        "tokyo-ghoul", "tokyo_ghoul", "tokyoghoul",
                        "wp-content/uploads"
                    ]):
                        # Skip thumbnails, icons, and donation images
                        if any(skip in src_lower for skip in [
                            "thumb", "icon", "logo", "avatar", "150x", "300x",
                            "ko-fi", "storage.ko-fi", "donation"
                        ]):
                            continue
                        
                        # Clean up URL
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = "https://tgmanga.com" + src
                        
                        if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                            images.append(src)
            
            # Strategy 3: Look in specific containers like entry-content
            if not images:
                containers = soup.find_all("div", class_=re.compile(
                    r"reading-content|chapter-content|entry-content|manga-content",
                    re.IGNORECASE
                ))
                
                for container in containers:
                    for img in container.find_all("img"):
                        src = (
                            img.get("src") or 
                            img.get("data-src") or 
                            img.get("data-lazy-src")
                        )
                        if src and src not in images:
                            # Skip donation images
                            if "ko-fi" in src.lower():
                                continue
                            
                            if src.startswith("//"):
                                src = "https:" + src
                            elif src.startswith("/"):
                                src = "https://tgmanga.com" + src
                            
                            if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                                images.append(src)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for img_url in images:
                # Normalize URL for comparison
                normalized = img_url.split("?")[0]  # Remove query params
                if normalized not in seen and img_url.strip():
                    seen.add(normalized)
                    unique_images.append(img_url)
            
            return unique_images
            
        except Exception as e:
            print(f"  Attempt {attempt + 1}/{max_retries} failed for chapter {chapter_num}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return []


def download_image(session, url, max_retries=3):
    """Download an image and return as PIL Image object."""
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary (required for PDF)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")
            
            return img
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
    
    return None


def save_images_to_pdf(images, output_path):
    """Save a list of PIL Images to a PDF file."""
    if not images:
        print("No images to save!")
        return False
    
    # First image
    first_image = images[0]
    
    # Remaining images
    remaining_images = images[1:] if len(images) > 1 else []
    
    # Save to PDF
    first_image.save(
        output_path,
        "PDF",
        save_all=True,
        append_images=remaining_images,
        resolution=100.0
    )
    
    return True


def create_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def compile_manga():
    """Main function to compile all chapters into a PDF using Selenium."""
    print("=" * 60)
    print("Tokyo Ghoul Manga Compiler (Selenium Mode)")
    print(f"Chapters: {START_CHAPTER} - {END_CHAPTER}")
    print("=" * 60)
    
    print("\nInitializing browser...")
    driver = create_driver()
    session = create_session()
    all_images = []
    failed_chapters = []
    
    try:
        # Step 1: Collect all image URLs from all chapters
        print("\n[Step 1/3] Collecting image URLs from all chapters...")
        
        chapter_image_urls = {}
        
        for chapter in tqdm(range(START_CHAPTER, END_CHAPTER + 1), desc="Scanning chapters"):
            image_urls = get_chapter_images(driver, chapter)
            
            if image_urls:
                chapter_image_urls[chapter] = image_urls
                tqdm.write(f"  Chapter {chapter}: Found {len(image_urls)} images")
            else:
                failed_chapters.append(chapter)
                tqdm.write(f"  Chapter {chapter}: No images found (will retry)")
            
            # Be polite to the server lol (Be kind to server == Server kind to you!!)
            time.sleep(0.5)
        
        # Retry any failed chapters with longer wait
        if failed_chapters:
            print(f"\nRetrying {len(failed_chapters)} failed chapters...")
            for chapter in failed_chapters[:]:
                time.sleep(3)
                image_urls = get_chapter_images(driver, chapter)
                if image_urls:
                    chapter_image_urls[chapter] = image_urls
                    failed_chapters.remove(chapter)
                    print(f"  Chapter {chapter}: Found {len(image_urls)} images (retry successful)")
        
        if failed_chapters:
            print(f"\nWarning: Could not fetch chapters: {failed_chapters}")
        
        # Calculate total images
        total_images = sum(len(urls) for urls in chapter_image_urls.values())
        print(f"\nTotal images to download: {total_images}")
        
        # Step 2: Download all images in order
        print("\n[Step 2/3] Downloading images...")
        
        for chapter in tqdm(range(START_CHAPTER, END_CHAPTER + 1), desc="Downloading chapters"):
            if chapter not in chapter_image_urls:
                continue
            
            urls = chapter_image_urls[chapter]
            chapter_images = []
            
            for idx, url in enumerate(urls):
                img = download_image(session, url)
                if img:
                    chapter_images.append(img)
                else:
                    tqdm.write(f"  Failed to download: Chapter {chapter}, Image {idx + 1}")
                
                # Small delay between images
                time.sleep(0.2)
            
            all_images.extend(chapter_images)
            tqdm.write(f"  Chapter {chapter}: Downloaded {len(chapter_images)}/{len(urls)} images")
        
        print(f"\nTotal images downloaded: {len(all_images)}")
        
        # Step 3: Compile into PDF
        print("\n[Step 3/3] Compiling PDF...")
        
        if all_images:
            print(f"Creating PDF with {len(all_images)} pages...")
            
            # For very large PDFs, batch them
            if len(all_images) > 500:
                batch_size = 200
                temp_pdfs = []
                
                for i in range(0, len(all_images), batch_size):
                    batch = all_images[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    temp_pdf = f"temp_batch_{batch_num}.pdf"
                    
                    print(f"  Saving batch {batch_num} ({len(batch)} images)...")
                    save_images_to_pdf(batch, temp_pdf)
                    temp_pdfs.append(temp_pdf)
                
                print("  Merging all batches...")
                merge_pdfs(temp_pdfs, OUTPUT_PDF)
                
                for temp_pdf in temp_pdfs:
                    if os.path.exists(temp_pdf):
                        os.remove(temp_pdf)
            else:
                save_images_to_pdf(all_images, OUTPUT_PDF)
            
            print(f"\n{'=' * 60}")
            print(f"SUCCESS! PDF saved as: {OUTPUT_PDF}")
            print(f"Total pages: {len(all_images)}")
            print(f"File size: {os.path.getsize(OUTPUT_PDF) / (1024*1024):.2f} MB")
            print(f"{'=' * 60}")
        else:
            print("No images were downloaded. Please check the URLs and try again.")
    
    finally:
        driver.quit()


def merge_pdfs(pdf_list, output_path):
    """Merge multiple PDFs into one."""
    from PyPDF2 import PdfMerger
    
    merger = PdfMerger()
    
    for pdf in pdf_list:
        merger.append(pdf)
    
    merger.write(output_path)
    merger.close()


def compile_manga_to_separate_pdfs():
    """
    Alternative approach: Create one PDF per chapter, then merge.
    Useful if you want to resume from a specific chapter.
    """
    print("=" * 60)
    print("Tokyo Ghoul Manga Compiler (Chapter-by-Chapter Mode)")
    print(f"Chapters: {START_CHAPTER} - {END_CHAPTER}")
    print("=" * 60)
    
    print("\nInitializing browser...")
    driver = create_driver()
    session = create_session()
    chapter_pdfs = []
    
    # Create output directory for chapter PDFs where we store the intermittent chapter by chapter PDFs
    chapter_pdf_dir = "chapter_pdfs"
    os.makedirs(chapter_pdf_dir, exist_ok=True)
    
    try:
        for chapter in range(START_CHAPTER, END_CHAPTER + 1):
            chapter_pdf_path = os.path.join(chapter_pdf_dir, f"chapter_{chapter:03d}.pdf")
            
            # Skip if it already exists (for resumptions)
            if os.path.exists(chapter_pdf_path):
                print(f"Chapter {chapter}: Already exists, skipping...")
                chapter_pdfs.append(chapter_pdf_path)
                continue
            
            print(f"\nProcessing Chapter {chapter}...")
            
            # Get image URLs using Selenium
            image_urls = get_chapter_images(driver, chapter)
            
            if not image_urls:
                print(f"  No images found for chapter {chapter}")
                continue
            
            print(f"  Found {len(image_urls)} images")
            
            # Download the images
            chapter_images = []
            for idx, url in enumerate(image_urls):
                img = download_image(session, url)
                if img:
                    chapter_images.append(img)
                    print(f"  Downloaded image {idx + 1}/{len(image_urls)}", end="\r")
                time.sleep(0.2)
            
            print(f"  Downloaded {len(chapter_images)} images" + " " * 20)
            
            # Save chapter PDF
            if chapter_images:
                save_images_to_pdf(chapter_images, chapter_pdf_path)
                chapter_pdfs.append(chapter_pdf_path)
                print(f"  Saved: {chapter_pdf_path}")
            
            # Be nice to the server lol
            time.sleep(1)
        
        # Merge all chapter PDFs
        print("\n" + "=" * 60)
        print("Merging all chapters into final PDF...")
        
        if chapter_pdfs:
            merge_pdfs(chapter_pdfs, OUTPUT_PDF)
            print(f"\nSUCCESS! Final PDF saved as: {OUTPUT_PDF}")
            print(f"File size: {os.path.getsize(OUTPUT_PDF) / (1024*1024):.2f} MB")
        else:
            print("No chapter PDFs were created!")
    
    finally:
        driver.quit()


def debug_chapter(chapter_num):
    """Debug function to inspect a specific chapter's HTML structure."""
    print(f"\n{'=' * 60}")
    print(f"Debugging Chapter {chapter_num}")
    print("=" * 60)
    
    driver = create_driver()
    
    try:
        url = BASE_URL.format(chapter=chapter_num)
        print(f"URL: {url}")
        
        driver.get(url)
        time.sleep(5)
        
        # Scroll so that we load any lazy images if pressent
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        
        # Get the page source
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Finding all images on page
        all_imgs = soup.find_all("img")
        print(f"\nFound {len(all_imgs)} total <img> tags")
        
        print("\nImage sources found:")
        for i, img in enumerate(all_imgs[:30]):  # Show first 30
            src = img.get("src", "")
            data_src = img.get("data-src", "")
            data_lazy = img.get("data-lazy-src", "")
            alt = img.get("alt", "")[:50]
            
            if src or data_src or data_lazy:
                print(f"\n  [{i+1}]")
                if src:
                    print(f"    src: {src[:100]}")
                if data_src:
                    print(f"    data-src: {data_src[:100]}")
                if data_lazy:
                    print(f"    data-lazy-src: {data_lazy[:100]}")
                if alt:
                    print(f"    alt: {alt}")
        
        # We look for any specific containers
        print("\n\nLooking for manga reader containers:")
        containers = [
            "reading-content", "chapter-content", "entry-content",
            "manga-content", "page-break", "wp-manga-chapter-img"
        ]
        
        for container_class in containers:
            elements = soup.find_all(class_=re.compile(container_class, re.IGNORECASE))
            if elements:
                print(f"\n  Found {len(elements)} elements with class containing '{container_class}'")
                for el in elements[:3]:
                    imgs = el.find_all("img")
                    print(f"    - Contains {len(imgs)} images")
        
        # Save HTML for manual inspection
        debug_file = f"debug_chapter_{chapter_num}.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"\nFull HTML saved to: {debug_file}")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    import sys
    
    print("\nSelect mode:")
    print("1. Direct compilation (downloads all, then creates PDF)")
    print("2. Chapter-by-chapter (resumable, creates individual PDFs first)")
    print("3. Debug mode (inspect a specific chapter's HTML)")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == "2":
        compile_manga_to_separate_pdfs()
    elif choice == "3":
        chapter = input("Enter chapter number to debug: ").strip()
        debug_chapter(int(chapter))
    else:
        compile_manga()
