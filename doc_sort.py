import os
import shutil
import json
import csv
import time
import fitz  # PyMuPDF
import ollama

# --- Configuration ---
INPUT_DIR = r"\docs_to_sort"
BASE_OUTPUT_DIR = r"\categorized_documents"
COMPLETED_DIR = r"\completed_originals"
SUMMARY_FILE = r"\document_summary.csv"

# Swap models here to test performance
ACTIVE_MODEL = "qwen3-vl:8b"

# Multi-page safety limits
MAX_PAGES_TO_SCAN = 8
RENDER_DPI = 120

# Number of times to retry failed LLM read
MAX_RETRIES = 3

ALLOWED_CATEGORIES = [
    "Financial Documents",
    "Personal",
    "Hobbies",
    "Fiction",
    "Fitness and Health",
    "Food and Recipes",
    "Programming and Data Science",
    "Personal Improvement",
    "Misc",
]


def setup_directories():
    """Ensure all required directories exist."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(COMPLETED_DIR, exist_ok=True)
    for category in ALLOWED_CATEGORIES:
        os.makedirs(os.path.join(BASE_OUTPUT_DIR, category), exist_ok=True)


def is_file_locked(filepath):
    """
    Checks if a file is currently being written to or locked by another process.
    Renaming a file to itself is the most reliable way to check Windows file locks.
    """
    try:
        os.rename(filepath, filepath)
        return False
    except OSError:
        return True


def process_document(file_path, filename):
    """Renders the PDF and sends it to the local LLM for categorization."""
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_to_process = min(total_pages, MAX_PAGES_TO_SCAN)

        image_list = []
        print(f"Extracting {pages_to_process} page(s) from {filename}...")

        for page_num in range(pages_to_process):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=RENDER_DPI)
            image_list.append(pix.tobytes("jpg"))

        doc.close()

        system_prompt = f"""
        Analyze this {pages_to_process}-page document carefully. It may contain multiple articles, receipts, or distinct sections.
        1. Write a short 2-3 sentence synopsis summarizing the overall contents.
        2. Select ONE OR MORE categories from this exact list: {", ".join(ALLOWED_CATEGORIES)}.
        
        You must respond ONLY with valid JSON.
        Format:
        {{
            "categories": ["Selected Category 1", "Selected Category 2"],
            "synopsis": "A brief summary here."
        }}
        """

        print(f"Analyzing {filename} with {ACTIVE_MODEL}...")

        start_time = time.time()

        # --- THE RETRY LOOP ---
        raw_text = ""

        for attempt in range(MAX_RETRIES):
            response = ollama.chat(
                model=ACTIVE_MODEL,
                messages=[
                    {"role": "user", "content": system_prompt, "images": image_list}
                ],
                format="json",
            )

            raw_text = response["message"]["content"].strip()

            # If the AI actually gave us text, break out of the retry loop
            if raw_text:
                break

            print(
                f"  [Attempt {attempt + 1} Failed: AI returned a blank response. Retrying...]"
            )
            time.sleep(1)  # Give the GPU a tiny 1-second breather before trying again

        end_time = time.time()
        processing_time = round(end_time - start_time, 2)

        # --- STEP 4: Parse the AI's response safely ---
        # If it failed all attempts, log it as a potential blank page
        if not raw_text:
            return {
                "categories": ["Misc"],
                "synopsis": "Error: AI repeatedly returned an empty response. (Page may be blank or unreadable).",
                "time": processing_time,
            }

        # Scrub off markdown formatting if the AI mistakenly included it
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]

        if raw_text.endswith("```"):
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
        files_skipped = 0

        for filename in os.listdir(INPUT_DIR):
            if not filename.lower().endswith(".pdf"):
                continue

            file_path = os.path.join(INPUT_DIR, filename)

            # --- The File Lock Check ---
            if is_file_locked(file_path):
                print(
                    f"⚠️ Skipping '{filename}' - File is currently locked or being saved by the scanner.\n"
                )
                files_skipped += 1
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
            print(f"  └─ Time taken: {process_time} seconds")
            print(f"  └─ Moved original to: {COMPLETED_DIR}\n")

            writer.writerow(
                [filename, ", ".join(categories), synopsis, ACTIVE_MODEL, process_time]
            )
            files_processed += 1

        batch_end = time.time()

        print("--- Batch Summary ---")
        print(f"Processed: {files_processed} file(s)")
        print(f"Skipped (Locked): {files_skipped} file(s)")
        if files_processed > 0:
            print(f"Total time: {round(batch_end - batch_start, 2)} seconds")


if __name__ == "__main__":
    main()
