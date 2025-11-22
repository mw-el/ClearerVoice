#!/usr/bin/env python3
"""Test script to verify MP3 processing works"""
import sys
import os

# Change to the correct directory
os.chdir('/home/matthias/_AA_Clearervoice')

# Add clearvoice to path
sys.path.insert(0, '/home/matthias/_AA_Clearervoice')

print("=" * 60)
print("Testing ClearVoice with MP3 file")
print("=" * 60)

from clearvoice.clearvoice import ClearVoice

# Test MP3 file
test_mp3 = 'clearvoice/samples/path_to_output_wavs/MossFormer2_SE_48K/speech1.mp3'

if not os.path.exists(test_mp3):
    print(f"ERROR: Test file not found: {test_mp3}")
    sys.exit(1)

print(f"\nTest file: {test_mp3}")
print(f"File exists: {os.path.exists(test_mp3)}")
print(f"File size: {os.path.getsize(test_mp3)} bytes")

print("\n" + "=" * 60)
print("Initializing ClearVoice model...")
print("=" * 60)

try:
    myClearVoice = ClearVoice(task='speech_enhancement', model_names=['MossFormer2_SE_48K'])
    print("✓ Model initialized successfully!")
except Exception as e:
    print(f"✗ Model initialization FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Processing MP3 file...")
print("=" * 60)

try:
    output_wav = myClearVoice(input_path=test_mp3, online_write=False)
    print("✓ MP3 file processed successfully!")
    print(f"Output type: {type(output_wav)}")
except Exception as e:
    print(f"✗ Processing FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Writing output file...")
print("=" * 60)

output_path = '/tmp/test_output.wav'
try:
    myClearVoice.write(output_wav, output_path=output_path)
    print(f"✓ Output written to: {output_path}")
    print(f"Output file exists: {os.path.exists(output_path)}")
    if os.path.exists(output_path):
        print(f"Output file size: {os.path.getsize(output_path)} bytes")
except Exception as e:
    print(f"✗ Writing output FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
