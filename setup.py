import subprocess
import sys
import os
from pathlib import Path

def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {str(e)}")
        sys.exit(1)

def get_python():
    """Get the path to Python executable"""
    return sys.executable

def check_requirements():
    """Check and install system requirements"""
    print("\nChecking system requirements...")
    
    # Check for Tesseract OCR
    print("Checking for Tesseract OCR (required for PDF processing)...")
    
    try:
        # First ensure numpy is properly installed
        run_command(f'"{get_python()}" -m pip install --upgrade numpy')
        run_command(f'"{get_python()}" -m pip install --upgrade pillow pytesseract')
        
        # Now check Tesseract
        result = subprocess.run(
            [get_python(), "-c", "import pytesseract; print(pytesseract.get_tesseract_version())"], 
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Tesseract OCR is installed and working")
            return True
    except Exception:
        pass
    
    print("\n⚠ Tesseract OCR is not properly configured. Please follow these steps:")
    print("\n1. Download Tesseract OCR installer:")
    print("   For Windows 64-bit: https://github.com/UB-Mannheim/tesseract/wiki")
    print("\n2. Run the installer and remember the installation path")
    print("   Recommended path: C:\\Program Files\\Tesseract-OCR")
    print("\n3. Add Tesseract to your system PATH:")
    print("   - Open Windows Settings")
    print("   - Search for 'Environment Variables'")
    print("   - Edit the PATH variable")
    print("   - Add the Tesseract installation directory")
    print("\nOr press Ctrl+C to cancel setup and install Tesseract first")
    input("\nPress Enter to continue anyway (if you plan to install Tesseract later)...")
    return False

def install_packages():
    """Install Python packages with proper error handling"""
    try:
        python = get_python()
        # Upgrade pip first
        run_command(f'"{python}" -m pip install --upgrade pip wheel setuptools')
        
        # Install PostgreSQL dependencies
        print("Installing PostgreSQL dependencies...")
        run_command(f'"{python}" -m pip install psycopg2-binary')
        
        # Read requirements file
        with open('requirements.txt', 'r') as f:
            requirements = [line.strip() for line in f 
                          if line.strip() and not line.startswith('#')]
        
        # Install packages one by one
        for req in requirements:
            try:
                if req.startswith('psycopg2'):
                    continue  # Skip as we already installed this
                print(f"Installing {req}...")
                run_command(f'"{python}" -m pip install {req}')
            except Exception as e:
                print(f"Warning: Failed to install {req}: {str(e)}")
                print("Continuing with remaining packages...")
        
    except Exception as e:
        print(f"Error during package installation: {str(e)}")
        print("Please try installing packages manually after setup.")
        return False
    return True

def main():
    print("Installing required packages for Student API project...")
    
    # Install required packages
    print("\nInstalling packages...")
    if not install_packages():
        print("\nContinuing despite package installation issues...")
    
    # Check system requirements
    check_requirements()
    
    print("\nSetup completed!")
    print("\nTo start development:")
    print("Run the development server: python manage.py runserver")
    print("\nAdditional Notes:")
    print("- Make sure Tesseract OCR is installed for PDF processing")
    print("- Check README.md for more details about the project")
    print("- The application will be available at http://127.0.0.1:8000/")

if __name__ == "__main__":
    main()
