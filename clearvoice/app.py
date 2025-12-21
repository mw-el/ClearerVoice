#!/usr/bin/env python3
import os
import sys
import subprocess
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import shutil

print("DEBUG: Starte Skript...")

# --------- Automatic Conda Environment Activation ---------
print("DEBUG: Überprüfe Conda Umgebung...")
TARGET_CONDA_ENV = "clearervoice"
current_env = os.environ.get("CONDA_DEFAULT_ENV")
if current_env != TARGET_CONDA_ENV:
    print(f"DEBUG: Aktuelle Umgebung '{current_env}' entspricht nicht '{TARGET_CONDA_ENV}'. Starte neu...")
    conda_exe = os.environ.get("CONDA_EXE")
    if not conda_exe:
        possible_conda = os.path.join(os.path.expanduser("~"), "miniconda3", "bin", "conda")
        conda_exe = possible_conda if os.path.isfile(possible_conda) else "conda"
    try:
        cmd = [conda_exe, "run", "-n", TARGET_CONDA_ENV, "python"] + sys.argv
        subprocess.run(cmd)
    except Exception as e:
        print(f"DEBUG: Failed to re-launch: {e}")
    sys.exit(0)
# --------- End of Conda Environment Activation ---------

print("DEBUG: Lade Module...")
try:
    import yamlargparse
    print("DEBUG: yamlargparse geladen")
except ImportError:
    print("ERROR: yamlargparse fehlt!")
    sys.exit(1)

# Add clearvoice directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
print(f"DEBUG: Script-Verzeichnis: {script_dir}")

try:
    from pydub import AudioSegment
    print("DEBUG: pydub geladen")
except ImportError:
    AudioSegment = None
    print("DEBUG: pydub nicht verfügbar")

# --------- Configuration ---------
DEFAULT_INPUT_DIR = "/home/matthias/_1_SYNOLOGY/MW-D/DOCS/"
if not os.path.exists(DEFAULT_INPUT_DIR):
    DEFAULT_INPUT_DIR = os.path.expanduser("~")
print(f"DEBUG: Start-Verzeichnis: {DEFAULT_INPUT_DIR}")

# All common audio extensions (checked case-insensitive)
AUDIO_EXTENSIONS = {
    '.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.opus', '.wma',
    '.aiff', '.aif', '.aifc', '.au', '.snd', '.ra', '.ram',
    '.mp2', '.m4b', '.m4p', '.m4r', '.mka',
    '.oga', '.spx', '.ac3', '.dts', '.amr', '.awb', '.ape', '.mpc', '.wv',
    '.tta', '.tak', '.shn', '.dsf', '.dff', '.caf', '.w64', '.rf64'
}

# Video extensions (will extract audio from these)
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.mpg', '.mpeg', '.3gp', '.3g2', '.ts', '.mts', '.m2ts',
    '.vob', '.ogv', '.rm', '.rmvb', '.asf', '.divx'
}

# Combined media extensions for file browser
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def extract_audio_from_video(video_path, output_wav_path):
    """Extract audio from video file using ffmpeg"""
    import subprocess
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # WAV format
        '-ar', '48000',  # 48kHz sample rate (matches MossFormer2_SE_48K)
        '-ac', '1',  # Mono
        output_wav_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr}")
    return output_wav_path


def is_video_file(filename):
    """Check if file is a video file"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS


def remux_video_with_audio(video_path, audio_path, output_path):
    """Replace audio in video with new audio track using ffmpeg"""
    import subprocess
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,      # Original video
        '-i', audio_path,      # New audio
        '-c:v', 'copy',        # Copy video stream (no re-encoding)
        '-map', '0:v:0',       # Use video from first input
        '-map', '1:a:0',       # Use audio from second input
        '-shortest',           # End when shortest stream ends
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg remux error: {result.stderr}")
    return output_path

# --------- DPI Scaling ---------
def get_dpi_scale():
    """Detect DPI scale factor for High-DPI displays"""
    temp_root = tk.Tk()
    temp_root.withdraw()
    dpi = temp_root.winfo_fpixels('1i')
    temp_root.destroy()
    scale = dpi / 96.0
    print(f"DEBUG: DPI={dpi}, Scale={scale:.2f}")
    return scale

DPI_SCALE = get_dpi_scale()
BASE_FONT_SIZE = 10
SCALED_FONT_SIZE = max(10, int(BASE_FONT_SIZE * DPI_SCALE))
DEFAULT_FONT = ('Segoe UI', SCALED_FONT_SIZE)
BOLD_FONT = ('Segoe UI', SCALED_FONT_SIZE, 'bold')
MONO_FONT = ('Monospace', SCALED_FONT_SIZE - 1)
print(f"DEBUG: Font-Größe: {SCALED_FONT_SIZE}")


# --------- File Selection Helper ---------
def open_file_picker(initialdir=DEFAULT_INPUT_DIR):
    """Open file picker using Nautilus-based dialog with bookmarks support"""
    # Simplified filters to avoid zenity crashes with too many patterns
    zenity_cmd = [
        'zenity', '--file-selection', '--multiple',
        f'--filename={initialdir}/',
        '--title=Audio- oder Videodatei auswählen',
        '--file-filter=Audio & Video | *.wav *.mp3 *.flac *.ogg *.m4a *.aac *.mp4 *.mkv *.avi *.mov *.webm',
        '--file-filter=Audio | *.wav *.mp3 *.flac *.ogg *.m4a *.aac',
        '--file-filter=Video | *.mp4 *.mkv *.avi *.mov *.webm',
        '--file-filter=All Files | *'
    ]

    try:
        result = subprocess.run(
            zenity_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )

        if result.returncode == 0 and result.stdout:
            # zenity returns paths separated by |
            files = result.stdout.strip().split('|')
            return tuple(f for f in files if f and os.path.isfile(f))  # Validate files exist
        else:
            return ()

    except Exception as e:
        print(f"DEBUG: File picker error: {e}")
        return ()


class ClearVoiceApp:
    def __init__(self, root):
        print("DEBUG: Initialisiere GUI...")
        self.root = root
        self.root.title("ClearerVoice - Speech Enhancement")

        # Scale window size with DPI
        win_width = int(1000 * DPI_SCALE)
        win_height = int(600 * DPI_SCALE)
        self.root.geometry(f"{win_width}x{win_height}")

        # Set default font for all widgets
        self.root.option_add('*Font', DEFAULT_FONT)

        # Configure ttk style
        style = ttk.Style()
        style.configure("Treeview", font=MONO_FONT, rowheight=int(24 * DPI_SCALE))
        style.configure("Treeview.Heading", font=BOLD_FONT)

        self.selected_files = []
        self.myClearVoice = None
        self.myClearVoice_SR = None
        self.checked_files = set()  # Track which files are checked in treeview

        self.create_widgets()
        print("DEBUG: GUI initialisiert")

    def create_widgets(self):
        # Top: File selection and Options
        options_frame = ttk.Frame(self.root)
        options_frame.pack(fill="x", padx=5, pady=5)

        # File picker button (left side)
        ttk.Button(options_frame, text="[ + ] Dateien hinzufügen",
                   command=self._open_file_picker).pack(side="left", padx=(0, 10))

        # Checkboxes (middle)
        self.apply_sr_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="SR (48kHz)",
                        variable=self.apply_sr_var).pack(side="left", padx=(0, 10))

        self.apply_loudness_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Lautstärke",
                        variable=self.apply_loudness_var).pack(side="left", padx=(0, 10))

        self.remux_video_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Video",
                        variable=self.remux_video_var).pack(side="left", padx=(0, 10))

        # Transcription format checkboxes
        self.transcribe_txt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="TXT",
                        variable=self.transcribe_txt_var).pack(side="left", padx=(0, 10))

        self.transcribe_srt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="SRT",
                        variable=self.transcribe_srt_var).pack(side="left", padx=(0, 10))

        # Transcribe button
        self.transcribe_btn = ttk.Button(options_frame, text="Transcribe",
                                         command=self.transcribe_files)
        self.transcribe_btn.pack(side="left", padx=(0, 10))

        # Process button (in toolbar)
        self.process_btn = ttk.Button(options_frame, text="Optimieren",
                                      command=self.process_files)
        self.process_btn.pack(side="left", padx=(0, 10))

        # Main content: Selected files and controls
        right_frame = ttk.Frame(self.root)
        right_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Selected files list with "Check All" checkbox
        list_header_frame = ttk.Frame(right_frame)
        list_header_frame.pack(fill="x", padx=5, pady=(5, 0))

        ttk.Label(list_header_frame, text="Ausgewählte Dateien").pack(side="left")

        self.check_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(list_header_frame, text="Alle auswählen",
                        variable=self.check_all_var,
                        command=self._toggle_all_files).pack(side="right", padx=(0, 5))

        list_frame = ttk.LabelFrame(right_frame, text="")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        list_container = ttk.Frame(list_frame)
        list_container.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")

        # Create Treeview with checkbox column
        self.file_tree = ttk.Treeview(list_container, columns=("checked", "filename"),
                                      show="tree", yscrollcommand=scrollbar.set, height=10)
        self.file_tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_tree.yview)

        # Configure columns
        self.file_tree.column("#0", width=0, stretch=tk.NO)
        self.file_tree.column("checked", width=30, anchor="center")
        self.file_tree.column("filename", anchor="w")

        # Bind events for checkbox toggling
        self.file_tree.bind("<Button-1>", self._on_treeview_click)
        self.file_tree.bind("<Button-3>", self._on_treeview_right_click)

        # Status frame
        status_frame = ttk.LabelFrame(right_frame, text="Status")
        status_frame.pack(fill="both", expand=True, padx=5, pady=5)

        status_container = ttk.Frame(status_frame)
        status_container.pack(fill="both", expand=True)

        status_scrollbar = ttk.Scrollbar(status_container)
        status_scrollbar.pack(side="right", fill="y")

        self.status_text = tk.Text(status_container, height=6, font=MONO_FONT,
                                    yscrollcommand=status_scrollbar.set, state="disabled",
                                    bg="#f0f0f0")
        self.status_text.pack(side="left", fill="both", expand=True)
        status_scrollbar.config(command=self.status_text.yview)

    def _open_file_picker(self):
        """Open system file picker to select audio/video files"""
        files = open_file_picker(initialdir=DEFAULT_INPUT_DIR)
        if files:
            for filepath in files:
                self.add_file(filepath)

    def add_file(self, filepath):
        """Add a single file to the selection"""
        if filepath not in self.selected_files:
            self.selected_files.append(filepath)
            # Add to treeview with checkbox
            item_id = self.file_tree.insert("", "end", values=(" ", os.path.basename(filepath)))
            self.checked_files.add(item_id)  # Default checked
            self._update_treeview_item(item_id)  # Update display
            self.log_status(f"+ {os.path.basename(filepath)}")

    def _update_treeview_item(self, item_id):
        """Update treeview item display based on checked state"""
        checkbox = "✓" if item_id in self.checked_files else " "
        values = self.file_tree.item(item_id, "values")
        self.file_tree.item(item_id, values=(checkbox, values[1]))

    def _on_treeview_click(self, event):
        """Handle left-click on treeview (toggle checkbox)"""
        region = self.file_tree.identify_region(event.x, event.y)
        if region == "cell":
            col = self.file_tree.identify_column(event.x)
            item = self.file_tree.identify_row(event.y)
            if item and col == "#1":  # Clicked on checkbox column
                if item in self.checked_files:
                    self.checked_files.discard(item)
                else:
                    self.checked_files.add(item)
                self._update_treeview_item(item)
                self._update_check_all_status()

    def _on_treeview_right_click(self, event):
        """Handle right-click on treeview (context menu)"""
        item = self.file_tree.identify_row(event.y)
        if item:
            # Show context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(
                label="Löschen",
                command=lambda: self._delete_file_item(item)
            )
            context_menu.add_separator()
            context_menu.add_command(
                label="Alle auswählen",
                command=self._select_all_items
            )
            context_menu.add_command(
                label="Auswahl aufheben",
                command=self._deselect_all_items
            )
            context_menu.post(event.x_root, event.y_root)

    def _delete_file_item(self, item_id):
        """Delete a file from the list"""
        values = self.file_tree.item(item_id, "values")
        filename = values[1]
        # Find and remove from selected_files
        for i, f in enumerate(self.selected_files):
            if os.path.basename(f) == filename:
                removed = self.selected_files.pop(i)
                break
        # Remove from treeview and checked_files
        self.file_tree.delete(item_id)
        self.checked_files.discard(item_id)
        self.log_status(f"- {filename}")

    def _toggle_all_files(self):
        """Toggle all files checked/unchecked"""
        if self.check_all_var.get():
            for item_id in self.file_tree.get_children():
                self.checked_files.add(item_id)
                self._update_treeview_item(item_id)
        else:
            for item_id in self.file_tree.get_children():
                self.checked_files.discard(item_id)
                self._update_treeview_item(item_id)

    def _update_check_all_status(self):
        """Update Check All checkbox based on individual items"""
        items = self.file_tree.get_children()
        if not items:
            self.check_all_var.set(False)
            return
        all_checked = all(item in self.checked_files for item in items)
        self.check_all_var.set(all_checked)

    def _select_all_items(self):
        """Select all items via context menu"""
        for item_id in self.file_tree.get_children():
            self.checked_files.add(item_id)
            self._update_treeview_item(item_id)
        self.check_all_var.set(True)

    def _deselect_all_items(self):
        """Deselect all items via context menu"""
        for item_id in self.file_tree.get_children():
            self.checked_files.discard(item_id)
            self._update_treeview_item(item_id)
        self.check_all_var.set(False)

    def log_status(self, message):
        """Add message to status window"""
        print(f"DEBUG: {message}")
        self.status_text.config(state="normal")
        self.status_text.insert("end", f"{message}\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")
        self.root.update()

    def clear_files(self):
        """Clear all files from list"""
        self.selected_files.clear()
        self.file_tree.delete(*self.file_tree.get_children())
        self.checked_files.clear()
        self.check_all_var.set(False)
        self.log_status("Liste geleert")

    def remove_selected(self):
        """Remove selected files from list (legacy - kept for compatibility)"""
        items_to_delete = [item for item in self.file_tree.get_children()
                          if item in self.checked_files]
        for item_id in items_to_delete:
            self._delete_file_item(item_id)

    def process_files(self):
        """Process all selected files"""
        if not self.selected_files:
            messagebox.showwarning("Keine Dateien", "Bitte erst Dateien hinzufügen!")
            return

        self.process_btn.config(state="disabled", text="Optimiert...")
        thread = threading.Thread(target=self._process_files_thread)
        thread.start()

    def _process_files_thread(self):
        """Processing thread"""
        try:
            self.log_status("=" * 40)
            self.log_status("Starte Verarbeitung...")

            if self.myClearVoice is None:
                self.log_status("Lade ClearVoice Modell...")
                try:
                    from clearvoice import ClearVoice
                    self.myClearVoice = ClearVoice(task='speech_enhancement',
                                                    model_names=['MossFormer2_SE_48K'],
                                                    apply_loudness_processing_flag=self.apply_loudness_var.get())
                    self.log_status("Modell geladen!")
                except Exception as e:
                    self.log_status(f"FEHLER: {e}")
                    import traceback
                    self.log_status(traceback.format_exc())
                    self._enable_process_btn()
                    return

            total = len(self.selected_files)
            for i, input_file in enumerate(self.selected_files, 1):
                self.log_status(f"\n[{i}/{total}] {os.path.basename(input_file)}")

                try:
                    folder = os.path.dirname(input_file)
                    base_name, ext = os.path.splitext(os.path.basename(input_file))
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

                    # Check if it's a video file - extract audio first
                    temp_audio = None
                    is_video = is_video_file(input_file)
                    if is_video:
                        self.log_status("  Extrahiere Audio aus Video...")
                        temp_audio = os.path.join(folder, f"{base_name}-temp-{timestamp}.wav")
                        extract_audio_from_video(input_file, temp_audio)
                        audio_to_process = temp_audio
                        output_ext = ".wav"  # Output as WAV for audio
                    else:
                        audio_to_process = input_file
                        output_ext = ext

                    cleaned_path = os.path.join(folder, f"{base_name}-cleaned-{timestamp}{output_ext}")

                    self.log_status("  Entrausche...")
                    enhanced_audio = self.myClearVoice(input_path=audio_to_process, online_write=False)
                    self.myClearVoice.write(enhanced_audio, output_path=cleaned_path)
                    self.log_status(f"  → {os.path.basename(cleaned_path)}")

                    # Clean up temp file if we extracted from video
                    if temp_audio and os.path.exists(temp_audio):
                        os.remove(temp_audio)

                    # Final audio path (might be SR output later)
                    final_audio = cleaned_path

                    if self.apply_sr_var.get():
                        if self.myClearVoice_SR is None:
                            self.log_status("  Lade SR-Modell...")
                            from clearvoice import ClearVoice
                            self.myClearVoice_SR = ClearVoice(task='speech_super_resolution',
                                                               model_names=['MossFormer2_SR_48K'])

                        sr_output = os.path.join(folder, f"{base_name}-cleaned-sr-{timestamp}{output_ext}")
                        self.log_status("  Super-Resolution...")
                        sr_audio = self.myClearVoice_SR(input_path=cleaned_path, online_write=False)
                        self.myClearVoice_SR.write(sr_audio, output_path=sr_output)
                        self.log_status(f"  → {os.path.basename(sr_output)}")
                        final_audio = sr_output

                    # Remux video with cleaned audio if requested
                    if is_video and self.remux_video_var.get():
                        self.log_status("  Remuxe Video mit bereinigtem Audio...")
                        remuxed_path = os.path.join(folder, f"{base_name}-cleaned-{timestamp}{ext}")
                        remux_video_with_audio(input_file, final_audio, remuxed_path)
                        self.log_status(f"  → {os.path.basename(remuxed_path)}")

                    self.log_status("  [OK] Fertig!")

                except Exception as e:
                    self.log_status(f"  FEHLER: {e}")
                    import traceback
                    self.log_status(traceback.format_exc())

            self.log_status("\n" + "=" * 40)
            self.log_status(f"Alle {total} Dateien verarbeitet!")

        except Exception as e:
            self.log_status(f"FEHLER: {e}")
            import traceback
            self.log_status(traceback.format_exc())

        finally:
            self._enable_process_btn()

    def transcribe_files(self):
        """Transcribe all checked files using aTrainCore"""
        # Get checked files only
        checked_items = [item for item in self.file_tree.get_children()
                        if item in self.checked_files]

        if not checked_items:
            messagebox.showwarning("Keine Dateien", "Bitte erst Dateien auswählen!")
            return

        # Check if at least one output format is selected
        if not (self.transcribe_txt_var.get() or self.transcribe_srt_var.get()):
            messagebox.showwarning("Kein Format", "Bitte TXT oder SRT auswählen!")
            return

        self.transcribe_btn.config(state="disabled", text="Transcribing...")
        thread = threading.Thread(target=self._transcribe_files_thread)
        thread.start()

    def _transcribe_files_thread(self):
        """Background thread for transcription"""
        try:
            self.log_status("=" * 40)
            self.log_status("Starte Transkription...")

            # Get checked files only
            checked_items = [item for item in self.file_tree.get_children()
                            if item in self.checked_files]

            total = len(checked_items)
            for idx, item_id in enumerate(checked_items, 1):
                values = self.file_tree.item(item_id, "values")
                filename = values[1]

                # Find full path from selected_files
                input_file = None
                for f in self.selected_files:
                    if os.path.basename(f) == filename:
                        input_file = f
                        break

                if not input_file:
                    self.log_status(f"[{idx}/{total}] FEHLER: Datei nicht gefunden: {filename}")
                    continue

                self.log_status(f"\n[{idx}/{total}] Transkribiere: {filename}")

                try:
                    # Get output folder and base name
                    output_folder = os.path.dirname(input_file)
                    base_name = os.path.splitext(os.path.basename(input_file))[0]

                    # Record time before transcription
                    before_time = datetime.datetime.now()

                    # Check if aTrain environment is available
                    conda_cmd = (
                        "source ~/miniconda3/etc/profile.d/conda.sh && "
                        "conda activate atrain && "
                    )

                    # Build aTrainCore command
                    transcribe_cmd = (
                        f"aTrain_core transcribe \"{input_file}\" "
                        f"--model large-v3-turbo "
                        f"--language auto-detect "
                        f"--device GPU "
                        f"--compute_type float16"
                    )

                    cmd = ["bash", "-c", conda_cmd + transcribe_cmd]

                    self.log_status("  Starte aTrain_core...")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=600  # 10 minutes timeout
                    )

                    if result.returncode != 0:
                        self.log_status(f"  aTrain_core Fehler: {result.stderr[:200]}")
                        continue

                    # aTrainCore writes to ~/Documents/aTrain/transcriptions/
                    transcriptions_dir = os.path.expanduser("~/Documents/aTrain/transcriptions")

                    # Find newly created transcription files (only newer than before_time)
                    transcript_files = self._find_transcription_files(transcriptions_dir, before_time)

                    if not transcript_files:
                        self.log_status("  FEHLER: Keine Transkriptions-Dateien gefunden")
                        continue

                    # Move and rename files
                    for transcript_file in transcript_files:
                        base_transcript = os.path.basename(transcript_file)

                        # Check if we should keep this format
                        keep_file = False
                        if "transcription.txt" in base_transcript and self.transcribe_txt_var.get():
                            keep_file = True
                            output_name = f"{base_name}.txt"
                        elif "transcription.srt" in base_transcript and self.transcribe_srt_var.get():
                            keep_file = True
                            output_name = f"{base_name}.srt"

                        if keep_file:
                            output_path = os.path.join(output_folder, output_name)
                            # Handle existing files
                            if os.path.exists(output_path):
                                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                                base, ext = os.path.splitext(output_path)
                                output_path = f"{base}_{timestamp}{ext}"

                            shutil.move(transcript_file, output_path)
                            self.log_status(f"  ✓ {output_name}")
                        else:
                            # Delete unwanted files
                            try:
                                os.remove(transcript_file)
                            except:
                                pass

                    self.log_status("  [OK] Fertig!")

                except subprocess.TimeoutExpired:
                    self.log_status(f"  FEHLER: Timeout (zu lange)")
                except Exception as e:
                    self.log_status(f"  FEHLER: {str(e)}")
                    import traceback
                    self.log_status(traceback.format_exc())

            self.log_status("\n" + "=" * 40)
            self.log_status(f"Transkription abgeschlossen!")

        except Exception as e:
            self.log_status(f"FEHLER: {e}")
            import traceback
            self.log_status(traceback.format_exc())

        finally:
            self._enable_transcribe_btn()

    def _find_transcription_files(self, transcriptions_dir, after_time=None):
        """Find newly created transcription files (optionally filtered by time)"""
        if not os.path.exists(transcriptions_dir):
            return []

        files = []
        for root, dirs, filenames in os.walk(transcriptions_dir):
            for filename in filenames:
                if filename in ("transcription.txt", "transcription.srt"):
                    filepath = os.path.join(root, filename)
                    # If after_time is specified, only return files created after that time
                    if after_time:
                        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                        if mtime >= after_time:
                            files.append(filepath)
                    else:
                        files.append(filepath)

        return files

    def _enable_transcribe_btn(self):
        """Re-enable transcribe button"""
        self.root.after(0, lambda: self.transcribe_btn.config(state="normal",
                                                             text="Transcribe"))

    def _enable_process_btn(self):
        """Re-enable process button"""
        self.root.after(0, lambda: self.process_btn.config(state="normal",
                                                            text="Optimieren"))


# --------- Main ---------
if __name__ == "__main__":
    print("DEBUG: Erstelle Hauptfenster...")
    root = tk.Tk(className='clearervoice')
    app = ClearVoiceApp(root)
    print("DEBUG: Starte Mainloop...")
    root.mainloop()
    print("DEBUG: Programm beendet.")
