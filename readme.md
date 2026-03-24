# **🗂️ Universal Local Document Categorizer (AI-Powered)**

An automated, entirely local, AI-powered document sorting tool. This script monitors a folder, reads your messy files, writes a summary, and automatically sorts them into categorized subfolders based on their content.

**100% Private:** Powered by [Ollama](https://ollama.com/), all document processing happens locally on your machine. No financial data, personal letters, or sensitive documents are ever sent to the cloud.

## **✨ Features**

* **Dual-Path Engine:** \* **Vision Path:** Takes pictures of fixed-layout documents (.pdf, .jpg, .png, .tiff) and uses a Vision-Language Model (VLM) to read the layouts, ignoring visual noise like magazine ads.  
  * **Text Path:** Directly extracts pure text from flowable documents (.txt, .docx) for lightning-fast processing.  
* **Auto-Sorting:** Automatically copies processed files into cleanly organized category folders and moves the originals to a "Completed" directory.  
* **CSV Logging:** Generates a document\_summary.csv tracking the filename, assigned categories, a generated synopsis, processing time, and the AI model used.  
* **Built for Real-World Scanners:** Includes file-lock detection (so it doesn't crash if your scanner is still saving a file) and a customizable retry loop for stubborn documents.  
* **VRAM Efficient:** Automatically converts high-res PDFs to grayscale and limits page scans to prevent Out-Of-Memory (OOM) crashes on standard consumer GPUs.

## **🛠️ Prerequisites & Hardware**

Because this uses Vision-Language Models to "look" at scanned PDFs, a dedicated GPU is highly recommended.

* **RAM/VRAM:** An NVIDIA GPU with at least 8GB of VRAM is recommended (16GB+ is ideal for 8B models like qwen3-vl:8b).  
* **Ollama:** You must have [Ollama](https://ollama.com/) installed and running on your system.  
* **Python:** Python 3.9+ installed.

## **🚀 Installation**

1. **Clone or Download** this repository to your local machine.  
2. **Install the required Python libraries:**

pip install PyMuPDF python-docx ollama

3. **Pull a Vision-capable LLM:**  
   You must pull a model that supports vision (VLMs). We highly recommend the Qwen-VL family for OCR and document understanding.  
   Open your terminal and run:

ollama pull qwen3-vl:8b

*(Note: You can also use smaller models like qwen3.5vl:4b if you have less VRAM, or larger models if you have a top-tier GPU).*

## **⚙️ Configuration**

Open universal\_categorizer.py in your favorite text editor. At the top of the file, you can easily customize the behavior of the script:

### **1\. Set Your Folders**

Adjust the input and output directories. You can use local paths or network drives.

INPUT\_DIR \= r"./docs\_to\_sort"  
BASE\_OUTPUT\_DIR \= r"./categorized\_documents"  
COMPLETED\_DIR \= r"./completed\_originals"

### **2\. Customize Your Categories**

Change the ALLOWED\_CATEGORIES list to fit your life or business. The AI will strictly stick to this list.

ALLOWED\_CATEGORIES \= \[  
    "Invoices", "Tax Documents", "Medical Records",   
    "Creative Writing", "Receipts", "Misc"  
\]

### **3\. Tweak Performance & Reliability**

If you run out of VRAM, lower MAX\_PAGES\_TO\_SCAN or drop the RENDER\_DPI. If you have stubborn files that return empty responses, increase MAX\_RETRIES (tip: running stubborn files in smaller batches also helps).

ACTIVE\_MODEL \= "qwen3-vl:8b" \# Change if you downloaded a different model  
MAX\_PAGES\_TO\_SCAN \= 8        \# How many pages of a PDF to "look" at  
RENDER\_DPI \= 120             \# Image quality sent to the AI  
MAX\_RETRIES \= 3              \# Increase if the AI struggles with complex layouts

## **🏃 Usage**

Simply drop your messy documents into the INPUT\_DIR (e.g., ./docs\_to\_sort) and run the script:

python universal\_categorizer.py

The console will display real-time progress, letting you know which files are being processed, any retry attempts, and where they were sorted. Once complete, check your output folders and the document\_summary.csv file\!

## **⚠️ Troubleshooting**

* **ModuleNotFoundError: No module named 'frontend'**: You installed the wrong fitz package. Run pip uninstall fitz and then pip install PyMuPDF.  
* **Error: AI returned empty response**: The LLM occasionally freezes on complex layouts or blank pages. The script will automatically retry based on your MAX\_RETRIES setting. If it exhausts all retries, it safely logs it as "Misc" so your batch process isn't interrupted.  
* **Out of Memory (OOM) Error**: Your GPU ran out of VRAM. Try lowering the RENDER\_DPI to 100 or lowering MAX\_PAGES\_TO\_SCAN to 3\. Alternatively, switch to a smaller model in Ollama.

## **License**

MIT License. Free to use, modify, and distribute\!