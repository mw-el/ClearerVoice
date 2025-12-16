import tkinter as tk
from tkinter import filedialog
from clearvoice import ClearVoice

# Create the root window with className for proper desktop integration
# This ensures the window is correctly identified in the dock with the right icon
root = tk.Tk(className='clearervoice')
root.withdraw()

# Ask user to select an input audio file
input_file = filedialog.askopenfilename(
    title="Select an audio file",
    filetypes=[("Audio Files", "*.wav *.mp3 *.flac"), ("All Files", "*.*")]
)
if not input_file:
    print("No file selected. Exiting.")
    exit()

# Ask user to select a location and name for the output file
output_file = filedialog.asksaveasfilename(
    title="Save enhanced audio as",
    defaultextension=".wav",
    filetypes=[("WAV Files", "*.wav"), ("All Files", "*.*")]
)
if not output_file:
    print("No output file selected. Exiting.")
    exit()

# Create a ClearVoice instance for speech enhancement using the MossFormer2_SE_48K model
myClearVoice = ClearVoice(task='speech_enhancement', model_names=['MossFormer2_SE_48K'])

# Process the selected input file (returns the enhanced audio)
output_wav = myClearVoice(input_path=input_file, online_write=False)

# Save the enhanced audio to the selected output file
myClearVoice.write(output_wav, output_path=output_file)

print(f"Processing complete. Output saved to {output_file}")

