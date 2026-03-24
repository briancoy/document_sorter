# **🗂️ Universal Local Document Categorizer (GUI Edition)**

An automated, entirely local, AI-powered document sorting tool. This app provides a clean graphical interface to monitor a folder, read your messy files, write a summary, and automatically sort them into categorized subfolders based on their content.

**100% Private:** Powered by Ollama, all document processing happens locally on your machine. No financial data, personal letters, or sensitive documents are ever sent to the cloud.

## **✨ Features**

* **Graphical User Interface (GUI):** No coding required\! Visually select your folders, manage custom categories, and adjust AI settings right from the app.  
* **Auto-Saving Configuration:** The app remembers your folders, custom categories, and settings between sessions.  
* **Live Console:** Watch the AI process your documents, view processing times, and monitor retries in real-time within the app.  
* **Dual-Path Engine:** \* *Vision Path:* Takes pictures of fixed-layout documents (.pdf, .jpg, .png, .tiff) and uses a Vision-Language Model (VLM) to read the layouts, ignoring visual noise.  
  * *Text Path:* Directly extracts pure text from flowable documents (.txt, .docx) for lightning-fast processing.  
* **Auto-Sorting:** Automatically copies processed files into cleanly organized category folders and moves the originals to a "Completed" directory.  
* **CSV Logging:** Generates a document\_summary.csv tracking the filename, assigned categories, a generated synopsis, processing time, and the AI model used.

## **🛠️ Prerequisites & Hardware**

Because this uses Vision-Language Models to "look" at scanned PDFs, a dedicated GPU is highly recommended.

* **RAM/VRAM:** An NVIDIA GPU with at least 8GB of VRAM is recommended (16GB+ is ideal for 8B models like qwen3-vl:8b).  
* **Ollama:** You must have Ollama (https://ollama.com/) installed and running on your system.  
* **Python:** Python 3.9+ installed.

## **🚀 Installation**

1. **Clone or Download** this repository to your local machine.  
2. **Install the required Python libraries:**  
   Open your terminal and run:  
   pip install PyMuPDF python-docx ollama  
3. **Pull a Vision-capable LLM:**  
   You must pull a model that supports vision (VLMs). We highly recommend the Qwen-VL family for OCR and document understanding. Run:  
   ollama pull qwen3-vl:8b  
   *(Note: You can also use smaller models like qwen3.5vl:4b if you have less VRAM, or larger models if you have a top-tier GPU).*

## **🏃 Usage & Configuration**

Simply launch the graphical interface by running the script:

python gui\_categorizer.py

1. **Set Your Folders:** Use the "Browse..." buttons to select your Source folder (where your messy scans go), your Output folder, and your Completed Originals folder.  
2. **Manage Categories:** Use the "Add" and "Remove" buttons to customize the exact list of categories you want the AI to use.  
3. **Select Your Model:** The dropdown will automatically fetch all the models you currently have downloaded in Ollama.  
4. **Start Sorting:** Click the big "START CATEGORIZING" button and watch the live log go to work\!

*(Pro-Tip: If you have stubborn files that return empty responses, try increasing "Max Retries" or process them in smaller batches).*

## **⚠️ Troubleshooting**

* **ModuleNotFoundError: No module named 'frontend'**  
  You accidentally installed the wrong fitz package. Run pip uninstall fitz and then pip install PyMuPDF.  
* **Error: AI returned empty response**  
  The LLM occasionally freezes on complex layouts or blank pages. The app will automatically retry based on your "Max Retries" setting. If it exhausts all retries, it safely logs it as "Misc" so your batch isn't interrupted.  
* **Out of Memory (OOM) Error**  
  Your GPU ran out of VRAM. Try lowering the "Render DPI" to 100 or lowering "Max Pages to Scan" to 3\. Alternatively, switch to a smaller model in Ollama.

## **License**

MIT License. Free to use, modify, and distribute\!