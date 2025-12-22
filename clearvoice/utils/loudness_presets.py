"""
Loudness Processing Presets for Dual-Pass Adaptive Compression
===============================================================

This module defines compression ratio presets for different audio dynamics levels.
Used in adaptive compression to handle whispers, normal speech, and loud segments
with appropriate gain reduction.

Two-Pass Strategy:
  Pass 1 (Aggressive): Rescue quiet segments, lift them significantly
  Pass 2 (Normal): Smooth everything out, natural-sounding normalization

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
    """

    class PassOne:
        """
        Aggressive Pass: Targets rescue of quiet segments.

        Higher ratios to aggressively compress and lift quiet material.
        This pass is meant to bring up the floor - make whispers audible.
        """
        WHISPER_RATIO = 10.0  # 10:1 - very aggressive on quiet parts
        NORMAL_RATIO = 5.0    # 5:1 - moderate aggression on normal speech
        LOUD_RATIO = 2.0      # 2:1 - minimal on loud parts

        THRESHOLD_DB = -20.0  # Where compression kicks in
        ATTACK_MS = 30.0      # Slightly slower to avoid pumping
        RELEASE_MS = 150.0    # Let it breathe
        KNEE_WIDTH_DB = 3.0   # Soft knee for smooth transition

    class PassTwo:
        """
        Normal Pass: Smooth and naturalize the output.

        Standard, gentle ratios for final polishing.
        This pass evens out Pass 1's work and makes it sound natural.
        """
        WHISPER_RATIO = 4.0   # 4:1 - standard gentle compression
        NORMAL_RATIO = 2.0    # 2:1 - very light on normal speech
        LOUD_RATIO = 1.0      # 1:1 - basically no compression on loud

        THRESHOLD_DB = -18.0  # Slightly higher threshold
        ATTACK_MS = 20.0      # Quick response
        RELEASE_MS = 100.0    # Natural release
        KNEE_WIDTH_DB = 4.0   # Softer knee for smoothness


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
# ============
# If output is too quiet:
#   - Increase PassOne.WHISPER_RATIO and NORMAL_RATIO
#   - Lower the thresholds (more negative values)
#
# If output sounds too "pumpy" or over-processed:
#   - Decrease PassOne ratios
#   - Increase KNEE_WIDTH for smoother transitions
#   - Increase ATTACK_MS and RELEASE_MS
#
# If it sounds unnatural:
#   - PassTwo ratios are too aggressive
#   - Increase PassTwo.ATTACK_MS and RELEASE_MS
#   - Make sure PassTwo KNEE_WIDTH is gentle
#
# For testing:
#   Try running with just PassOne to hear aggressive lifting
#   Then enable PassTwo to hear how it smooths things
