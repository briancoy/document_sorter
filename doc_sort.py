import os
import shutil
import json
import csv
import time
import fitz  # PyMuPDF for PDFs and Images
import docx  # For Word Documents
import ollama

# --- Configuration ---
INPUT_DIR = r"./docs_to_sort"
BASE_OUTPUT_DIR = r"./categorized_documents"
COMPLETED_DIR = r"./completed_originals"
SUMMARY_FILE = r"./document_summary.csv"

# The LLM model to use
ACTIVE_MODEL = "qwen3-vl:8b"

# Processing Limits
MAX_PAGES_TO_SCAN = 8
RENDER_DPI = 120

# How many times the LLM will try to process the file before giving up
MAX_RETRIES = 3

ALLOWED_CATEGORIES = [
    "Debts",
    "General Financial",
    "Personal",
    "Hobbies",
    "Writings or Fiction",
    "Fitness and Health",
    "Food and Recipes",
    "Programming and Data Science",
    "Personal Improvement",
    "Misc",
]

# Supported file extensions for the open-source app
VISION_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif")
TEXT_EXTENSIONS = (".txt", ".docx")


def setup_directories():
    """Ensure all required directories exist."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(COMPLETED_DIR, exist_ok=True)
    for category in ALLOWED_CATEGORIES:
        os.makedirs(os.path.join(BASE_OUTPUT_DIR, category), exist_ok=True)


def is_file_locked(filepath):
    """Check if a file is still being copied or saved."""
    try:
        os.rename(filepath, filepath)
        return False
    except OSError:
        return True


def extract_text(file_path, filename):
    """Extracts raw text from .txt and .docx files."""
    try:
        if filename.lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif filename.lower().endswith(".docx"):
            doc = docx.Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        print(f"Error reading text from {filename}: {e}")
        return ""


def process_document(file_path, filename):
    """The Dual-Path Engine: Routes the file based on its extension."""
    try:
        is_vision = filename.lower().endswith(VISION_EXTENSIONS)
        is_text = filename.lower().endswith(TEXT_EXTENSIONS)

        image_list = []
        document_text = ""

        # --- PATH 1: The Vision Engine (PDFs, Images) ---
        if is_vision:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            pages_to_process = min(total_pages, MAX_PAGES_TO_SCAN)
            print(f"Rendering {pages_to_process} page(s) from {filename}...")

            for page_num in range(pages_to_process):
                page = doc.load_page(page_num)
                # Grayscale to strip visual noise
                pix = page.get_pixmap(dpi=RENDER_DPI, colorspace=fitz.csGRAY)
                image_list.append(pix.tobytes("jpg"))
            doc.close()

        # --- PATH 2: The Text Engine (TXT, DOCX) ---
        elif is_text:
            print(f"Extracting raw text from {filename}...")
            document_text = extract_text(file_path, filename)
            # Truncate text to prevent exploding the LLM's context window (approx 5-6 pages)
            document_text = document_text[:15000]

        else:
            return {
                "categories": ["Misc"],
                "synopsis": "Unsupported file format.",
                "time": 0,
            }

        # --- Unified Prompting ---
        # Formatted to avoid IDE string-highlighting bugs
        allowed_cats_str = ", ".join(ALLOWED_CATEGORIES)
        system_prompt = (
            f"Analyze this document carefully.\n"
            f"1. Write a short 2-3 sentence synopsis summarizing the overall contents.\n"
            f"2. Select ONE OR MORE categories from this exact list: {allowed_cats_str}.\n\n"
            f"You must respond ONLY with valid JSON.\n"
            f"Format:\n{{\n"
            f'    "categories": ["Selected Category 1", "Selected Category 2"],\n'
            f'    "synopsis": "A brief summary here."\n'
            f"}}\n"
        )

        # If it's a text document, append the text directly to the prompt
        if is_text:
            system_prompt += f"\n\n--- DOCUMENT TEXT ---\n{document_text}"

        print(f"Analyzing {filename} with {ACTIVE_MODEL}...")
        start_time = time.time()

        # --- The LLM Call (With Retry Loop) ---
        raw_text = ""

        for attempt in range(MAX_RETRIES):
            # Send images if Vision, send only text if Text
            messages = [{"role": "user", "content": system_prompt}]
            if is_vision:
                messages[0]["images"] = image_list

            response = ollama.chat(
                model=ACTIVE_MODEL,
                messages=messages,
                format="json",
            )

            raw_text = response["message"]["content"].strip()
            if raw_text:
                break

            print(f"  [Attempt {attempt + 1} Failed: Retrying...]")
            time.sleep(1)

        end_time = time.time()
        processing_time = round(end_time - start_time, 2)

        # --- Safe JSON Parsing ---
        if not raw_text:
            return {
                "categories": ["Misc"],
                "synopsis": "Error: AI returned empty response.",
                "time": processing_time,
            }

        # Safely strip markdown formatting without triggering chat interface or IDE bugs
        # chr(96) generates a backtick character dynamically
        MD_FENCE = chr(96) * 3

        if raw_text.startswith(MD_FENCE + "json\n"):
            raw_text = raw_text[8:]
        elif raw_text.startswith(MD_FENCE + "json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith(MD_FENCE):
            raw_text = raw_text[3:]

        if raw_text.endswith(MD_FENCE):
            raw_text = raw_text[:-3]

        result = json.loads(raw_text.strip())

        valid_categories = [
            cat for cat in result.get("categories", []) if cat in ALLOWED_CATEGORIES
        ]

        if not valid_categories:
            valid_categories = ["Misc"]

        return {
            "categories": valid_categories,
            "synopsis": result.get("synopsis", "No synopsis generated."),
            "time": processing_time,
        }

    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return {
            "categories": ["Misc"],
            "synopsis": f"Error during processing: {e}",
            "time": 0,
        }


def main():
    setup_directories()

    file_exists = os.path.isfile(SUMMARY_FILE)
    with open(SUMMARY_FILE, mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(
                ["Filename", "Categories", "Synopsis", "Model Used", "Time (Seconds)"]
            )

        batch_start = time.time()
        files_processed = 0

        for filename in os.listdir(INPUT_DIR):
            # Check against BOTH sets of allowed extensions
            if not filename.lower().endswith(VISION_EXTENSIONS + TEXT_EXTENSIONS):
                continue

            file_path = os.path.join(INPUT_DIR, filename)

            if is_file_locked(file_path):
                print(f"⚠️ Skipping '{filename}' - File is locked.\n")
                continue

            analysis = process_document(file_path, filename)
            categories = analysis["categories"]
            synopsis = analysis["synopsis"]
            process_time = analysis["time"]

            for category in categories:
                dest_path = os.path.join(BASE_OUTPUT_DIR, category, filename)
                shutil.copy2(file_path, dest_path)

            completed_path = os.path.join(COMPLETED_DIR, filename)
            shutil.move(file_path, completed_path)

            print(f"✓ Sorted '{filename}' into: {', '.join(categories)}")
            print(f"  └─ Time taken: {process_time} seconds\n")

            writer.writerow(
                [filename, ", ".join(categories), synopsis, ACTIVE_MODEL, process_time]
            )
            files_processed += 1

        batch_end = time.time()

        # --- Clean Console Summary ---
        print("\n=========================================")
        if files_processed > 0:
            print(f"SUCCESS! Batch complete.")
            print(
                f"Processed {files_processed} files in {round(batch_end - batch_start, 2)} seconds."
            )
        else:
            print("No valid documents found in the input directory.")
        print("=========================================")


if __name__ == "__main__":
    main()
