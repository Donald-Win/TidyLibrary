import os
import json
import re
import shutil
import datetime
from pathlib import Path

# Terminal Colors
class Colors:
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def clean_metadata(value):
    if value is None: return ""
    if isinstance(value, list):
        return clean_metadata(value[0]) if len(value) > 0 else ""
    s = str(value)
    if "," in s:
        s = s.split(",")[0]
    s = re.sub(r"^\[['\"]", "", s)
    s = re.sub(r"['\"]\]$", "", s)
    return s.strip()

def clean_filename(name):
    if not name: return ""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    return re.sub(r'\s+', ' ', name).strip()

def get_metadata_value(data, key_names):
    if isinstance(key_names, str):
        key_names = [key_names]
    for key in key_names:
        if data.get(key) is not None:
            return clean_metadata(data.get(key))
    meta = data.get('metadata', {})
    if isinstance(meta, dict):
        for key in key_names:
            if meta.get(key) is not None:
                return clean_metadata(meta.get(key))
    return ""

def format_total_duration(seconds):
    if not seconds: return "0h 0m"
    days = int(seconds // 86400)
    remaining_secs = seconds % 86400
    h = int(remaining_secs // 3600)
    m = int((remaining_secs % 3600) // 60)
    if days > 0:
        return f"{days}d {h}h {m}m"
    return f"{h}h {m}m"

def log_event(log_file, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def execute_move(book_info, log_file, collisions_set):
    target_dir = book_info['target_dir']
    old_book_dir = book_info['old_dir']
    try:
        log_event(log_file, f"START BOOK: {book_info['title']}")
        target_dir.mkdir(parents=True, exist_ok=True)
        for old_f, new_f in book_info['move_plan']:
            if old_f.is_file():
                if new_f.exists() and old_f.resolve() == new_f.resolve():
                    continue
                if new_f.exists():
                    log_event(log_file, f"  CONFLICT: {new_f.name} already exists.")
                    # Tidied: Add only the filename to the set for a cleaner unique list
                    collisions_set.add(new_f.name)
                    continue
                    
                shutil.move(str(old_f), str(new_f))
                log_event(log_file, f"  MOVED: {old_f.name} -> {new_f.name}")
        if old_book_dir.exists() and not any(old_book_dir.iterdir()):
            shutil.rmtree(old_book_dir)
            log_event(log_file, f"  CLEANUP: Removed empty dir {old_book_dir.name}")
        return True
    except Exception as e:
        log_event(log_file, f"!!! ERROR: {e}")
        return False

def print_section_header(title, color=Colors.CYAN):
    print(f"\n{color}{'='*60}{Colors.END}")
    print(f"{color}{Colors.BOLD}{title.center(60)}{Colors.END}")
    print(f"{color}{'='*60}{Colors.END}")

def print_book_details(book, root_path, counter_text=None):
    prefix = f"{counter_text} " if counter_text else ""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{prefix}{book['title'].upper()}{Colors.END}")
    
    old_rel = book['old_dir'].relative_to(root_path) if book['old_dir'].is_relative_to(root_path) else book['old_dir']
    new_rel = book['target_dir'].relative_to(root_path) if book['target_dir'].is_relative_to(root_path) else book['target_dir']
    
    if old_rel != new_rel:
        print(f"  {Colors.YELLOW}[FOLDER]{Colors.END} {Colors.RED}-{old_rel}{Colors.END}")
        print(f"           {Colors.GREEN}+{new_rel}{Colors.END}")

    for old, new in book['move_plan']:
        if old.name != new.name:
            print(f"    {Colors.YELLOW}[FILE]{Colors.END} {Colors.RED}-{old.name}{Colors.END}")
            print(f"           {Colors.GREEN}+{new.name}{Colors.END}")

def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== Audiobookshelf Library Tidy Tool ==={Colors.END}")
    
    while True:
        root_input = input(f"\n{Colors.BOLD}Enter path to library:{Colors.END} ").strip()
        if not root_input: continue
        root_path = Path(root_input)
        if root_path.exists() and root_path.is_dir(): break
        print(f"{Colors.RED}Path invalid.{Colors.END}")

    log_file = root_path / "tidy_library_log.txt"
    meta_files = list(root_path.rglob('metadata.json'))
    total_found = len(meta_files)
    audio_extensions = {'.mp3', '.m4b', '.m4a', '.flac', '.ogg'}
    
    planned_moves = []
    # Tidied: Using a set to prevent duplicate filenames in the final report
    collision_tracker = set()
    
    stats = {
        "books": 0, "authors": set(), "narrators": set(), "series": set(),
        "total_size": 0, "total_duration": 0.0, "standalone_count": 0
    }
    
    print(f"\n{Colors.CYAN}Scanning and analyzing library...{Colors.END}")

    for idx, meta_path in enumerate(meta_files, 1):
        if idx % 5 == 0 or idx == total_found:
            print(f"\r  Processing: {idx}/{total_found} books...", end="", flush=True)
            
        old_book_dir = meta_path.parent
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stats["books"] += 1
            author = get_metadata_value(data, ['authorName', 'author', 'authors', 'bookAuthor']) or "Unknown Author"
            book_title = get_metadata_value(data, ['title', 'bookTitle']) or "Unknown Title"
            narrator = get_metadata_value(data, ['narratorName', 'narrator', 'narrators']) or "Unknown Narrator"
            series_field = get_metadata_value(data, ['seriesName', 'series']) or ""
            duration_raw = data.get('duration') or data.get('metadata', {}).get('duration') or 0
            
            stats["authors"].add(author)
            if narrator != "Unknown Narrator":
                stats["narrators"].add(narrator)
            
            if series_field:
                series_name = series_field.split("#")[0].strip()
                stats["series"].add(series_name)
            else:
                stats["standalone_count"] += 1

            try:
                stats["total_duration"] += float(duration_raw)
            except: pass

            series_title = ""
            book_number = ""
            if "#" in series_field:
                parts = series_field.split("#")
                series_title = clean_filename(parts[0])
                raw_num = parts[1].strip()
                if "." in raw_num:
                    n_p = raw_num.split(".")
                    book_number = f"{n_p[0].zfill(2)}.{n_p[1]}"
                elif raw_num.isdigit():
                    book_number = raw_num.zfill(2)
                else:
                    book_number = raw_num
            else:
                series_title = clean_filename(series_field)

            c_author = clean_filename(author)
            c_title = clean_filename(book_title)

            if series_title:
                folder_label = f"{book_number} {c_title}".strip() if book_number else c_title
                target_dir = root_path / c_author / series_title / folder_label
            else:
                target_dir = root_path / c_author / c_title

            all_items = list(old_book_dir.iterdir())
            audio_files = sorted([f for f in all_items if f.suffix.lower() in audio_extensions], key=lambda x: natural_sort_key(x.name))
            
            for item in all_items:
                if item.is_file():
                    stats["total_size"] += item.stat().st_size
            
            move_plan = []
            num_audio = len(audio_files)
            for i, old_path in enumerate(audio_files, start=1):
                name_parts = [c_author]
                if series_title:
                    name_parts.append(f"{series_title} {book_number}".strip())
                name_parts.append(c_title)
                base_name = " - ".join([p for p in name_parts if p])
                final_filename = f"{base_name}{' - ' + str(i).zfill(2) if num_audio > 1 else ''}{old_path.suffix}"
                move_plan.append((old_path, target_dir / clean_filename(final_filename)))

            for f in all_items:
                if f.is_file() and f not in audio_files:
                    move_plan.append((f, target_dir / f.name))

            if (old_book_dir.resolve() != target_dir.resolve()) or any(old.name != new.name for old, new in move_plan):
                planned_moves.append({'title': book_title, 'old_dir': old_book_dir, 'target_dir': target_dir, 'move_plan': move_plan})
        except: pass

    print_section_header("LIBRARY STATISTICS")
    print(f"  Books:           {stats['books']}")
    print(f"  Authors:         {len(stats['authors'])}")
    print(f"  Narrators:       {len(stats['narrators'])}")
    print(f"  Series:          {len(stats['series'])}")
    print(f"  Standalone:      {stats['standalone_count']}")
    print(f"  Total Play Time: {format_total_duration(stats['total_duration'])}")
    print(f"  Library Size:    {stats['total_size'] / (1024**3):.2f} GB")

    if not planned_moves:
        print_section_header("✨ GREAT NEWS ✨", Colors.GREEN)
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'YOUR LIBRARY IS ALREADY TIDY!'.center(60)}{Colors.END}")
        print(f"\n{Colors.GREEN}{'='*60}{Colors.END}\n")
        return

    print_section_header("PROPOSED CHANGES")
    for book in planned_moves:
        print_book_details(book, root_path)

    print_section_header("EXECUTION")
    print(f"  Found {len(planned_moves)} books to tidy.")
    print(f"\n  [1] Apply ALL   [2] Review One-by-One   [3] Exit")
    
    choice = input(f"\n  Selection: ").strip()
    exec_stats = {"applied": 0, "skipped": 0, "errors": 0}
    
    if choice in ['1', '2']:
        log_event(log_file, f"--- SESSION START: {len(planned_moves)} books ---")
        for i, book in enumerate(planned_moves, 1):
            if choice == '2':
                print_book_details(book, root_path, f"[{i}/{len(planned_moves)}]")
                prompt = (f"\n  Apply Changes?  "
                         f"[{Colors.YELLOW}{Colors.BOLD}Y{Colors.END}] for Yes   "
                         f"[{Colors.YELLOW}{Colors.BOLD}N{Colors.END}] for No   "
                         f"[{Colors.YELLOW}{Colors.BOLD}Q{Colors.END}] to Quit: ")
                confirm = input(prompt).lower().strip()
                if confirm == 'q': break
                if confirm != 'y':
                    exec_stats["skipped"] += 1; continue

            if execute_move(book, log_file, collision_tracker):
                exec_stats["applied"] += 1
                if choice == '2': print(f"  {Colors.GREEN}✓ Applied.{Colors.END}")
            else:
                exec_stats["errors"] += 1

        print_section_header("RESULTS", Colors.GREEN if not collision_tracker and exec_stats['errors'] == 0 else Colors.YELLOW)
        print(f"  Applied:    {Colors.GREEN}{exec_stats['applied']}{Colors.END}")
        print(f"  Skipped:    {Colors.YELLOW}{exec_stats['skipped']}{Colors.END}")
        
        if collision_tracker:
            # Sorted unique filenames for a cleaner display
            print(f"  Collisions: {Colors.RED}{len(collision_tracker)}{Colors.END} (Files already at target)")
            for filename in sorted(collision_tracker):
                print(f"    {Colors.DIM}- {filename}{Colors.END}")

        if exec_stats['errors'] > 0: 
            print(f"  Errors:     {Colors.RED}{exec_stats['errors']}{Colors.END}")
            
        print(f"\n  Log: {Colors.DIM}{log_file}{Colors.END}\n")
    else:
        print(f"\n{Colors.YELLOW}Exited.{Colors.END}\n")

if __name__ == "__main__":
    main()
