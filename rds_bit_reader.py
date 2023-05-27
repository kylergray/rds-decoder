from scipy import signal
from typing import List
import numpy as np


class RDSBitReader:

    # RDS Spectrum is 57kHz with tolerance of 6 (expanding for extra room)
    _RDS_CENTER_FREQ = 57e3
    _RDS_FREQ_TOLERANCE = 12.0

    # Samples for the in buffer
    _IN_BUF_LEN = 4096

    # Number of bits for out buffer
    _OUT_BUF_LEN = 128

    def __init__(self, sample_rate: int) -> None:
        self._sample_rate = sample_rate
        # downsample
        self._decimate = int(self._sample_rate / 7125)

        self._data_bit = 0

        self._prev_acc = 0
        self._counter = 0
        self._reading_frame = 0
        self._tot_errs = [0, 0]

        self._bits = []

        pass

    def run(self, samples: List[int]) -> None:
        fsc = self._RDS_CENTER_FREQ

        # subcarrier phase
        subcarr_phi = 0
        subcarr_bb = [0, 0]

        # clock tracking
        clock_offset = 0
        clock_phi = 0

        lo_clock = 0
        prev_clock = 0
        prev_bb = 0

        # error of subcarrier phase
        d_phi_sc = 0
        d_cphi = 0
        acc = 0
        pll_beta = 50

        # Design lowpass Butterworth filter coefficients for lp2400Coeffs
        lp2400Coeffs = signal.butter(
            5, 2000.0 / self._sample_rate, btype='low', analog=False, output='sos')

        # Design lowpass Butterworth filter coefficients for lpPllCoeffs
        lpPllCoeffs = signal.butter(
            1, 2200.0 / self._sample_rate, btype='low', analog=False, output='sos')


        for i, sample in enumerate(samples):
            subcarr_phi += 2 * np.pi * fsc / self._sample_rate
            subcarr_bb[0] = signal.sosfilt(lp2400Coeffs, [sample.real / 32768.0 * np.cos(subcarr_phi)])[0]
            subcarr_bb[1] = signal.sosfilt(lp2400Coeffs, [sample.imag / 32768.0 * np.sin(subcarr_phi)])[0]
            # print(subcarr_bb)

            d_phi_sc = signal.sosfilt(lpPllCoeffs, [subcarr_bb[1] * subcarr_bb[0]])[0]
            # print(d_phi_sc)
            subcarr_phi -= pll_beta * d_phi_sc
            fsc -= 0.5 * pll_beta * d_phi_sc

            # print(self._decimate)
            if i % self._decimate == 0:
                if ((fsc > self._RDS_CENTER_FREQ + self._RDS_FREQ_TOLERANCE) or
                        (fsc < self._RDS_CENTER_FREQ - self._RDS_FREQ_TOLERANCE)):
                    fsc = self._RDS_CENTER_FREQ

                # 1187.5 Hz clock
                clock_phi = subcarr_phi / 48.0 + clock_offset
                lo_clock = 1 if clock_phi % (2 * np.pi) < np.pi else -1

                if self._sign(prev_bb) != self._sign(subcarr_bb[0]):
                    d_cphi = clock_phi % np.pi
                    if (d_cphi >= (np.pi / 2)):
                        d_cphi -= np.pi
                    clock_offset -= 0.005 * d_cphi

                acc += subcarr_bb[0] * lo_clock

                if (self._sign(lo_clock) != self._sign(prev_clock)):
                    self._biphase(acc)
                    acc = 0

                prev_clock = lo_clock
                prev_bb = subcarr_bb[0]


    def _store_value(self, bit: int) -> None:
        # print((bit ^ self._data_bit) != 0)
        self._data_bit = bit
        self._bits.append(self._data_bit)

    def _biphase(self, acc: int) -> None:
        if self._sign(acc) != self._sign(self._prev_acc):
            self._tot_errs[self._counter % 2] += 1


        if self._counter % 2 == self._reading_frame:
            self._store_value(self._sign(acc + self._prev_acc))

        if self._counter == 0:
            if (self._tot_errs[1 - self._reading_frame] <
                    self._tot_errs[self._reading_frame]):
                self._reading_frame = 1 - self._reading_frame
            self._tot_errs = [0, 0]

        self._prev_acc = acc
        self._counter = (self._counter + 1) % 800

    def _sign(self, num: int) -> int:
        return 1 if num >= 0 else -1
    
    def bits(self) -> List:
        return np.copy(self._bits)
