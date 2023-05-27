import numpy as np


def lowpass_fir_filter(samples: np.ndarray, taps=10) -> tuple[np.ndarray, int]:
    """Apply a low pass FIR filter to a given signal with taps number of taps.

    Low Pass Filter Shape

            /----\
           /      \
           |      |
        /\ |      | /\
     /\/  \/      \/  \/\

    Args:
        samples (np.ndarray): the array to filter
        taps (int): the number of taps to use

    Returns:
        np.ndarray: the filtered signal
        int: the length of the filtered signal
    """
    filtered = np.convolve(samples, np.ones(taps) / taps, 'valid')
    return (filtered, len(filtered))


def bandpassmask(N: int, nyquist: np.ndarray, f_low: int, f_high: int) -> tuple[np.ndarray, tuple[int, int]]:
    """Generate a bandpass mask that is N samples long for a frequency domain
    signal with the set nyquist limit. The mask will retain frequencies from
    f_low to f_high.

    Get back the mask, as well as the first and last indexes of the high section.

    Args:
        N (int): number of samples
        nyquist (np.ndarray): nyquist limit
        f_low (int): lowest frequency to retain
        f_high (int): highest frequency to retain

    Returns:
        tuple[np.ndarray, tuple[int, int]]: (mask, (start index, end index))
    """
    low_ratio = f_low / nyquist
    high_ratio = f_high / nyquist

    split = int(N / 2)
    zeros_before = np.zeros(split + int(low_ratio * split))
    zeros_after = np.zeros(split - int(high_ratio * split))
    ones = np.ones(N - len(zeros_after) - len(zeros_before))

    mask = np.concatenate((zeros_before, ones, zeros_after))
    start_idx = len(zeros_before)
    end_idx = start_idx + len(ones) - 1
    return (mask, (start_idx, end_idx))
