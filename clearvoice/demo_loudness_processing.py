"""
Demo: Using Loudness Processing for Podcast Audio

This demo shows how to use the new loudness normalization and dynamic range
compression features for professional podcast audio processing.

The processing chain works as follows:
1. Speech Enhancement (via MossFormer2_SE_48K) - removes background noise
2. Loudness Normalization (to -16 LUFS) - ensures consistent perceived loudness
3. Dynamic Range Compression (4:1 ratio) - makes quiet parts louder, loud parts softer
4. Peak Limiting (at -1 dB) - prevents clipping

See clearvoice/utils/loudness_settings.py for detailed parameter documentation.
"""

from clearvoice import ClearVoice
import os

# ==============================================================================
# EXAMPLE 1: Speech Enhancement ONLY (traditional approach)
# ==============================================================================
if False:
    print("\n" + "="*60)
    print("EXAMPLE 1: Only Speech Enhancement")
    print("="*60)

    # Create ClearVoice with apply_loudness_processing_flag=False
    myClearVoice = ClearVoice(
        task='speech_enhancement',
        model_names=['MossFormer2_SE_48K'],
        apply_loudness_processing_flag=False  # <- No loudness processing
    )

    # Process a single audio file
    input_file = 'samples/input.wav'
    if os.path.exists(input_file):
        print(f"Processing: {input_file}")
        output_wav = myClearVoice(input_path=input_file, online_write=False)
        myClearVoice.write(output_wav, output_path='samples/output_se_only.wav')
        print("✓ Saved as: samples/output_se_only.wav")


# ==============================================================================
# EXAMPLE 2: Speech Enhancement + Loudness Optimization (recommended for podcasts)
# ==============================================================================
if True:
    print("\n" + "="*60)
    print("EXAMPLE 2: Speech Enhancement + Loudness Optimization")
    print("="*60)

    # Create ClearVoice with apply_loudness_processing_flag=True
    myClearVoice = ClearVoice(
        task='speech_enhancement',
        model_names=['MossFormer2_SE_48K'],
        apply_loudness_processing_flag=True  # <- Enable loudness processing!
    )

    # Process a single audio file
    input_file = 'samples/input.wav'
    if os.path.exists(input_file):
        print(f"Processing: {input_file}")
        print("  Step 1: Speech Enhancement (noise reduction)")
        print("  Step 2: Loudness Normalization (to -16 LUFS)")
        print("  Step 3: Dynamic Range Compression (4:1 ratio)")
        print("  Step 4: Peak Limiting (at -1 dB)")

        output_wav = myClearVoice(input_path=input_file, online_write=False)
        myClearVoice.write(output_wav, output_path='samples/output_se_loudness.wav')
        print("\n✓ Saved as: samples/output_se_loudness.wav")
        print("\nThe output should sound:")
        print("  - Cleaner (noise removed)")
        print("  - Louder and more consistent")
        print("  - Professional and podcast-ready")
    else:
        print(f"⚠ File not found: {input_file}")


# ==============================================================================
# EXAMPLE 3: Batch processing multiple files with loudness optimization
# ==============================================================================
if False:
    print("\n" + "="*60)
    print("EXAMPLE 3: Batch Processing with Loudness Optimization")
    print("="*60)

    myClearVoice = ClearVoice(
        task='speech_enhancement',
        model_names=['MossFormer2_SE_48K'],
        apply_loudness_processing_flag=True
    )

    # Process all wav files in input directory
    input_dir = 'samples/path_to_input_wavs'
    output_dir = 'samples/path_to_output_wavs_loudness'

    if os.path.exists(input_dir):
        print(f"Processing all audio files in: {input_dir}")
        print(f"Output directory: {output_dir}")
        myClearVoice(input_path=input_dir, online_write=True, output_path=output_dir)
        print("✓ Batch processing complete!")
    else:
        print(f"⚠ Directory not found: {input_dir}")


# ==============================================================================
# EXAMPLE 4: Advanced - Customizing loudness processing settings
# ==============================================================================
if False:
    print("\n" + "="*60)
    print("EXAMPLE 4: Advanced - Custom Loudness Settings")
    print("="*60)

    # To customize loudness processing, you would need to modify
    # clearvoice/utils/loudness_settings.py before creating the ClearVoice object.
    #
    # Key parameters you can adjust:
    # - LoudnessNormalization.TARGET_LUFS (default: -16.0)
    # - DynamicRangeCompressor.RATIO (default: 4.0)
    # - DynamicRangeCompressor.THRESHOLD (default: -20.0 dB)
    # - DynamicRangeCompressor.ATTACK_TIME_MS (default: 20.0)
    # - DynamicRangeCompressor.RELEASE_TIME_MS (default: 100.0)

    print("Loudness processing parameters are defined in:")
    print("  clearvoice/utils/loudness_settings.py")
    print("\nEach parameter has detailed documentation explaining:")
    print("  - What it controls")
    print("  - Recommended range of values")
    print("  - How changes affect the sound")
    print("\nBefore adjusting parameters, read the comments in loudness_settings.py!")


# ==============================================================================
# NOTES FOR PODCAST PRODUCERS
# ==============================================================================
"""
Why use loudness processing for podcasts?

1. CONSISTENCY across different speakers and recording conditions
   - Some speakers are naturally louder/quieter than others
   - Loudness processing normalizes these differences

2. PROFESSIONAL SOUND
   - Listeners don't have to adjust volume constantly
   - Sounds "radio-ready" and polished
   - Better compatibility across all playback devices

3. LOUDNESS STANDARDS
   - Apple Podcasts recommend -16 LUFS
   - Spotify uses -14 LUFS
   - This tool normalizes to -16 LUFS by default

4. DYNAMIC RANGE COMPRESSION
   - Makes quiet parts audible (e.g., whispers)
   - Prevents loud parts from clipping (e.g., shouting, emphasis)
   - The 4:1 ratio is gentle enough to sound natural

Processing Order Matters:
1. Enhancement First: Clean up the signal (remove noise)
2. Then Normalize: Once it's clean, ensure consistent loudness
3. Then Compress: Smooth out remaining dynamics
4. Then Limit: Prevent any peaks from clipping

This order is automatic in this tool - just enable loudness processing!
"""
