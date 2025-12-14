# Manga to Kindle

A Python tool to scrape manga chapters from websites and compile them into Kindle-ready PDF ebooks (Originally built to scrape Tokyo-Ghoul).

## Features

- **Web Scraping** - Selenium-based scraping handles JavaScript-rendered manga sites
- **Batch Download** - Download all chapters (1-145+) automatically
- **Resume Support** - Chapter-by-chapter mode lets you resume interrupted downloads
- **PDF Compilation** - Combines all chapters into a single PDF in reading order
- **Kindle Optimization** - Automatic PDF splitting to stay under Kindle's 200MB limit
- **Progress Tracking** - Real-time progress bars with tqdm

## Requirements

- Python 3.8+
- Google Chrome browser (for Selenium)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ayeshkadike/manga-to-kindle.git
   cd manga-to-kindle
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage:

### Download & Compile Manga

```bash
python main.py
```

You'll be prompted to select a mode:
- **Mode 1**: Direct compilation - Downloads all images to memory, then creates PDF (faster, uses more RAM)
- **Mode 2**: Chapter-by-chapter - Creates individual chapter PDFs, then merges (resumable, recommended)
- **Mode 3**: Debug mode - Inspect a chapter's HTML structure for troubleshooting

### Split Large PDFs for Kindle

If your compiled PDF exceeds Kindle's 200MB limit:

```bash
python compress.py
```

This will split the PDF into multiple parts, each under 200MB while preserving original quality.

**Custom usage:**
```bash
python compress.py input.pdf output_prefix 200
```

## Configuration

Edit the configuration variables in `main.py`:

```python
BASE_URL = "https://example.com/manga/series-chapter-{chapter}/"
START_CHAPTER = 1
END_CHAPTER = 145
OUTPUT_PDF = "Manga_Complete.pdf"
```

## Project Structure

```
manga-to-kindle/
├── main.py           # Main scraper and PDF compiler
├── compress.py       # PDF splitter for Kindle size limits
├── requirements.txt  # Python dependencies
├── chapter_pdfs/     # Individual chapter PDFs (created during download)
└── README.md
```

## How It Works

1. **Scraping**: Uses Selenium WebDriver to load manga pages and extract image URLs
2. **Detection**: Identifies manga images via `alt` attributes and URL patterns
3. **Downloading**: Downloads images with retry logic and rate limiting
4. **Compilation**: Combines images into PDF format using Pillow
5. **Splitting**: Divides large PDFs by chapter boundaries to meet size limits

## To Customize for Other Manga Sites

To adapt for a different manga website:

1. Update `BASE_URL` with the site's chapter URL pattern
2. Modify the image detection logic in `get_chapter_images()` if needed:
   - Check `alt` text patterns
   - Update URL filters for the site's image hosting

## Disclaimer

This tool is for personal use only. Please respect copyright laws and the terms of service of manga websites. Support official releases when available.

## Contributing

Contributions are welcome! Feel free to submit issues and pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.
