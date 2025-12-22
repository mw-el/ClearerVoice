"""
Loudness Processing Presets for Dual-Pass Adaptive Compression
===============================================================

This module defines compression ratio presets for different audio dynamics levels.
Used in adaptive compression to handle whispers, normal speech, and loud segments
with appropriate gain reduction.

Two Preset Strategies:
  MODERATE: For already-processed audio files (gentle lifting)
    Pass 1: 7:1, 4:1, 2:1 ratios
    Pass 2: 3:1, 2:1, 1:1 ratios

  STRONG: For original/raw audio files (aggressive rescue of quiet segments)
    Pass 1: 10:1, 5:1, 2:1 ratios
    Pass 2: 4:1, 2:1, 1:1 ratios

Adjust the RATIO values here to tune the loudness processing behavior.
Lower ratio = less compression (more dynamic)
Higher ratio = more compression (flatter, more processed)
"""


class AdaptiveCompressionRatios:
    """
    Define compression ratios for different audio levels.

    Audio Levels:
    - WHISPER: Very quiet speech (-40 to -25 dB RMS)
    - NORMAL: Normal conversational speech (-25 to -15 dB RMS)
    - LOUD: Loud speech or shouting (-15 to -5 dB RMS)

    Three presets available: SOFT, MODERATE, and STRONG
    """

    class Soft:
        """
        Soft Preset: For gentle loudness enhancement with minimal artifacts.

        Use this for:
        - Audio that has already been through some processing
        - When you want subtle enhancement
        - To avoid over-processing artifacts
        """
        class PassOne:
            """Soft Pass 1: Very gentle lifting of quiet segments"""
            WHISPER_RATIO = 4.0   # 4:1 - gentle on quiet parts
            NORMAL_RATIO = 2.5    # 2.5:1 - very light on normal speech
            LOUD_RATIO = 1.5      # 1.5:1 - minimal on loud parts

            THRESHOLD_DB = -18.0  # Higher threshold = less compression
            ATTACK_MS = 40.0      # Slower attack for smoothness
            RELEASE_MS = 200.0    # Slow release to breathe
            KNEE_WIDTH_DB = 5.0   # Wide knee for soft transition

        class PassTwo:
            """Soft Pass 2: Minimal smoothing"""
            WHISPER_RATIO = 1.5   # 1.5:1 - barely any compression
            NORMAL_RATIO = 1.2    # 1.2:1 - almost no compression
            LOUD_RATIO = 1.0      # 1:1 - no compression on loud

            THRESHOLD_DB = -16.0  # Higher threshold
            ATTACK_MS = 50.0      # Very slow attack
            RELEASE_MS = 250.0    # Very slow release
            KNEE_WIDTH_DB = 6.0   # Very soft knee

    class Moderate:
        """
        Moderate Preset: For already-processed or less dynamic audio.

        Use this for:
        - Audio files that have already been through loudness processing
        - Less dynamic recordings
        - When you want subtle, gentle loudness enhancement
        """
        class PassOne:
            """Moderate Pass 1: Gentle lifting of quiet segments"""
            WHISPER_RATIO = 7.0   # 7:1 - moderate on quiet parts
            NORMAL_RATIO = 4.0    # 4:1 - light on normal speech
            LOUD_RATIO = 2.0      # 2:1 - minimal on loud parts

            THRESHOLD_DB = -20.0  # Where compression kicks in
            ATTACK_MS = 30.0      # Slightly slower to avoid pumping
            RELEASE_MS = 150.0    # Let it breathe
            KNEE_WIDTH_DB = 3.0   # Soft knee for smooth transition

        class PassTwo:
            """Moderate Pass 2: Gentle smoothing"""
            WHISPER_RATIO = 3.0   # 3:1 - light compression
            NORMAL_RATIO = 2.0    # 2:1 - very light on normal speech
            LOUD_RATIO = 1.0      # 1:1 - basically no compression on loud

            THRESHOLD_DB = -18.0  # Slightly higher threshold
            ATTACK_MS = 20.0      # Quick response
            RELEASE_MS = 100.0    # Natural release
            KNEE_WIDTH_DB = 4.0   # Softer knee for smoothness

    class Strong:
        """
        Strong Preset: For original/raw audio with high dynamic range.

        Use this for:
        - Original, unprocessed audio recordings
        - Highly variable speaker dynamics
        - When you need aggressive rescue of whispered passages
        """
        class PassOne:
            """Strong Pass 1: Aggressive lifting of quiet segments"""
            WHISPER_RATIO = 10.0  # 10:1 - very aggressive on quiet parts
            NORMAL_RATIO = 5.0    # 5:1 - moderate aggression on normal speech
            LOUD_RATIO = 2.0      # 2:1 - minimal on loud parts

            THRESHOLD_DB = -20.0  # Where compression kicks in
            ATTACK_MS = 30.0      # Slightly slower to avoid pumping
            RELEASE_MS = 150.0    # Let it breathe
            KNEE_WIDTH_DB = 3.0   # Soft knee for smooth transition

        class PassTwo:
            """Strong Pass 2: Standard smoothing"""
            WHISPER_RATIO = 4.0   # 4:1 - standard gentle compression
            NORMAL_RATIO = 2.0    # 2:1 - very light on normal speech
            LOUD_RATIO = 1.0      # 1:1 - basically no compression on loud

            THRESHOLD_DB = -18.0  # Slightly higher threshold
            ATTACK_MS = 20.0      # Quick response
            RELEASE_MS = 100.0    # Natural release
            KNEE_WIDTH_DB = 4.0   # Softer knee for smoothness

    # Backward compatibility: Default to Strong
    class PassOne(Strong.PassOne):
        pass

    class PassTwo(Strong.PassTwo):
        pass


class DynamicsAnalysisThresholds:
    """
    Thresholds for categorizing audio into Whisper/Normal/Loud buckets.

    These are RMS (Root Mean Square) values in dB that define the boundaries.
    Audio segments are analyzed and classified into categories.
    """
    WHISPER_UPPER_LIMIT = -25.0   # Anything quieter is "whisper"
    NORMAL_UPPER_LIMIT = -15.0    # Whisper to Normal boundary
    # Anything louder than -15 dB is "Loud"

    ANALYSIS_WINDOW_MS = 100  # Analyze in 100ms windows for granularity


# Tuning Guide:
# ==============
#
# CHOOSING PRESET (via loudness_strength parameter in ClearVoice):
# ================================================================
#
# Use 'strong' (default) for:
#   - Original, unprocessed audio recordings
#   - High dynamic range with many whispered passages
#   - First-time processing of podcast audio
#
# Use 'moderate' for:
#   - Audio that's already been through loudness processing
#   - Less dynamic recordings
#   - When you want subtle, gentle enhancement (not aggressive rescue)
#
#
# ADJUSTING PARAMETERS:
# =====================
#
# If output is too quiet:
#   - Increase PassOne.WHISPER_RATIO and NORMAL_RATIO
#   - Lower the thresholds (more negative values, e.g., -22 dB)
#
# If output sounds too "pumpy" or over-processed:
#   - Decrease PassOne ratios
#   - Increase KNEE_WIDTH for smoother transitions
#   - Increase ATTACK_MS and RELEASE_MS for slower response
#
# If it sounds unnatural (plastic/compressed):
#   - PassTwo ratios are too aggressive - reduce them
#   - Increase PassTwo.ATTACK_MS and RELEASE_MS
#   - Make sure PassTwo KNEE_WIDTH is gentle (3-5 dB)
#
# If whispers are STILL hard to hear with 'moderate':
#   - Try 'strong' preset instead
#   - Or increase Moderate.PassOne.WHISPER_RATIO to 8 or 9
#
#
# EXAMPLES:
# =========
#
# For raw podcast audio with very soft speakers:
#   Use 'strong' preset (current defaults)
#
# For already-processed audio that just needs slight adjustment:
#   Use 'moderate' preset
#
# For extremely dynamic audio (big difference between whispers and normal):
#   Use 'strong' and maybe increase PassOne ratios to 12:1, 6:1, 2:1
