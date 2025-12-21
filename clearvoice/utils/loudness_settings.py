"""
Loudness Processing Settings for Podcast Audio
================================================

This module contains all configuration parameters for loudness normalization and
dynamic range compression, optimized for podcast voice tracks.

The processing chain uses industry-standard LUFS (Loudness Units relative to Full Scale)
normalization combined with a gentle dynamic range compressor to ensure consistent,
professional-sounding podcast audio.

Processing Order:
1. Speech Enhancement (MossFormer, FRCRN, etc.) - optional
2. Loudness Normalization (LUFS-based) - mandatory in this processing
3. Dynamic Range Compression - mandatory in this processing
4. Peak Limiting - safety mechanism

For detailed information about why these settings work for podcasts, see:
- https://www.descript.com/blog/article/podcast-loudness-standard-getting-the-right-volume
- https://auphonic.com/blog/2011/07/25/loudness-normalization-and-compression-podcasts-and-speech-audio/
"""

# ==============================================================================
# LOUDNESS NORMALIZATION SETTINGS (LUFS-based)
# ==============================================================================

class LoudnessNormalization:
    """
    LUFS (Loudness Units relative to Full Scale) Normalization

    LUFS is the industry standard for measuring perceived loudness and is much
    better than peak normalization for speech/podcasts. Unlike peak normalization
    which only looks at the highest volume spike, LUFS measures how loud the audio
    actually sounds to the human ear.

    Standards by Platform:
    - Apple Podcasts: -16 LUFS (de facto podcast standard)
    - Spotify: -14 LUFS (slightly louder)
    - YouTube: -13 LUFS (music-oriented)
    - Radio/Broadcast: -23 LUFS (more conservative)

    For most podcasts, -16 LUFS is the best choice.
    """

    # Target loudness for podcast audio
    TARGET_LUFS = -16.0
    # Range: -20 to -14 LUFS
    # Lower (e.g., -20) = quieter, more dynamic, more natural but might get drowned out
    # Higher (e.g., -14) = louder, more aggressive, better presence in noisy environments
    # Default -16 LUFS is the "Goldilocks" zone for podcasts

    # Integrated loudness (long-term average) calculation window
    # Standard is 3 seconds (Leq(A) 3s) for measuring perceived loudness
    INTEGRATION_WINDOW = 3.0  # seconds

    # True Peak limit - prevents clipping and ensures compatibility across all platforms
    TRUE_PEAK_LIMIT = -1.0  # dB
    # Must stay below 0 dB to prevent digital clipping
    # -1 dB provides 1 dB headroom for safety
    # Range: 0 to -3 dB
    #   -1 dB: standard, safe margin
    #   -2 dB: very conservative, extra safe
    #   -3 dB: overkill, risks being too quiet on some platforms


# ==============================================================================
# DYNAMIC RANGE COMPRESSOR SETTINGS
# ==============================================================================

class DynamicRangeCompressor:
    """
    Compressor reduces the volume difference between quiet and loud parts,
    making speech more consistent and "professional" sounding.

    How it works:
    - When audio goes above THRESHOLD, it gets compressed by the RATIO
    - ATTACK controls how quickly compression activates
    - RELEASE controls how quickly compression releases
    - KNEE makes the transition smooth instead of hard

    For podcasts, we use GENTLE compression to maintain naturalness while
    improving consistency.
    """

    # RATIO: How much to reduce volume above threshold
    RATIO = 4.0
    # Range: 2:1 to 8:1
    # 2:1 = very subtle (barely noticeable)
    # 4:1 = ideal for podcasts (controlled but natural)
    # 6:1 = more aggressive (noticeably more controlled)
    # 8:1+ = very aggressive (can sound artificial if overdone)
    #
    # What it means:
    # If threshold is -20 dB and ratio is 4:1, and audio hits -10 dB (10 dB above threshold),
    # then it gets compressed to: threshold + (10 dB / 4) = -20 + 2.5 = -17.5 dB
    # So a 10 dB overshoot becomes only 2.5 dB

    # THRESHOLD: The level above which compression starts
    THRESHOLD = -20.0  # dB
    # Range: -40 to 0 dB
    # Lower (e.g., -30) = more compression (more aggressive leveling)
    # Higher (e.g., -10) = less compression (more natural, only catches peaks)
    #
    # For podcasts:
    # -20 dB = good default (catches loud moments but preserves dynamics)
    # -25 dB = more aggressive compression (good for very dynamic speakers)
    # -15 dB = subtle compression (minimal intervention)
    #
    # To find the right threshold for your audio:
    # 1. Look at the waveform
    # 2. Find the level of normal speaking volume
    # 3. Set threshold 5-10 dB below that level

    # ATTACK TIME: How fast compression kicks in (in milliseconds)
    ATTACK_TIME_MS = 20.0
    # Range: 3 to 50 ms
    # 3-5 ms = very fast (catches transients, can sound clicky with speech)
    # 20-30 ms = ideal for speech (natural sounding, still controls peaks)
    # 50+ ms = slow (misses quick peaks, more natural but less controlled)
    #
    # For podcasts, 20-30 ms prevents unnaturally fast compression pumping
    # while still controlling volume spikes (shouting, emphasis).

    # RELEASE TIME: How fast compression releases after dropping below threshold (milliseconds)
    RELEASE_TIME_MS = 100.0
    # Range: 50 to 300 ms
    # 50 ms = fast release (can sound "pumpy" - volume pumping in/out)
    # 100 ms = ideal for speech (smooth, natural recovery)
    # 200+ ms = slow release (smooth but can feel sluggish)
    #
    # If release is too fast: audio sounds like it's "breathing" (pumping effect)
    # If release is too slow: compressed state lingers too long unnaturally
    # 100 ms is the sweet spot for voice: noticeable but not artificial

    # KNEE WIDTH: How gradual is the compression curve (in dB)
    KNEE_WIDTH = 2.0
    # Range: 0 to 6 dB
    # 0 dB = hard knee (abrupt transition at threshold, can sound unnatural)
    # 2-4 dB = soft knee (smooth transition, sounds natural)
    # 6+ dB = very soft knee (barely noticeable compression start)
    #
    # Soft knee is essential for speech because it prevents the obvious
    # "compression kicking in" sound that makes audio sound processed.

    # MAKEUP GAIN: Automatic gain compensation to bring level back up
    # This is calculated automatically as: RATIO * (peak - THRESHOLD)
    # but typically 3-6 dB for podcast processing
    MAKEUP_GAIN_DB = 4.0  # will be calculated automatically, this is a reference
    # This ensures the output is as loud as the input overall, even though
    # the dynamics are compressed. Without this, the audio would sound duller.


# ==============================================================================
# PEAK LIMITER SETTINGS (Safety mechanism)
# ==============================================================================

class PeakLimiter:
    """
    A limiter is a compressor with infinite ratio (1:∞).
    It acts as a safety valve - anything above the threshold gets
    hard-clamped to prevent clipping.

    This is different from the main compressor: while the compressor
    gradually controls dynamics, the limiter prevents hard clipping.
    """

    # THRESHOLD: Maximum allowed peak level
    THRESHOLD = -1.0  # dB
    # Must match TRUE_PEAK_LIMIT in LoudnessNormalization
    # Prevents any peaks from exceeding this level (hard brick-wall limiting)

    # ATTACK TIME: Should be very fast to catch peaks
    ATTACK_TIME_MS = 3.0
    # Must be fast enough to prevent even single samples from clipping
    # 3 ms is standard for limiters

    # RELEASE TIME: Fast but not so fast as to cause artifacts
    RELEASE_TIME_MS = 50.0
    # Should be fast enough to recover smoothly after peaks


# ==============================================================================
# OVERALL PROCESSING CONFIGURATION
# ==============================================================================

class ProcessingConfig:
    """
    Master configuration for the complete loudness processing chain.
    """

    # Enable/disable each stage of processing
    ENABLE_LOUDNESS_NORMALIZATION = True
    ENABLE_COMPRESSOR = True
    ENABLE_LIMITER = True

    # Whether to measure and display LUFS before and after processing
    MEASURE_LOUDNESS = True

    # How many samples to use for LUFS measurement (for efficiency)
    # Higher = more accurate but slower
    # For real-time or batch processing, using the full waveform is fine
    MEASUREMENT_CHUNK_SIZE = None  # None = use full waveform

    # Linear gain applied uniformly across the entire audio (after compression)
    # This is different from makeup gain in the compressor
    # Useful for fine-tuning if the overall output is still too quiet/loud
    FINAL_GAIN_ADJUSTMENT_DB = 0.0
    # Range: -6 to +6 dB
    # 0 = no additional gain adjustment
    # Positive = louder output
    # Negative = quieter output


# ==============================================================================
# QUICK REFERENCE: COMMON SCENARIOS
# ==============================================================================

"""
SCENARIO 1: Consistent, controlled speaker (e.g., one host)
    LoudnessNormalization.TARGET_LUFS = -16.0
    DynamicRangeCompressor.RATIO = 4.0
    DynamicRangeCompressor.THRESHOLD = -20.0
    → This is the DEFAULT - safe choice for most podcasts

SCENARIO 2: Very dynamic speaker (lots of quiet/loud variation)
    DynamicRangeCompressor.RATIO = 5.0
    DynamicRangeCompressor.THRESHOLD = -25.0
    → More aggressive compression to tame dynamics

SCENARIO 3: Natural, minimal processing (preserve dynamics)
    DynamicRangeCompressor.RATIO = 3.0
    DynamicRangeCompressor.THRESHOLD = -15.0
    → Lighter touch, only catches major peaks

SCENARIO 4: Loud, aggressive podcast (radio-like presence)
    LoudnessNormalization.TARGET_LUFS = -14.0
    DynamicRangeCompressor.RATIO = 4.5
    ProcessingConfig.FINAL_GAIN_ADJUSTMENT_DB = +2.0
    → Louder overall, more compressed for "radio" sound

SCENARIO 5: Very quiet source that needs boosting
    DynamicRangeCompressor.THRESHOLD = -30.0
    ProcessingConfig.FINAL_GAIN_ADJUSTMENT_DB = +3.0
    → Lower threshold compresses more, final gain boost helps
"""
