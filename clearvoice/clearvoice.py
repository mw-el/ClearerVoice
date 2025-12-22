from network_wrapper import network_wrapper
from utils.audio_processing import apply_loudness_processing, apply_dual_pass_loudness_processing, log_processing_stats
import os
import warnings
import numpy as np
warnings.filterwarnings("ignore")

class ClearVoice:
    """ The main class inferface to the end users for performing speech processing
        this class provides the desired model to perform the given task
    """
    def __init__(self, task, model_names, apply_loudness_processing_flag=False):
        """ Load the desired models for the specified task. Perform all the given models and return all results.

        Parameters:
        ----------
        task: str
            the task matching any of the provided tasks:
            'speech_enhancement'
            'speech_separation'
            'target_speaker_extraction'
        model_names: str or list of str
            the model names matching any of the provided models:
            'FRCRN_SE_16K'
            'MossFormer2_SE_48K'
            'MossFormerGAN_SE_16K'
            'MossFormer2_SS_16K'
            'AV_MossFormer2_TSE_16K'
        apply_loudness_processing_flag: bool
            If True, applies loudness normalization and dynamic range compression
            after speech enhancement for more consistent podcast audio.
            If False, only applies speech enhancement.

        Returns:
        --------
        A ClearVoice object, that can be run to get the desired results
        """
        self.network_wrapper = network_wrapper()
        self.models = []
        self.apply_loudness_processing = apply_loudness_processing_flag
        for model_name in model_names:
            model = self.network_wrapper(task, model_name)
            self.models += [model]

    def __call__(self, input_path, online_write=False, output_path=None, sr=None):
        results = {}
        for model in self.models:
            result = model.process(input_path, online_write, output_path)

            # Apply loudness processing if enabled and not online_write
            if self.apply_loudness_processing and not online_write:
                if sr is None:
                    # Try to get sample rate from model configuration
                    sr = getattr(model, 'sr', 48000)

                result = self._apply_loudness_to_results(result, sr)

            if not online_write:
                results[model.name] = result

        if not online_write:
            if len(results) == 1:
                return results[model.name]
            else:
                return results

    def _apply_loudness_to_results(self, results, sr):
        """
        Apply dual-pass loudness processing to model results.

        Uses adaptive compression with two passes:
        - Pass 1: Aggressive ratios (10:1, 5:1, 2:1) to lift quiet segments
        - Pass 2: Normal ratios (4:1, 2:1, 1:1) to smooth and naturalize

        Handles both single waveforms and lists of waveforms (e.g., from speech separation).

        Args:
            results: Either a single waveform or a list of waveforms
            sr: Sample rate in Hz

        Returns:
            Processed results with same structure as input
        """
        if isinstance(results, (list, tuple)):
            # Multiple outputs (e.g., speech separation with 2 speakers)
            processed_results = []
            for waveform in results:
                processed, stats = apply_dual_pass_loudness_processing(waveform, sr=sr)
                processed_results.append(processed)
                print(log_processing_stats(stats))
            return processed_results
        else:
            # Single waveform output
            processed, stats = apply_dual_pass_loudness_processing(results, sr=sr)
            print(log_processing_stats(stats))
            return processed

    def write(self, results, output_path):
        add_subdir = False
        use_key = False
        if len(self.models) > 1: add_subdir = True #multi_model is True
        for model in self.models:
            if isinstance(results, dict):
                if model.name in results:
                   if len(results[model.name]) > 1: use_key = True

                else:
                   if len(results) > 1: use_key = True #multi_input is True
            break

        for model in self.models:
            model.write(output_path, add_subdir, use_key)
