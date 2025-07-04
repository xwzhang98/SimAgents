import os
import sys
from pathlib import Path
import json
from datetime import datetime
from baseline import *
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

def read_pdf_content(pdf_path):
    """Read content from PDF file."""
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        return content
    except ImportError:
        print("PyPDF2 not installed. Install with: pip install PyPDF2")
        # Fallback to sample content
        return """
        Sample paper content for testing.
        Cosmological parameters: Ωm = 0.3, h = 0.7
        Simulation: Box size 100 Mpc/h, 256^3 particles
        """


manual_path = "data/MP_Gadget_User_Guide.pdf"
paper_content = read_pdf_content(pdf_path)