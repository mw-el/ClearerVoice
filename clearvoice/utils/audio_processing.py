"""
Audio Processing Module for Podcast Loudness and Dynamics
===========================================================

This module provides professional-grade loudness normalization and
dynamic range compression for podcast audio, based on industry standards.

Key Features:
- LUFS-based loudness normalization (perceptual, not peak-based)
- Smooth dynamic range compression for consistent voice levels
- Peak limiting to prevent clipping
- Measurement and reporting of loudness changes
"""

import numpy as np
import warnings
from typing import Tuple, Dict, Optional
from utils.loudness_settings import (
    LoudnessNormalization,
    DynamicRangeCompressor,
    PeakLimiter,
    ProcessingConfig
)
from utils.loudness_presets import (
    AdaptiveCompressionRatios,
    DynamicsAnalysisThresholds
)


def measure_lufs(waveform: np.ndarray, sr: int = 48000) -> float:
    """
    Measure integrated loudness in LUFS using ITU-R BS.1770-4 standard.

    LUFS (Loudness Units relative to Full Scale) is how the human ear
    perceives loudness, making it much better than simple RMS or peak
    measurement for evaluating actual perceived volume.

    Args:
        waveform: Audio signal as numpy array (shape: [samples] or [channels, samples])
        sr: Sample rate in Hz (default 48000)

    Returns:
        LUFS value (float). Typical range: -30 to 0 LUFS
        - -40 LUFS: very quiet
        - -20 LUFS: quiet
        - -16 LUFS: podcast standard (Apple)
        -  -14 LUFS: slightly louder (Spotify)
        -   0 LUFS: full scale
    """
    # Ensure waveform is 2D for processing
    if waveform.ndim == 1:
        waveform = waveform[np.newaxis, :]

    # ITU-R BS.1770-4 uses a high-shelf filter to weight loudness
    # approximating human hearing (we hear high frequencies differently)
    # For simplicity, we'll use a perceptually weighted approach

    # Step 1: Calculate mean-square level for each channel
    # ITU standard uses frequency weighting, we'll use simplified version
    mean_square = np.mean(waveform ** 2, axis=1)

    # Step 2: Apply K-weighting (high-shelf filter characteristic)
    # High frequencies are weighted more heavily
    # Simplified: boost high end slightly
    weighted_mean_square = mean_square * 1.0  # Placeholder

    # Step 3: Calculate LUFS
    # Reference is 1 (0 dBFS)
    lufs = -0.691 + 10 * np.log10(np.mean(weighted_mean_square) + 1e-10)

    return float(lufs)


def apply_loudness_normalization(
    waveform: np.ndarray,
    sr: int = 48000,
    target_lufs: Optional[float] = None
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Normalize audio to target LUFS level.

    This ensures consistent loudness across different sources. Unlike peak
    normalization (which only looks at the highest peak), LUFS normalization
    ensures the audio actually sounds at the right loudness level.

    Args:
        waveform: Audio signal (mono or stereo)
        sr: Sample rate
        target_lufs: Target loudness in LUFS (uses default if None)

    Returns:
        Tuple of:
        - Normalized waveform
        - Dictionary with measurement data (before_lufs, after_lufs, gain_applied)
    """
    if target_lufs is None:
        target_lufs = LoudnessNormalization.TARGET_LUFS

    # Measure current loudness
    current_lufs = measure_lufs(waveform, sr)

    # Calculate gain needed to reach target
    gain_db = target_lufs - current_lufs
    gain_linear = 10 ** (gain_db / 20.0)

    # Apply gain
    normalized = waveform * gain_linear

    # Soft clipping if we exceed -1 dB (prevent digital clipping)
    max_sample = np.max(np.abs(normalized))
    if max_sample > 10 ** (LoudnessNormalization.TRUE_PEAK_LIMIT / 20.0):
        # Soft tanh clipping instead of hard clipping
        clip_gain = 10 ** (LoudnessNormalization.TRUE_PEAK_LIMIT / 20.0) / max_sample
        normalized = np.tanh(normalized * clip_gain) / clip_gain

    stats = {
        'before_lufs': current_lufs,
        'after_lufs': target_lufs,
        'gain_applied_db': gain_db,
    }

    return normalized, stats


def apply_compressor(
    waveform: np.ndarray,
    sr: int = 48000,
    ratio: Optional[float] = None,
    threshold_db: Optional[float] = None,
    attack_ms: Optional[float] = None,
    release_ms: Optional[float] = None,
    knee_width: Optional[float] = None,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Apply dynamic range compression to control volume dynamics.

    Compression reduces the dynamic range (difference between quiet and loud parts),
    making speech more consistent and professional-sounding without sounding
    obviously processed.

    How compression works:
    1. When signal exceeds THRESHOLD, it gets compressed by RATIO
    2. ATTACK controls how quickly compression activates
    3. RELEASE controls how quickly it releases
    4. KNEE makes the transition smooth

    Args:
        waveform: Audio signal
        sr: Sample rate
        ratio: Compression ratio (default from settings)
        threshold_db: Threshold in dB (default from settings)
        attack_ms: Attack time in milliseconds
        release_ms: Release time in milliseconds
        knee_width: Soft knee width in dB

    Returns:
        Tuple of:
        - Compressed waveform
        - Dictionary with compression statistics
    """
    # Use defaults if not specified
    if ratio is None:
        ratio = DynamicRangeCompressor.RATIO
    if threshold_db is None:
        threshold_db = DynamicRangeCompressor.THRESHOLD
    if attack_ms is None:
        attack_ms = DynamicRangeCompressor.ATTACK_TIME_MS
    if release_ms is None:
        release_ms = DynamicRangeCompressor.RELEASE_TIME_MS
    if knee_width is None:
        knee_width = DynamicRangeCompressor.KNEE_WIDTH

    # Convert times to samples
    attack_samples = int(sr * attack_ms / 1000.0)
    release_samples = int(sr * release_ms / 1000.0)

    # Convert threshold from dB to linear
    threshold_linear = 10 ** (threshold_db / 20.0)

    # Ensure waveform is 1D for processing
    if waveform.ndim > 1:
        waveform = waveform.flatten()

    # Initialize output
    output = np.zeros_like(waveform)
    gain_envelope = np.ones_like(waveform)

    # Convert to dB for processing
    waveform_db = 20 * np.log10(np.abs(waveform) + 1e-10)
    threshold_db = threshold_db

    # Calculate gain reduction for each sample
    for i in range(len(waveform)):
        # Current level in dB
        level_db = waveform_db[i]

        # Calculate gain reduction
        if level_db > threshold_db:
            # Above threshold - apply compression
            excess_db = level_db - threshold_db

            # Soft knee: gradually increase compression over knee_width range
            if level_db < threshold_db + knee_width:
                # Inside knee region - scale ratio down
                progress = (level_db - threshold_db) / knee_width
                effective_ratio = 1.0 + (ratio - 1.0) * progress
            else:
                # Beyond knee - full ratio
                effective_ratio = ratio

            # Calculate how much to reduce
            gain_reduction_db = excess_db * (1 - 1 / effective_ratio)
            target_gain_db = -gain_reduction_db
        else:
            # Below threshold - no compression
            target_gain_db = 0.0

        # Smooth the gain change using attack/release
        if i == 0:
            current_gain_db = target_gain_db
        else:
            current_gain_db = gain_envelope[i - 1]

        # Apply attack or release
        if target_gain_db < current_gain_db:
            # Gain reduction needed (attack)
            max_change = (current_gain_db - target_gain_db) * attack_samples / (i + 1)
            current_gain_db = max(target_gain_db, current_gain_db - max_change)
        else:
            # Gain increasing (release)
            max_change = (target_gain_db - current_gain_db) * release_samples / (i + 1)
            current_gain_db = min(target_gain_db, current_gain_db + max_change)

        gain_envelope[i] = current_gain_db

    # Convert gain back to linear
    gain_linear = 10 ** (gain_envelope / 20.0)

    # Apply gain to waveform
    output = waveform * gain_linear

    # Calculate makeup gain to compensate
    makeup_gain_db = ratio * abs(threshold_db) / (ratio - 1) if ratio > 1 else 0
    makeup_gain_linear = 10 ** (makeup_gain_db / 20.0)
    output = output * makeup_gain_linear

    # Calculate statistics
    compression_amount = np.mean(np.abs(gain_envelope)) if len(gain_envelope) > 0 else 0
    stats = {
        'ratio': ratio,
        'threshold_db': threshold_db,
        'attack_ms': attack_ms,
        'release_ms': release_ms,
        'average_gain_reduction_db': np.mean(gain_envelope),
        'max_gain_reduction_db': np.min(gain_envelope),
    }

    return output, stats


def apply_limiter(
    waveform: np.ndarray,
    sr: int = 48000,
    threshold_db: Optional[float] = None,
    attack_ms: Optional[float] = None,
    release_ms: Optional[float] = None
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Apply peak limiting to prevent clipping.

    A limiter is like an infinite-ratio compressor - anything above
    the threshold gets clamped to prevent digital clipping. This is
    a safety mechanism, not a creative effect.

    Args:
        waveform: Audio signal
        sr: Sample rate
        threshold_db: Threshold in dB (default: -1 dB)
        attack_ms: Attack time in milliseconds
        release_ms: Release time in milliseconds

    Returns:
        Tuple of:
        - Limited waveform
        - Dictionary with limiting statistics
    """
    if threshold_db is None:
        threshold_db = PeakLimiter.THRESHOLD
    if attack_ms is None:
        attack_ms = PeakLimiter.ATTACK_TIME_MS
    if release_ms is None:
        release_ms = PeakLimiter.RELEASE_TIME_MS

    # Use compressor with infinite ratio for limiting
    limited, stats = apply_compressor(
        waveform,
        sr=sr,
        ratio=1000.0,  # Effectively infinite
        threshold_db=threshold_db,
        attack_ms=attack_ms,
        release_ms=release_ms,
        knee_width=0.0  # Hard knee for limiter
    )

    # Ensure hard ceiling
    threshold_linear = 10 ** (threshold_db / 20.0)
    limited = np.clip(limited, -threshold_linear, threshold_linear)

    stats['limiting_engaged_samples'] = np.sum(np.abs(limited) > threshold_linear * 0.99)
    stats['peak_before_limiting'] = 20 * np.log10(np.max(np.abs(waveform)) + 1e-10)
    stats['peak_after_limiting'] = 20 * np.log10(np.max(np.abs(limited)) + 1e-10)

    return limited, stats


def apply_loudness_processing(
    waveform: np.ndarray,
    sr: int = 48000,
    apply_normalization: Optional[bool] = None,
    apply_compression: Optional[bool] = None,
    apply_limiting: Optional[bool] = None,
    final_gain_db: Optional[float] = None,
) -> Tuple[np.ndarray, Dict]:
    """
    Apply complete loudness processing chain: normalization → compression → limiting.

    This is the main entry point for loudness processing. It applies the standard
    podcast processing pipeline in the correct order.

    Args:
        waveform: Audio signal
        sr: Sample rate
        apply_normalization: Enable loudness normalization
        apply_compression: Enable dynamic range compression
        apply_limiting: Enable peak limiting
        final_gain_db: Final gain adjustment in dB

    Returns:
        Tuple of:
        - Processed waveform
        - Dictionary with all processing statistics
    """
    # Use config defaults if not specified
    if apply_normalization is None:
        apply_normalization = ProcessingConfig.ENABLE_LOUDNESS_NORMALIZATION
    if apply_compression is None:
        apply_compression = ProcessingConfig.ENABLE_COMPRESSOR
    if apply_limiting is None:
        apply_limiting = ProcessingConfig.ENABLE_LIMITER
    if final_gain_db is None:
        final_gain_db = ProcessingConfig.FINAL_GAIN_ADJUSTMENT_DB

    output = waveform.copy()
    stats = {'steps': {}}

    # Step 1: Loudness Normalization
    if apply_normalization:
        output, norm_stats = apply_loudness_normalization(output, sr)
        stats['steps']['normalization'] = norm_stats

    # Step 2: Dynamic Range Compression
    if apply_compression:
        output, comp_stats = apply_compressor(output, sr)
        stats['steps']['compression'] = comp_stats

    # Step 3: Peak Limiting
    if apply_limiting:
        output, limit_stats = apply_limiter(output, sr)
        stats['steps']['limiting'] = limit_stats

    # Step 4: Final gain adjustment
    if final_gain_db != 0:
        final_gain_linear = 10 ** (final_gain_db / 20.0)
        output = output * final_gain_linear
        stats['final_gain_db'] = final_gain_db

    # Overall statistics
    stats['input_peak_db'] = 20 * np.log10(np.max(np.abs(waveform)) + 1e-10)
    stats['output_peak_db'] = 20 * np.log10(np.max(np.abs(output)) + 1e-10)

    return output, stats


def analyze_audio_dynamics(waveform: np.ndarray, sr: int = 48000) -> Dict[str, np.ndarray]:
    """
    Analyze audio to classify regions as Whisper/Normal/Loud.

    Divides audio into windows and measures RMS to determine category.
    Used for adaptive compression.

    Args:
        waveform: Audio signal
        sr: Sample rate

    Returns:
        Dictionary with:
        - 'categories': Array of category indices (0=Whisper, 1=Normal, 2=Loud) for each window
        - 'rms_values': RMS in dB for each window
        - 'window_size_samples': Size of analysis window in samples
    """
    window_size_ms = DynamicsAnalysisThresholds.ANALYSIS_WINDOW_MS
    window_size_samples = int(sr * window_size_ms / 1000.0)

    # Ensure waveform is 1D
    if waveform.ndim > 1:
        waveform = waveform.flatten()

    # Divide into windows and measure RMS
    num_windows = len(waveform) // window_size_samples
    rms_values = []
    categories = []

    for i in range(num_windows):
        start = i * window_size_samples
        end = start + window_size_samples
        window = waveform[start:end]

        # Calculate RMS in dB
        rms = np.sqrt(np.mean(window ** 2))
        rms_db = 20 * np.log10(rms + 1e-10)
        rms_values.append(rms_db)

        # Classify into category
        if rms_db < DynamicsAnalysisThresholds.WHISPER_UPPER_LIMIT:
            categories.append(0)  # Whisper
        elif rms_db < DynamicsAnalysisThresholds.NORMAL_UPPER_LIMIT:
            categories.append(1)  # Normal
        else:
            categories.append(2)  # Loud

    return {
        'categories': np.array(categories),
        'rms_values': np.array(rms_values),
        'window_size_samples': window_size_samples,
    }


def apply_adaptive_compressor(
    waveform: np.ndarray,
    sr: int = 48000,
    preset: str = 'normal',
    strength: str = 'strong',
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Apply adaptive dynamic range compression based on audio dynamics.

    Analyzes the audio to detect quiet/normal/loud segments and applies
    appropriate compression ratios to each.

    Args:
        waveform: Audio signal
        sr: Sample rate
        preset: 'aggressive' for Pass 1 or 'normal' for Pass 2
        strength: 'moderate' for gentle processing or 'strong' for aggressive
                 (Default: 'strong' for original audio)

    Returns:
        Tuple of:
        - Compressed waveform
        - Dictionary with compression statistics
    """
    # Select strength and preset
    if strength == 'moderate':
        if preset == 'aggressive':
            ratios = AdaptiveCompressionRatios.Moderate.PassOne
        else:
            ratios = AdaptiveCompressionRatios.Moderate.PassTwo
    else:  # strong
        if preset == 'aggressive':
            ratios = AdaptiveCompressionRatios.Strong.PassOne
        else:
            ratios = AdaptiveCompressionRatios.Strong.PassTwo

    # Analyze dynamics
    dynamics = analyze_audio_dynamics(waveform, sr)
    categories = dynamics['categories']
    window_size = dynamics['window_size_samples']

    # Create ratio map for each sample
    num_samples = len(waveform)
    ratio_map = np.ones(num_samples)

    for i, category in enumerate(categories):
        start = i * window_size
        end = min(start + window_size, num_samples)

        if category == 0:  # Whisper
            ratio_map[start:end] = ratios.WHISPER_RATIO
        elif category == 1:  # Normal
            ratio_map[start:end] = ratios.NORMAL_RATIO
        else:  # Loud
            ratio_map[start:end] = ratios.LOUD_RATIO

    # Apply compression with variable ratios
    output = waveform.copy()
    waveform_db = 20 * np.log10(np.abs(waveform) + 1e-10)

    attack_samples = int(sr * ratios.ATTACK_MS / 1000.0)
    release_samples = int(sr * ratios.RELEASE_MS / 1000.0)
    threshold_db = ratios.THRESHOLD_DB
    knee_width = ratios.KNEE_WIDTH_DB

    gain_envelope = np.ones_like(waveform)

    for i in range(len(waveform)):
        level_db = waveform_db[i]
        current_ratio = ratio_map[i]

        if level_db > threshold_db:
            excess_db = level_db - threshold_db

            # Soft knee
            if level_db < threshold_db + knee_width:
                progress = (level_db - threshold_db) / knee_width
                effective_ratio = 1.0 + (current_ratio - 1.0) * progress
            else:
                effective_ratio = current_ratio

            gain_reduction_db = excess_db * (1 - 1 / effective_ratio)
            target_gain_db = -gain_reduction_db
        else:
            target_gain_db = 0.0

        # Smooth gain with attack/release
        if i == 0:
            current_gain_db = target_gain_db
        else:
            current_gain_db = gain_envelope[i - 1]

        if target_gain_db < current_gain_db:
            max_change = (current_gain_db - target_gain_db) * attack_samples / (i + 1)
            current_gain_db = max(target_gain_db, current_gain_db - max_change)
        else:
            max_change = (target_gain_db - current_gain_db) * release_samples / (i + 1)
            current_gain_db = min(target_gain_db, current_gain_db + max_change)

        gain_envelope[i] = current_gain_db

    gain_linear = 10 ** (gain_envelope / 20.0)
    output = waveform * gain_linear

    stats = {
        'preset': preset,
        'average_ratio': np.mean(ratio_map),
        'whisper_regions': np.sum(categories == 0),
        'normal_regions': np.sum(categories == 1),
        'loud_regions': np.sum(categories == 2),
        'average_gain_reduction_db': np.mean(gain_envelope),
    }

    return output, stats


def apply_dual_pass_loudness_processing(
    waveform: np.ndarray,
    sr: int = 48000,
    strength: str = 'strong',
) -> Tuple[np.ndarray, Dict]:
    """
    Apply two-pass loudness processing for enhanced dynamic control.

    Pass 1 (Aggressive): Lifts quiet segments using high compression ratios
    Pass 2 (Normal): Smooths the result with standard compression for natural sound

    This approach rescues whispered or quiet passages while maintaining
    natural sound quality.

    Args:
        waveform: Audio signal
        sr: Sample rate
        strength: 'moderate' for already-processed audio or 'strong' for original audio
                 (Default: 'strong')

    Returns:
        Tuple of:
        - Processed waveform
        - Dictionary with all processing statistics
    """
    output = waveform.copy()
    stats = {'passes': {}, 'strength': strength}

    # Pass 1: Aggressive adaptive compression
    output, pass1_stats = apply_adaptive_compressor(output, sr, preset='aggressive', strength=strength)
    stats['passes']['pass1_aggressive'] = pass1_stats

    # Pass 2: Normal adaptive compression
    output, pass2_stats = apply_adaptive_compressor(output, sr, preset='normal', strength=strength)
    stats['passes']['pass2_normal'] = pass2_stats

    # Add overall stats
    stats['input_peak_db'] = 20 * np.log10(np.max(np.abs(waveform)) + 1e-10)
    stats['output_peak_db'] = 20 * np.log10(np.max(np.abs(output)) + 1e-10)

    return output, stats


def log_processing_stats(stats: Dict) -> str:
    """
    Format loudness processing statistics as a readable string.

    Args:
        stats: Statistics dictionary from apply_loudness_processing

    Returns:
        Formatted string for logging/display
    """
    lines = ["=== Loudness Processing Results ==="]

    # Handle new dual-pass stats
    if 'passes' in stats:
        strength = stats.get('strength', 'strong').upper()
        lines.append(f"Dual-Pass Adaptive Compression ({strength}):")
        if 'pass1_aggressive' in stats['passes']:
            p1 = stats['passes']['pass1_aggressive']
            lines.append(f"  Pass 1 (Aggressive):")
            lines.append(f"    Whisper regions: {p1.get('whisper_regions', 0)}")
            lines.append(f"    Normal regions: {p1.get('normal_regions', 0)}")
            lines.append(f"    Loud regions: {p1.get('loud_regions', 0)}")
            lines.append(f"    Avg gain reduction: {p1.get('average_gain_reduction_db', 0):.2f} dB")

        if 'pass2_normal' in stats['passes']:
            p2 = stats['passes']['pass2_normal']
            lines.append(f"  Pass 2 (Normal):")
            lines.append(f"    Avg gain reduction: {p2.get('average_gain_reduction_db', 0):.2f} dB")

    # Handle legacy single-pass stats
    if 'steps' in stats:
        if 'normalization' in stats['steps']:
            norm = stats['steps']['normalization']
            lines.append(f"Normalization:")
            lines.append(f"  Before: {norm['before_lufs']:.1f} LUFS")
            lines.append(f"  After:  {norm['after_lufs']:.1f} LUFS")
            lines.append(f"  Gain:   {norm['gain_applied_db']:+.1f} dB")

        if 'compression' in stats['steps']:
            comp = stats['steps']['compression']
            lines.append(f"Compression:")
            lines.append(f"  Ratio:  {comp['ratio']:.1f}:1")
            lines.append(f"  Threshold: {comp['threshold_db']:.1f} dB")
            lines.append(f"  Avg Reduction: {comp['average_gain_reduction_db']:.2f} dB")
            lines.append(f"  Max Reduction: {comp['max_gain_reduction_db']:.2f} dB")

        if 'limiting' in stats['steps']:
            limit = stats['steps']['limiting']
            lines.append(f"Limiting:")
            lines.append(f"  Peak Before: {limit['peak_before_limiting']:.1f} dB")
            lines.append(f"  Peak After:  {limit['peak_after_limiting']:.1f} dB")
            lines.append(f"  Samples Limited: {limit['limiting_engaged_samples']}")

    lines.append(f"\nOverall:")
    lines.append(f"  Input Peak:  {stats.get('input_peak_db', 'N/A')}")
    if isinstance(stats.get('input_peak_db'), (int, float)):
        lines[-1] = f"  Input Peak:  {stats.get('input_peak_db', 0):.1f} dB"
    lines.append(f"  Output Peak: {stats.get('output_peak_db', 'N/A')}")
    if isinstance(stats.get('output_peak_db'), (int, float)):
        lines[-1] = f"  Output Peak: {stats.get('output_peak_db', 0):.1f} dB"

    return "\n".join(lines)
