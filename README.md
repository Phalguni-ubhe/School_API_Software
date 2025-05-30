# Student API - Academic Performance Index Calculator

This is a Django-based application for teachers to calculate student Academic Performance Index (API) from exam results. The system can process PDF result sheets, extract data, perform calculations, and export results to Excel.

## Features (Planned)
- PDF result sheet processing
- Automatic data extraction using OCR
- Academic Performance Index calculation
- Excel report generation
- Teacher-only access control

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- (Windows only) Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki

### Installation

1. Clone this repository:
```bash
git clone [repository-url]
cd [project-directory]
```

2. Run the setup script:
```bash
python setup.py
```

3. Activate the virtual environment:
- Windows:
  ```bash
  .\venv\Scripts\activate
  ```
- Unix/Linux/MacOS:
  ```bash
  source ./venv/bin/activate
  ```

4. Run the development server:
```bash
python manage.py runserver
```

## Project Structure
```
student_api/
├── manage.py
├── setup.py              # Project setup script
├── requirements.txt      # Project dependencies
├── venv/                # Virtual environment
└── student_api/         # Main project folder
```

## Developer Notes
- The project uses Django for the web framework
- PDF processing is handled using pdf2image and pytesseract
- Data analysis and Excel export use pandas and openpyxl
- Make sure to run migrations before starting development

## Contributing
1. Create a new branch for your feature
2. Make your changes
3. Run tests (when available)
4. Submit a pull request
