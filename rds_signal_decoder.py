from scipy import signal
import matplotlib.pyplot as plt
import numpy as np


class RDSSignalDecoder:

    _RDS_CENTER_FREQ = 57e3
    _RDS_BPS = 1187.5

    def __init__(self, sample_rate: int) -> None:

        self._sample_rate = sample_rate
        self._samples = []
        self._bitstream = []

        pass

    def load_samples(self, samples) -> None:
        self._samples.append(samples)
        self._process_samples()

    def read_bits(self) -> np.ndarray:
        if len(self._bitstream) == 0:
            return None
        return self._bitstream.pop(0)

    def _process_samples(self) -> None:
        while len(self._samples) > 0:
            # process
            samples = self._samples.pop(0)

            plt.figure()
            plt.title("Raw Power Spectrum Density Centered at 95.7 MHz")
            plt.psd(samples, Fs=self._sample_rate)
            d_signal, dsig_samp_ps = self._demod(samples)
            plt.figure()
            plt.title('Power Spectrum After Demodulation and Bandpass')
            plt.psd(d_signal, Fs=dsig_samp_ps)
            plt.show()
            rds_filt_signal, rds_filt_samp_ps = self._filter_rds_segment(
                d_signal, dsig_samp_ps)
            plt.figure()
            plt.title('Power Spectrum After Demodulation and Bandpass')
            plt.plot(rds_filt_signal[:200])
            plt.show()
            self._bitstream.append(self._create_bits(
                rds_filt_signal, rds_filt_samp_ps))

    def _demod(self, samples: np.ndarray, gain=42.0) -> np.ndarray:
        filt_signal, filtsig_samp_ps = self._band_pass_filter(
            self._sample_rate, 250e3, 200000, samples)

        deriv = filt_signal[1:] * filt_signal[:-1].conjugate()
        return gain * np.arctan2(deriv.imag, deriv.real), filtsig_samp_ps

    def _band_pass_filter(self, sample_rate, center_freq, f_bw, samples):
        taps = 100
        base_lpf = signal.remez(taps, [
                                0,
                                f_bw,
                                f_bw + (sample_rate / 2 - f_bw) / 4,
                                sample_rate / 2], [1, 0], Hz=sample_rate)

        # Center our frequency
        fwT0 = 2.0 * np.pi * center_freq / sample_rate
        center_filter = base_lpf * np.exp(1.0j * fwT0 * np.arange(0, taps))
        filtered_samples = signal.lfilter(center_filter, 1.0, samples)

        # Mix the filtered data down down by the carrier frequency
        x_filtered_downmix = filtered_samples * \
            np.exp(-1.0j * fwT0 * np.arange(len(filtered_samples)))

        # decimate the data
        dec_step = int(sample_rate / f_bw)
        dec_is = np.arange(0, len(x_filtered_downmix), dec_step)
        y = x_filtered_downmix[dec_is]

        return y, sample_rate / dec_step

    def _filter_rds_segment(self, demoded_signal: np.ndarray, dsig_samp_ps: int) -> np.ndarray:
        taps = 400
        phase_step = 2.0 * np.pi * self._RDS_CENTER_FREQ / dsig_samp_ps

        base_lpf = signal.remez(taps,
                                [0, 1250, 2500, dsig_samp_ps / 2.0],
                                [1, 0],
                                Hz=dsig_samp_ps)

        lpf_shifted = base_lpf * np.cos(phase_step * np.arange(0, taps))

        v_lpf_shift = signal.lfilter(lpf_shifted, 1.0, demoded_signal)
        rds_filt_signal = v_lpf_shift * \
            np.cos(phase_step * np.arange(0, len(v_lpf_shift)))
        rds_filt_signal = signal.lfilter(base_lpf, 1.0, rds_filt_signal)

        dec_step = int(dsig_samp_ps / (4 * self._RDS_BPS))
        rds_filt_samp_ps = dsig_samp_ps / dec_step
        rds_filt_signal = rds_filt_signal[range(
            0, len(rds_filt_signal), dec_step)]

        return rds_filt_signal, rds_filt_samp_ps

    def _create_bits(self, rds_signal: np.ndarray, rds_samp_ps: np.ndarray) -> np.ndarray:
        # calculate the phase and determine if it is in the -90deg range or +90deg range
        # matches the BPSK protocol
        plt.figure()
        plt.title('Raw Bits (first 200 samples)')
        plt.plot(np.abs(np.arctan2(rds_signal.imag, rds_signal.real))[:200])
        plt.show()
        bits = np.abs(np.arctan2(rds_signal.imag, rds_signal.real)) < np.pi / 2
        dec_step = int(rds_samp_ps / self._RDS_BPS)
        bits = bits[range(0, len(bits), dec_step)]

        # There is a differential coding
        # we need to undo this so we xor the bits one off
        # i.e. [1, 0, 0, 1, 1]
        # [1 xor 0: 1, 0 xor 0: 0, 0 xor 1: 1, 1 xor 1: 0]
        bits = [int(bit) for bit in bits[1:] != bits[:-1]]
        
        plt.figure()
        plt.title('Bits After Undoing Differential Coding and Decimation')
        plt.plot(bits[:200])
        plt.show()
        return bits
