#!/usr/bin/env python3
import os
import sys
import subprocess
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
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
        'ffmpeg', '-y',
        '-loglevel', 'error',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # WAV format
        '-ar', '48000',  # 48kHz sample rate (matches MossFormer2_SE_48K)
        '-ac', '1',  # Mono
        output_wav_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
        '-loglevel', 'error',
        '-i', video_path,      # Original video
        '-i', audio_path,      # New audio
        '-c:v', 'copy',        # Copy video stream (no re-encoding)
        '-map', '0:v:0',       # Use video from first input
        '-map', '1:a:0',       # Use audio from second input
        '-shortest',           # End when shortest stream ends
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
BASE_FONT_SIZE = 11  # Increased from 10 for better readability
SCALED_FONT_SIZE = max(11, int(BASE_FONT_SIZE * DPI_SCALE))
SCALED_FONT_SIZE_LARGE = max(12, int(12 * DPI_SCALE))  # For headings
SCALED_FONT_SIZE_SMALL = max(9, int(9 * DPI_SCALE))    # For small text

# Font definitions will be set up after root window is created
DEFAULT_FONT = None
BOLD_FONT = None
HEADING_FONT = None
MONO_FONT = None


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

        # Set up fonts now that root window exists
        self._setup_fonts()

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

        # GPU queue management - prevent concurrent GPU operations
        self.operation_running = None  # 'optimize' or 'transcribe' or None
        self.optimize_queued = False   # Flag if optimize was queued while transcribe running
        self.transcribe_queued = False # Flag if transcribe was queued while optimize running
        self.operation_lock = threading.Lock()  # Lock for thread-safe state management

        self.create_widgets()
        print("DEBUG: GUI initialisiert")

    def _on_loudness_preset_changed(self):
        """Handle loudness preset change - just log it"""
        preset = self.loudness_preset_var.get()
        self.log_status(f"Loudness Preset: {preset.capitalize()}")

    def _get_processing_mode(self):
        """Get processing mode from display text"""
        display_text = self.processing_mode_var.get()
        for key, value in self.mode_display_map.items():
            if value == display_text:
                return key
        return 'full'  # Default fallback

    def _setup_fonts(self):
        """Set up fonts with Ubuntu preference and DPI scaling"""
        global DEFAULT_FONT, BOLD_FONT, HEADING_FONT, MONO_FONT

        try:
            # Test if Ubuntu font is available
            test_font = font.Font(family="Ubuntu", size=10)
            DEFAULT_FONT = ('Ubuntu', SCALED_FONT_SIZE)
            BOLD_FONT = ('Ubuntu', SCALED_FONT_SIZE, 'bold')
            HEADING_FONT = ('Ubuntu', SCALED_FONT_SIZE_LARGE, 'bold')
            MONO_FONT = ('Ubuntu Mono', SCALED_FONT_SIZE - 1)
            print("DEBUG: Ubuntu-Schrift verfügbar - verwende Ubuntu")
        except tk.TclError:
            # Fallback to system defaults if Ubuntu not available
            print("DEBUG: Ubuntu-Schrift nicht verfügbar - verwende System-Standard")
            DEFAULT_FONT = ('TkDefaultFont', SCALED_FONT_SIZE)
            BOLD_FONT = ('TkDefaultFont', SCALED_FONT_SIZE, 'bold')
            HEADING_FONT = ('TkDefaultFont', SCALED_FONT_SIZE_LARGE, 'bold')
            MONO_FONT = ('TkFixedFont', SCALED_FONT_SIZE - 1)

        print(f"DEBUG: Font-Größe: {SCALED_FONT_SIZE}, DPI-Skalierung: {DPI_SCALE:.2f}")

    def create_widgets(self):
        # Top toolbar with two rows
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=5, pady=5)

        # ===== ROW 1: Labels and Mode (top row) =====
        row1_labels = ttk.Frame(toolbar)
        row1_labels.pack(fill="x", pady=(0, 2))

        # File picker button with Material Design outlined icon
        try:
            import os
            icon_path = os.path.join(os.path.dirname(__file__), '../assets/icons/folder_outlined_24.png')
            if os.path.exists(icon_path):
                from PIL import Image, ImageTk
                img = Image.open(icon_path)
                self.folder_icon = ImageTk.PhotoImage(img)
                file_btn = tk.Button(row1_labels, image=self.folder_icon, command=self._open_file_picker,
                                     relief=tk.FLAT, bd=0, padx=2, pady=2)
                file_btn.pack(side="left", padx=(0, 10))
            else:
                tk.Button(row1_labels, text="📁", font=DEFAULT_FONT,
                          command=self._open_file_picker).pack(side="left", padx=(0, 10))
        except Exception as e:
            tk.Button(row1_labels, text="📁", font=DEFAULT_FONT,
                      command=self._open_file_picker).pack(side="left", padx=(0, 10))

        # SR label
        tk.Label(row1_labels, text="SR (48kHz)", font=DEFAULT_FONT).pack(side="left", padx=(0, 20))

        # Loudness label
        tk.Label(row1_labels, text="Loudness Correction", font=DEFAULT_FONT).pack(side="left", padx=(0, 20))

        # Mode label
        tk.Label(row1_labels, text="Mode:", font=DEFAULT_FONT).pack(side="left", padx=(0, 5))

        # Mode dropdown
        self.processing_mode_var = tk.StringVar(value='full')
        self.mode_display_map = {
            'full': 'Vollständig (ClearVoice + SR + Loudness)',
            'loudness_only': 'Nur Loudness',
            'clearvoice_only': 'Nur ClearVoice (+ SR, keine Loudness)'
        }
        mode_dropdown = ttk.Combobox(row1_labels, textvariable=self.processing_mode_var,
                                      values=list(self.mode_display_map.values()),
                                      state='readonly', width=40, font=DEFAULT_FONT)
        mode_dropdown.pack(side="left", padx=(0, 50))
        mode_dropdown.set(self.mode_display_map['full'])

        # Action buttons
        self.process_btn = tk.Button(row1_labels, text="Optimieren", font=DEFAULT_FONT,
                                     command=self.process_files)
        self.process_btn.pack(side="left", padx=(0, 50))

        self.transcribe_btn = tk.Button(row1_labels, text="Transcribe", font=DEFAULT_FONT,
                                        command=self.transcribe_files, width=14)
        self.transcribe_btn.pack(side="left", padx=(0, 0))

        # ===== ROW 2: Controls (bottom row - all on same height) =====
        row2_controls = ttk.Frame(toolbar)
        row2_controls.pack(fill="x")

        # SR and Videomux vertical frame
        sr_video_frame = ttk.Frame(row2_controls)
        sr_video_frame.pack(side="left", padx=(0, 20))

        self.apply_sr_var = tk.BooleanVar(value=True)
        tk.Checkbutton(sr_video_frame, text="SR", font=DEFAULT_FONT,
                       variable=self.apply_sr_var).pack(anchor="w")

        self.remux_video_var = tk.BooleanVar(value=True)
        tk.Checkbutton(sr_video_frame, text="Videomux", font=DEFAULT_FONT,
                       variable=self.remux_video_var).pack(anchor="w")

        # Loudness preset selector (radio buttons only, no label)
        loudness_frame = ttk.Frame(row2_controls)
        loudness_frame.pack(side="left", padx=(0, 20))

        self.loudness_preset_var = tk.StringVar(value='moderate')

        tk.Radiobutton(loudness_frame, text="+", font=DEFAULT_FONT,
                       variable=self.loudness_preset_var, value='soft',
                       command=self._on_loudness_preset_changed).pack(side="left", padx=(0, 5))
        tk.Radiobutton(loudness_frame, text="++", font=DEFAULT_FONT,
                       variable=self.loudness_preset_var, value='moderate',
                       command=self._on_loudness_preset_changed).pack(side="left", padx=(0, 5))
        tk.Radiobutton(loudness_frame, text="+++", font=DEFAULT_FONT,
                       variable=self.loudness_preset_var, value='strong',
                       command=self._on_loudness_preset_changed).pack(side="left", padx=(0, 5))

        # Transcription format checkboxes (right aligned under Transcribe button)
        transcribe_format_frame = ttk.Frame(row2_controls)
        transcribe_format_frame.pack(side="right", padx=(0, 0))

        self.transcribe_txt_var = tk.BooleanVar(value=True)
        tk.Checkbutton(transcribe_format_frame, text="TXT", font=DEFAULT_FONT,
                       variable=self.transcribe_txt_var).pack(side="left", padx=(0, 10))

        self.transcribe_srt_var = tk.BooleanVar(value=True)
        tk.Checkbutton(transcribe_format_frame, text="SRT", font=DEFAULT_FONT,
                       variable=self.transcribe_srt_var).pack(side="left", padx=(0, 10))


        # Main content: Selected files and controls
        right_frame = ttk.Frame(self.root)
        right_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Selected files list
        list_container = ttk.Frame(right_frame)
        list_container.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")

        # Create simple Treeview for file list
        self.file_tree = ttk.Treeview(list_container, columns=("filename",),
                                      show="headings", yscrollcommand=scrollbar.set, height=10)
        self.file_tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_tree.yview)

        # Configure column
        self.file_tree.heading("filename", text="Dateiname")
        self.file_tree.column("filename", anchor="w")

        # Bind right-click for context menu
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
            # Add to treeview
            self.file_tree.insert("", "end", values=(os.path.basename(filepath),))
            self.log_status(f"+ {os.path.basename(filepath)}")

    def _on_treeview_right_click(self, event):
        """Handle right-click on treeview (context menu)"""
        item = self.file_tree.identify_row(event.y)
        if item:
            # If clicked item is not in selection, select only it
            if item not in self.file_tree.selection():
                self.file_tree.selection_set(item)

            # Get all selected items
            selected_items = self.file_tree.selection()

            # Show context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            if len(selected_items) == 1:
                context_menu.add_command(
                    label="Löschen",
                    command=lambda: self._delete_file_items(selected_items)
                )
            else:
                context_menu.add_command(
                    label=f"Alle {len(selected_items)} löschen",
                    command=lambda: self._delete_file_items(selected_items)
                )
            context_menu.post(event.x_root, event.y_root)

    def _delete_file_items(self, item_ids):
        """Delete multiple files from the list"""
        for item_id in item_ids:
            values = self.file_tree.item(item_id, "values")
            filename = values[0]
            # Find and remove from selected_files
            for i, f in enumerate(self.selected_files):
                if os.path.basename(f) == filename:
                    self.selected_files.pop(i)
                    break
            # Remove from treeview
            self.file_tree.delete(item_id)
            self.log_status(f"- {filename}")

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
        self.log_status("Liste geleert")

    def process_files(self):
        """Process all selected files"""
        if not self.selected_files:
            messagebox.showwarning("Keine Dateien", "Bitte erst Dateien hinzufügen!")
            return

        with self.operation_lock:
            # If transcribe is currently running, queue optimize instead
            if self.operation_running == 'transcribe':
                self.optimize_queued = True
                self.log_status("→ Optimierung wird nach Transkription gestartet...")
                return

            # Start optimize immediately
            self.operation_running = 'optimize'
            self.optimize_queued = False
            self.transcribe_queued = False

        self.process_btn.config(state="disabled", text="Optimiert...")
        thread = threading.Thread(target=self._process_files_thread, daemon=False)
        thread.start()

    def _process_files_thread(self):
        """Processing thread"""
        try:
            self.log_status("=" * 40)
            self.log_status("Starte Verarbeitung...")

            # Get processing mode
            mode = self._get_processing_mode()
            self.log_status(f"Modus: {self.mode_display_map[mode]}")

            # Load ClearVoice if needed (full or clearvoice_only modes)
            if mode in ['full', 'clearvoice_only']:
                self.log_status("Lade ClearVoice Modell...")
                try:
                    from clearvoice import ClearVoice
                    loudness_preset = self.loudness_preset_var.get()
                    if mode == 'full':
                        self.log_status(f"  Loudness Preset: {loudness_preset.capitalize()} (wird nach SR angewendet)")
                    # Load ClearVoice WITHOUT loudness - we apply it after SR (if full mode)
                    self.myClearVoice = ClearVoice(task='speech_enhancement',
                                                    model_names=['MossFormer2_SE_48K'],
                                                    apply_loudness_processing_flag=False)
                    self.log_status("Modell geladen!")
                except Exception as e:
                    self.log_status(f"FEHLER: {e}")
                    import traceback
                    self.log_status(traceback.format_exc())
                    self._enable_process_btn()
                    return

            # Process all selected files
            total = len(self.selected_files)
            for i, input_file in enumerate(self.selected_files, 1):
                self.log_status(f"\n[{i}/{total}] {os.path.basename(input_file)}")

                try:
                    folder = os.path.dirname(input_file)
                    base_name, ext = os.path.splitext(os.path.basename(input_file))
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    is_video = is_video_file(input_file)

                    # Determine which file to process based on mode
                    if mode == 'loudness_only':
                        # LOUDNESS ONLY MODE: Apply loudness to input file directly
                        final_audio = input_file
                        self.log_status(f"  Wende Loudness an...")
                    else:
                        # FULL or CLEARVOICE_ONLY MODE: Run ClearVoice pipeline

                        # Check if it's a video file - extract audio first
                        temp_audio = None
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
                        self.log_status(f"  Enhancement abgeschlossen")

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

                    # Apply loudness processing if in FULL mode
                    if mode == 'full':
                        loudness_preset = self.loudness_preset_var.get()
                        self.log_status(f"  Wende Loudness ({loudness_preset}) an...")
                        try:
                            import numpy as np
                            from clearvoice.utils.audio_processing import apply_dual_pass_loudness_processing, log_processing_stats
                            import soundfile as sf

                            # Read the audio file
                            audio_data, sr_value = sf.read(final_audio)

                            # Apply loudness processing with selected preset
                            processed_audio, stats = apply_dual_pass_loudness_processing(
                                audio_data, sr=sr_value, strength=loudness_preset
                            )

                            # Write back to the same file (overwrite)
                            sf.write(final_audio, processed_audio, sr_value)
                            self.log_status(f"    Loudness angewendet")
                            self.log_status(log_processing_stats(stats))
                        except Exception as loudness_error:
                            self.log_status(f"  FEHLER bei Loudness: {loudness_error}")
                            import traceback
                            self.log_status(traceback.format_exc())
                    elif mode == 'loudness_only':
                        # LOUDNESS ONLY: Apply loudness to the input file directly
                        loudness_preset = self.loudness_preset_var.get()
                        try:
                            import numpy as np
                            from clearvoice.utils.audio_processing import apply_dual_pass_loudness_processing, log_processing_stats
                            import soundfile as sf

                            # Read the audio file
                            audio_data, sr_value = sf.read(final_audio)

                            # Apply loudness processing with selected preset
                            processed_audio, stats = apply_dual_pass_loudness_processing(
                                audio_data, sr=sr_value, strength=loudness_preset
                            )

                            # Create output file with loudness-processed audio
                            loudness_path = os.path.join(folder, f"{base_name}-loudness-{timestamp}{ext}")
                            sf.write(loudness_path, processed_audio, sr_value)
                            self.log_status(f"    → {os.path.basename(loudness_path)}")
                            self.log_status(log_processing_stats(stats))
                        except Exception as loudness_error:
                            self.log_status(f"  FEHLER bei Loudness: {loudness_error}")
                            import traceback
                            self.log_status(traceback.format_exc())

                    # Remux video with cleaned audio if requested
                    if is_video and self.remux_video_var.get():
                        self.log_status("  Remuxe Video mit bereinigtem Audio...")
                        remuxed_path = os.path.join(folder, f"{base_name}-cleaned-{timestamp}{ext}")
                        try:
                            remux_video_with_audio(input_file, final_audio, remuxed_path)
                            self.log_status(f"  → {os.path.basename(remuxed_path)}")
                        except Exception as remux_error:
                            self.log_status(f"  ✗ Remuxing fehlgeschlagen: {remux_error}")

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
            # Check if transcribe was queued while we were processing
            with self.operation_lock:
                if self.transcribe_queued:
                    self.transcribe_queued = False
                    self.operation_running = None  # Clear optimize state
                    self._enable_process_btn()
                    # Automatically start transcription
                    self.log_status("\n" + "=" * 40)
                    self.log_status("→ Starte automatisch Transkription...")
                    self.root.after(100, self._start_transcribe_thread)
                else:
                    self.operation_running = None  # Clear optimize state
                    self._enable_process_btn()

    def transcribe_files(self):
        """Transcribe all selected files using aTrainCore"""
        if not self.selected_files:
            messagebox.showwarning("Keine Dateien", "Bitte erst Dateien auswählen!")
            return

        # Check if at least one output format is selected
        if not (self.transcribe_txt_var.get() or self.transcribe_srt_var.get()):
            messagebox.showwarning("Kein Format", "Bitte TXT oder SRT auswählen!")
            return

        with self.operation_lock:
            # If optimize is currently running, queue transcribe instead
            if self.operation_running == 'optimize':
                self.transcribe_queued = True
                self.log_status("→ Transkription wird nach Optimierung gestartet...")
                return

            # Start transcribe immediately
            self.operation_running = 'transcribe'
            self.optimize_queued = False
            self.transcribe_queued = False

        self.transcribe_btn.config(state="disabled", text="Transcribing...")
        thread = threading.Thread(target=self._transcribe_files_thread, daemon=False)
        thread.start()

    def _start_transcribe_thread(self):
        """Helper to start transcription from auto-trigger (already has lock released)"""
        self.transcribe_btn.config(state="disabled", text="Transcribing...")
        thread = threading.Thread(target=self._transcribe_files_thread, daemon=False)
        thread.start()

    def _transcribe_files_thread(self):
        """Background thread for transcription"""
        try:
            self.log_status("=" * 40)
            self.log_status("Starte Transkription...")

            total = len(self.selected_files)
            for idx, input_file in enumerate(self.selected_files, 1):
                filename = os.path.basename(input_file)
                self.log_status(f"\n[{idx}/{total}] Transkribiere: {filename}")

                try:
                    # Record time BEFORE transcription (before any operations)
                    before_time = datetime.datetime.now()

                    # Get output folder and base name
                    output_folder = os.path.dirname(input_file)
                    base_name = os.path.splitext(os.path.basename(input_file))[0]

                    # Check if aTrain environment is available
                    conda_cmd = (
                        "source ~/miniconda3/etc/profile.d/conda.sh && "
                        "conda activate atrain && "
                    )

                    # Build aTrainCore command
                    # Note: positional argument must come first, language defaults to auto-detect if not specified
                    transcribe_cmd = (
                        f"aTrain_core transcribe \"{input_file}\" "
                        f"--model large-v3-turbo "
                        f"--device GPU "
                        f"--compute_type float16"
                    )

                    cmd = ["bash", "-c", conda_cmd + transcribe_cmd]

                    self.log_status("  Starte aTrain_core...")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=600  # 10 minutes timeout
                    )

                    self.log_status(f"  DEBUG: aTrain returncode = {result.returncode}")
                    if result.returncode != 0:
                        self.log_status(f"  aTrain_core Fehler: {result.stderr[:500]}")
                        self.log_status(f"  aTrain stdout: {result.stdout[:500]}")
                        continue
                    else:
                        self.log_status(f"  aTrain_core erfolgreich")

                    # aTrainCore writes to ~/Documents/aTrain/transcriptions/
                    transcriptions_dir = os.path.expanduser("~/Documents/aTrain/transcriptions")
                    self.log_status(f"  Suche Transkriptionen in: {transcriptions_dir}")

                    # Check if directory exists
                    if not os.path.exists(transcriptions_dir):
                        self.log_status(f"  DEBUG: Verzeichnis existiert nicht!")
                        # Try to find transcriptions in current directory
                        transcriptions_dir = output_folder
                        self.log_status(f"  Versuche stattdessen: {transcriptions_dir}")

                    # Find newly created transcription files
                    # First try to find files newer than before_time, fallback to latest folder
                    transcript_files = self._find_transcription_files(transcriptions_dir, before_time)

                    # If no files found with time filter, try the newest folder
                    if not transcript_files:
                        self.log_status(f"  DEBUG: Keine neuen Dateien gefunden, versuche neuesten Ordner...")
                        transcript_files = self._find_latest_transcription_files(transcriptions_dir)

                    self.log_status(f"  DEBUG: Gefundene Dateien: {len(transcript_files)}")

                    if not transcript_files:
                        # List what's in the directory for debugging
                        try:
                            files_in_dir = os.listdir(transcriptions_dir) if os.path.exists(transcriptions_dir) else []
                            self.log_status(f"  DEBUG: Dateien im Verzeichnis: {files_in_dir[-5:]}")  # Last 5 files
                        except:
                            pass
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
            # Check if optimize was queued while we were transcribing
            with self.operation_lock:
                if self.optimize_queued:
                    self.optimize_queued = False
                    self.operation_running = None  # Clear transcribe state
                    self._enable_transcribe_btn()
                    # Automatically start optimization
                    self.log_status("\n" + "=" * 40)
                    self.log_status("→ Starte automatisch Optimierung...")
                    self.root.after(100, self._start_optimize_thread)
                else:
                    self.operation_running = None  # Clear transcribe state
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

    def _find_latest_transcription_files(self, transcriptions_dir):
        """Find transcription files in the most recently created folder"""
        if not os.path.exists(transcriptions_dir):
            return []

        # Find the newest folder
        try:
            folders = [
                os.path.join(transcriptions_dir, d)
                for d in os.listdir(transcriptions_dir)
                if os.path.isdir(os.path.join(transcriptions_dir, d))
            ]
            if not folders:
                return []

            newest_folder = max(folders, key=os.path.getmtime)

            # Find transcription files in this folder
            files = []
            for filename in os.listdir(newest_folder):
                if filename in ("transcription.txt", "transcription.srt"):
                    files.append(os.path.join(newest_folder, filename))

            return files
        except Exception as e:
            self.log_status(f"  DEBUG: Fehler beim Suchen des neuesten Ordners: {e}")
            return []

    def _start_optimize_thread(self):
        """Helper to start optimization from auto-trigger (already has lock released)"""
        self.process_btn.config(state="disabled", text="Optimiert...")
        thread = threading.Thread(target=self._process_files_thread, daemon=False)
        thread.start()

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
