# Text Recognition System

This system extracts student results from PDF files, supporting both text-based PDFs and PDFs containing images of results.

## Features

- Supports both text-based PDFs and image-based PDFs
- Extracts student information including roll number, name, and marks
- Processes multiple pages
- Exports results to CSV format
- Calculates statistics and identifies top performers

## Prerequisites

### Windows
1. Install Python 3.8 or higher
2. Install Tesseract OCR:
   - Download the installer from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - Run the installer and note the installation path (default: `C:\Program Files\Tesseract-OCR`)
   - Add Tesseract to your system PATH
3. Install Poppler for PDF processing:
   - Download from [Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)
   - Extract to a folder (e.g., `C:\Program Files\poppler-xx`)
   - Add the `bin` directory to your system PATH

### Linux
```bash
# Install Tesseract OCR
sudo apt-get update
sudo apt-get install tesseract-ocr

# Install Poppler
sudo apt-get install poppler-utils
```

## Installation

1. Clone this repository
2. Create a virtual environment and activate it:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Place your PDF file(s) in the `data` directory
2. Run the extraction script:
```bash
python src/pdf_extractor.py
```

3. The extracted results will be saved in the `output` directory as CSV files

## File Structure

```
.
├── data/                  # Place PDF files here
├── output/               # Extracted results are saved here
├── src/
│   ├── pdf_extractor.py  # Main PDF processing script
│   └── data_processor.py # Data analysis utilities
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Troubleshooting

### OCR Issues
- Make sure Tesseract is properly installed and in your system PATH
- For Windows, set the Tesseract path in your environment variables:
  ```python
  import os
  os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'
  ```

### PDF Processing Issues
- Ensure Poppler is installed and in your system PATH
- For image-heavy PDFs, the processing might take longer
- Make sure the PDF is not password-protected

## Notes

- The system automatically detects whether a PDF contains mostly text or images
- For image-based PDFs, OCR processing is used which might be slower but handles scanned documents
- The extracted data includes:
  - Student information (roll number, name, etc.)
  - Subject-wise marks
  - Total marks and percentages
  - Performance statistics 