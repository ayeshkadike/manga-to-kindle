"""
This is the PDF Splitter Script originally built for splitting the Tokyo Ghoul manga PDF into Kindle-friendly parts.
Splits large PDFs into smaller parts for Kindle (max 200MB each).
"""

import os
import sys
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from tqdm import tqdm


def get_file_size_mb(path):
    """Get file size in MB."""
    return os.path.getsize(path) / (1024 * 1024)


def split_pdf_by_size(input_path, output_prefix, max_size_mb=200):
    """
    Split a PDF into multiple parts, each under max_size_mb.
    """
    print(f"Opening: {input_path}")
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    original_size = get_file_size_mb(input_path)
    
    print(f"Total pages: {total_pages}")
    print(f"Original size: {original_size:.2f} MB")
    print(f"Target max size per part: {max_size_mb} MB")
    
    # Estimate pages per part based on file size
    num_parts = max(2, int(original_size / max_size_mb) + 1)
    pages_per_part = total_pages // num_parts
    
    print(f"Splitting into ~{num_parts} parts ({pages_per_part} pages each)")
    print("=" * 50)
    
    parts = []
    current_part = 1
    start_page = 0
    
    while start_page < total_pages:
        end_page = min(start_page + pages_per_part, total_pages)
        
        # For the last part, include all remaining pages
        if total_pages - end_page < pages_per_part // 2:
            end_page = total_pages
        
        output_path = f"{output_prefix}_Part{current_part}.pdf"
        
        print(f"\nCreating Part {current_part}: pages {start_page + 1} to {end_page}")
        
        writer = PdfWriter()
        for page_num in tqdm(range(start_page, end_page), desc=f"Part {current_part}"):
            writer.add_page(reader.pages[page_num])
        
        with open(output_path, "wb") as f:
            writer.write(f)
        
        size = get_file_size_mb(output_path)
        print(f"  Saved: {output_path} ({size:.2f} MB)")
        
        parts.append((output_path, size))
        
        start_page = end_page
        current_part += 1
    
    return parts


def split_from_chapters(chapter_dir, output_prefix, max_size_mb=200):
    """
    Split by combining chapter PDFs into parts, each under max_size_mb.
    This preserves original quality.
    """
    # Get all chapter PDFs
    chapter_files = sorted([
        os.path.join(chapter_dir, f) 
        for f in os.listdir(chapter_dir) 
        if f.endswith('.pdf')
    ])
    
    if not chapter_files:
        print(f"No PDF files found in {chapter_dir}")
        return []
    
    print(f"Found {len(chapter_files)} chapter PDFs")
    
    # Calculate total size and estimate parts needed
    total_size = sum(get_file_size_mb(f) for f in chapter_files)
    num_parts = max(2, int(total_size / max_size_mb) + 1)
    target_size_per_part = total_size / num_parts
    
    print(f"Total size: {total_size:.2f} MB")
    print(f"Target: {num_parts} parts, ~{target_size_per_part:.0f} MB each")
    print("=" * 50)
    
    parts = []
    current_part = 1
    current_merger = PdfMerger()
    current_size = 0
    chapters_in_part = []
    
    for chapter_path in tqdm(chapter_files, desc="Processing chapters"):
        chapter_size = get_file_size_mb(chapter_path)
        chapter_num = os.path.basename(chapter_path).replace("chapter_", "").replace(".pdf", "")
        
        # Check if adding this chapter would exceed the limit
        if current_size + chapter_size > max_size_mb and current_size > 0:
            # Save current part
            output_path = f"{output_prefix}_Part{current_part}.pdf"
            current_merger.write(output_path)
            current_merger.close()
            
            part_size = get_file_size_mb(output_path)
            print(f"\n  Part {current_part}: Chapters {chapters_in_part[0]}-{chapters_in_part[-1]} ({part_size:.2f} MB)")
            parts.append((output_path, part_size, chapters_in_part[0], chapters_in_part[-1]))
            
            # Start new part
            current_part += 1
            current_merger = PdfMerger()
            current_size = 0
            chapters_in_part = []
        
        current_merger.append(chapter_path)
        current_size += chapter_size
        chapters_in_part.append(chapter_num)
    
    # Save final part
    if chapters_in_part:
        output_path = f"{output_prefix}_Part{current_part}.pdf"
        current_merger.write(output_path)
        current_merger.close()
        
        part_size = get_file_size_mb(output_path)
        print(f"\n  Part {current_part}: Chapters {chapters_in_part[0]}-{chapters_in_part[-1]} ({part_size:.2f} MB)")
        parts.append((output_path, part_size, chapters_in_part[0], chapters_in_part[-1]))
    
    return parts


def split_pdf(input_path=None, output_prefix="Tokyo_Ghoul", max_size_mb=200):
    """Main function to split PDF into parts."""
    
    chapter_dir = "chapter_pdfs"
    
    print("\n" + "=" * 50)
    print("PDF Splitter - Preserving Original Quality")
    print("=" * 50)
    
    # Prefer splitting from chapters (preserves quality)
    if os.path.exists(chapter_dir) and os.listdir(chapter_dir):
        print(f"\nUsing chapter PDFs from: {chapter_dir}")
        parts = split_from_chapters(chapter_dir, output_prefix, max_size_mb)
    elif input_path and os.path.exists(input_path):
        print(f"\nSplitting from: {input_path}")
        parts = split_pdf_by_size(input_path, output_prefix, max_size_mb)
    else:
        print("Error: No chapter_pdfs directory or input PDF found")
        return
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    total_size = 0
    for i, part_info in enumerate(parts, 1):
        if len(part_info) == 4:
            path, size, start_ch, end_ch = part_info
            print(f"  Part {i}: {path}")
            print(f"          Chapters {start_ch}-{end_ch}, Size: {size:.2f} MB")
        else:
            path, size = part_info
            print(f"  Part {i}: {path} ({size:.2f} MB)")
        total_size += size
    
    print(f"\n  Total: {len(parts)} parts, {total_size:.2f} MB")
    print("=" * 50)


if __name__ == "__main__":
    input_pdf = "Tokyo_Ghoul_Complete.pdf"
    output_prefix = "Tokyo_Ghoul"
    max_mb = 200
    
    if len(sys.argv) > 1:
        input_pdf = sys.argv[1]
    if len(sys.argv) > 2:
        output_prefix = sys.argv[2]
    if len(sys.argv) > 3:
        max_mb = int(sys.argv[3])
    
    split_pdf(input_pdf, output_prefix, max_mb)
