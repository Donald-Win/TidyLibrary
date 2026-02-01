# Audiobookshelf Library Tidy Tool

A Python utility for standardizing and organizing audiobook libraries. This tool parses `metadata.json` files from **Audiobookshelf** to rename folders and files into a clean, consistent hierarchy.

## 🚀 Quick Start (Best Method)

For Raspberry Pi and Linux users, the best way to run this script without managing a full repository is to download the standalone file. This ensures the script can correctly generate its `tidy_library_log.txt` in your current directory.

**Run these commands in your terminal:**

`wget https://raw.githubusercontent.com/Donald-Win/TidyLibrary/main/tidy.py`

`python3 tidy.py`

## 📂 Organizational Logic

The tool reorganizes your library into a standardized structure:

- **Standard Books:** `Library/Author/Title/Author - Title.m4b`
- **Series:** `Library/Author/Series Name/Volume Title/Author - Series Vol - Title.m4b`

## ✨ Key Features

* **Collision Protection:** Automatically detects if a file already exists at the destination. It will skip the move and report the unique collision in the final summary.
* **Multi-Author Handling:** Intelligently uses the primary author for folder organization to keep your directory structure clean.
* **Series Awareness:** Automatically pads volume numbers (e.g., `01`, `02`) for perfect alphabetical sorting.
* **Library Analytics:** Provides a comprehensive summary including total books, unique authors, total play time, and library size.
* **Interactive Modes:** Choose between a bulk "Apply ALL" or a "Review One-by-One" mode to verify changes.

## 📊 Requirements

* **Python 3.6+**
* No external dependencies (Standard Library only).

## ⚠️ Safety & Logging

The script is designed to be "safety-first." It will never move a file without your confirmation (unless you explicitly select "Apply ALL"). Every action—including moves, empty folder cleanups, and skipped collisions—is logged to `tidy_library_log.txt` in the root of your library for easy auditing.

---
*Created for the Audiobookshelf community.*
