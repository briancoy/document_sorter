import os
import shutil
import json
import csv
import time
import threading
import fitz  # PyMuPDF
import docx
import ollama

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import scrolledtext

CONFIG_FILE = "categorizer_config.json"

DEFAULT_CONFIG = {
    "input_dir": "./docs_to_sort",
    "output_dir": "./categorized_documents",
    "completed_dir": "./completed_originals",
    "categories": [
        "General Financial",
        "Personal",
        "Hobbies",
        "Writings or Fiction",
        "Fitness and Health",
        "Food and Recipes",
        "Programming and Data Science",
        "Personal Improvement",
        "Misc",
    ],
    "model": "qwen3-vl:8b",
    "max_pages": 8,
    "dpi": 120,
    "max_retries": 3,
}

# Supported file extensions
VISION_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif")
TEXT_EXTENSIONS = (".txt", ".docx")


class CategorizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Document Categorizer (AI-Powered)")
        self.root.geometry("850x700")
        self.root.minsize(800, 600)

        self.config = self.load_config()
        self.is_running = False

        self.create_widgets()

        # Handle window close to save config
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_ollama_models(self):
        """Fetch available models from local Ollama instance."""
        try:
            response = ollama.list()
            models = []

            # ollama.list() handles versions differently; this safely checks both
            for m in response.get("models", []):
                if hasattr(m, "model"):
                    models.append(m.model)
                elif isinstance(m, dict) and "name" in m:
                    models.append(m["name"])

            if not models:
                return [self.config.get("model", "qwen3-vl:8b")]
            return models
        except Exception as e:
            print(f"Warning: Could not fetch Ollama models (is Ollama running?): {e}")
            return [self.config.get("model", "qwen3-vl:8b")]

    def load_config(self):
        """Load settings from config file or use defaults."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        """Save current settings to config file."""
        # Update config dictionary from UI elements
        self.config["input_dir"] = self.input_var.get()
        self.config["output_dir"] = self.output_var.get()
        self.config["completed_dir"] = self.completed_var.get()
        self.config["categories"] = list(self.category_listbox.get(0, tk.END))
        self.config["model"] = self.model_var.get()
        self.config["max_pages"] = int(self.pages_var.get())
        self.config["dpi"] = int(self.dpi_var.get())
        self.config["max_retries"] = int(self.retries_var.get())

        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def on_closing(self):
        """Triggered when the user closes the window."""
        if self.is_running:
            messagebox.showwarning(
                "Running", "Please wait for the current batch to finish before closing."
            )
            return
        self.save_config()
        self.root.destroy()

    def create_widgets(self):
        """Build the GUI layout."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Directories Section ---
        dir_frame = ttk.LabelFrame(main_frame, text="Directories", padding="10")
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        self.input_var = tk.StringVar(value=self.config.get("input_dir", ""))
        self.output_var = tk.StringVar(value=self.config.get("output_dir", ""))
        self.completed_var = tk.StringVar(value=self.config.get("completed_dir", ""))

        self.add_directory_row(dir_frame, "Source Folder (To Sort):", self.input_var, 0)
        self.add_directory_row(dir_frame, "Base Output Folder:", self.output_var, 1)
        self.add_directory_row(
            dir_frame, "Completed Originals Folder:", self.completed_var, 2
        )

        # --- Middle Section (Categories & Settings) ---
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        middle_frame.columnconfigure(0, weight=1)
        middle_frame.columnconfigure(1, weight=1)

        # Categories
        cat_frame = ttk.LabelFrame(middle_frame, text="Categories", padding="10")
        cat_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.category_listbox = tk.Listbox(cat_frame, height=8)
        self.category_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        for cat in self.config.get("categories", []):
            self.category_listbox.insert(tk.END, cat)

        cat_btn_frame = ttk.Frame(cat_frame)
        cat_btn_frame.pack(fill=tk.X)
        self.new_cat_var = tk.StringVar()
        ttk.Entry(cat_btn_frame, textvariable=self.new_cat_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(cat_btn_frame, text="Add", command=self.add_category).pack(
            side=tk.LEFT
        )
        ttk.Button(cat_btn_frame, text="Remove", command=self.remove_category).pack(
            side=tk.LEFT, padx=(5, 0)
        )

        # Settings
        set_frame = ttk.LabelFrame(
            middle_frame, text="Processing Options", padding="10"
        )
        set_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Fetch available models for the dropdown
        available_models = self.get_ollama_models()
        saved_model = self.config.get("model", "qwen3-vl:8b")

        # Ensure the saved model is always in the list, even if Ollama is currently offline
        if saved_model not in available_models:
            available_models.insert(0, saved_model)

        self.model_var = tk.StringVar(value=saved_model)
        self.pages_var = tk.StringVar(value=str(self.config.get("max_pages", 8)))
        self.dpi_var = tk.StringVar(value=str(self.config.get("dpi", 120)))
        self.retries_var = tk.StringVar(value=str(self.config.get("max_retries", 3)))

        # Update the first row to use a Combobox
        self.add_setting_row(
            set_frame,
            "Ollama Model:",
            self.model_var,
            0,
            is_combobox=True,
            values=available_models,
        )
        self.add_setting_row(set_frame, "Max Pages to Scan:", self.pages_var, 1)
        self.add_setting_row(set_frame, "Render DPI:", self.dpi_var, 2)
        self.add_setting_row(set_frame, "Max Retries:", self.retries_var, 3)

        # --- Console & Action Section ---
        console_frame = ttk.LabelFrame(main_frame, text="Live Log", padding="10")
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.console = scrolledtext.ScrolledText(
            console_frame,
            height=10,
            state="disabled",
            bg="#1e1e1e",
            fg="#d4d4d4",
            font=("Consolas", 10),
        )
        self.console.pack(fill=tk.BOTH, expand=True)

        self.run_button = ttk.Button(
            main_frame,
            text="▶ START CATEGORIZING",
            command=self.start_processing_thread,
            style="Accent.TButton",
        )
        self.run_button.pack(fill=tk.X, ipady=10)

    def add_directory_row(self, parent, label_text, string_var, row):
        """Helper to build directory selection rows."""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=2)
        entry = ttk.Entry(parent, textvariable=string_var, width=50)
        entry.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        ttk.Button(
            parent, text="Browse...", command=lambda: self.browse_directory(string_var)
        ).grid(row=row, column=2, pady=2)
        parent.columnconfigure(1, weight=1)

    def add_setting_row(
        self, parent, label_text, string_var, row, is_combobox=False, values=None
    ):
        """Helper to build setting rows."""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=5)

        if is_combobox:
            cb = ttk.Combobox(parent, textvariable=string_var, values=values, width=17)
            cb.grid(row=row, column=1, sticky="e", pady=5)
        else:
            ttk.Entry(parent, textvariable=string_var, width=20).grid(
                row=row, column=1, sticky="e", pady=5
            )

        parent.columnconfigure(1, weight=1)

    def browse_directory(self, string_var):
        """Open a folder selection dialog."""
        directory = filedialog.askdirectory()
        if directory:
            string_var.set(directory)

    def add_category(self):
        new_cat = self.new_cat_var.get().strip()
        if new_cat and new_cat not in self.category_listbox.get(0, tk.END):
            self.category_listbox.insert(tk.END, new_cat)
            self.new_cat_var.set("")

    def remove_category(self):
        selection = self.category_listbox.curselection()
        if selection:
            self.category_listbox.delete(selection)

    def log(self, message):
        """Safely append text to the console from any thread."""

        def append():
            self.console.config(state="normal")
            self.console.insert(tk.END, message + "\n")
            self.console.see(tk.END)
            self.console.config(state="disabled")

        self.root.after(0, append)

    # =========================================================
    # BACKEND PROCESSING LOGIC
    # =========================================================

    def extract_text(self, file_path, filename):
        try:
            if filename.lower().endswith(".txt"):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            elif filename.lower().endswith(".docx"):
                doc = docx.Document(file_path)
                return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            self.log(f"[!] Error reading text from {filename}: {e}")
            return ""

    def start_processing_thread(self):
        if self.is_running:
            return

        # Validate Folders
        if not os.path.isdir(self.input_var.get()):
            messagebox.showerror("Error", "Source Folder does not exist!")
            return

        # Save current UI settings into config before running
        self.save_config()

        self.is_running = True
        self.run_button.config(text="Processing...", state=tk.DISABLED)
        self.console.config(state="normal")
        self.console.delete(1.0, tk.END)
        self.console.config(state="disabled")

        # Run in a background thread so the GUI doesn't freeze
        thread = threading.Thread(target=self.run_batch, daemon=True)
        thread.start()

    def run_batch(self):
        """The main execution loop (runs in a separate thread)."""
        input_dir = self.config["input_dir"]
        base_out_dir = self.config["output_dir"]
        completed_dir = self.config["completed_dir"]
        categories = self.config["categories"]
        model = self.config["model"]
        max_pages = self.config["max_pages"]
        dpi = self.config["dpi"]
        max_retries = self.config["max_retries"]

        summary_file = os.path.join(base_out_dir, "document_summary.csv")

        # Setup Directories
        os.makedirs(completed_dir, exist_ok=True)
        for cat in categories:
            os.makedirs(os.path.join(base_out_dir, cat), exist_ok=True)

        self.log("--- Starting Categorization Batch ---")
        self.log(f"Monitoring: {input_dir}")
        self.log(f"Model: {model} | Retries: {max_retries}")

        file_exists = os.path.isfile(summary_file)
        files_processed = 0
        batch_start = time.time()

        try:
            with open(summary_file, mode="a", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                if not file_exists:
                    writer.writerow(
                        [
                            "Filename",
                            "Categories",
                            "Synopsis",
                            "Model Used",
                            "Time (Seconds)",
                        ]
                    )

                for filename in os.listdir(input_dir):
                    if not filename.lower().endswith(
                        VISION_EXTENSIONS + TEXT_EXTENSIONS
                    ):
                        continue

                    file_path = os.path.join(input_dir, filename)

                    # Lock Check
                    try:
                        os.rename(file_path, file_path)
                    except OSError:
                        self.log(
                            f"⚠️ Skipping '{filename}' - File is locked or still copying."
                        )
                        continue

                    # Process Document
                    analysis = self.process_single_document(
                        file_path,
                        filename,
                        categories,
                        model,
                        max_pages,
                        dpi,
                        max_retries,
                    )

                    found_categories = analysis["categories"]
                    synopsis = analysis["synopsis"]
                    process_time = analysis["time"]

                    # Move Files
                    for category in found_categories:
                        dest_path = os.path.join(base_out_dir, category, filename)
                        shutil.copy2(file_path, dest_path)

                    completed_path = os.path.join(completed_dir, filename)
                    shutil.move(file_path, completed_path)

                    self.log(f"✓ Sorted '{filename}' -> {', '.join(found_categories)}")
                    self.log(f"  └─ Time: {process_time}s")

                    writer.writerow(
                        [
                            filename,
                            ", ".join(found_categories),
                            synopsis,
                            model,
                            process_time,
                        ]
                    )
                    files_processed += 1

        except Exception as e:
            self.log(f"[FATAL ERROR] {e}")

        batch_end = time.time()
        self.log("\n=========================================")
        if files_processed > 0:
            self.log(
                f"SUCCESS! Processed {files_processed} files in {round(batch_end - batch_start, 2)} seconds."
            )
        else:
            self.log("No valid documents found in the Source folder.")
        self.log("=========================================")

        # Reset UI
        self.root.after(0, self.reset_ui)

    def reset_ui(self):
        self.is_running = False
        self.run_button.config(text="▶ START CATEGORIZING", state=tk.NORMAL)

    def process_single_document(
        self, file_path, filename, allowed_cats, model, max_pages, dpi, max_retries
    ):
        """Handles the AI analysis of a single file."""
        try:
            is_vision = filename.lower().endswith(VISION_EXTENSIONS)
            is_text = filename.lower().endswith(TEXT_EXTENSIONS)

            image_list = []
            document_text = ""

            if is_vision:
                doc = fitz.open(file_path)
                pages_to_process = min(len(doc), max_pages)
                self.log(f"Rendering {pages_to_process} page(s) from {filename}...")

                for page_num in range(pages_to_process):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
                    image_list.append(pix.tobytes("jpg"))
                doc.close()
            elif is_text:
                self.log(f"Extracting text from {filename}...")
                document_text = self.extract_text(file_path, filename)[:15000]

            allowed_cats_str = ", ".join(allowed_cats)
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

            if is_text:
                system_prompt += f"\n\n--- DOCUMENT TEXT ---\n{document_text}"

            self.log(f"Analyzing {filename} with {model}...")
            start_time = time.time()

            raw_text = ""
            for attempt in range(max_retries):
                messages = [{"role": "user", "content": system_prompt}]
                if is_vision:
                    messages[0]["images"] = image_list

                response = ollama.chat(model=model, messages=messages, format="json")
                raw_text = response["message"]["content"].strip()

                if raw_text:
                    break

                self.log(f"  [Attempt {attempt + 1} Failed: Retrying...]")
                time.sleep(1)

            end_time = time.time()
            processing_time = round(end_time - start_time, 2)

            if not raw_text:
                return {
                    "categories": ["Misc"],
                    "synopsis": "Error: AI returned empty response.",
                    "time": processing_time,
                }

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
                cat for cat in result.get("categories", []) if cat in allowed_cats
            ]

            return {
                "categories": valid_categories if valid_categories else ["Misc"],
                "synopsis": result.get("synopsis", "No synopsis generated."),
                "time": processing_time,
            }

        except Exception as e:
            self.log(f"  └─ Error: {e}")
            return {"categories": ["Misc"], "synopsis": f"Error: {e}", "time": 0}


if __name__ == "__main__":
    root = tk.Tk()

    # Optional: Apply a slightly cleaner theme if available on the OS
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")

    app = CategorizerApp(root)
    root.mainloop()
