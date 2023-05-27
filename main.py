from rtlsdr import RtlSdr
import numpy as np
from scipy.signal import resample_poly, firwin, bilinear, lfilter, welch, hilbert, resample, butter, filtfilt
import matplotlib.pyplot as plt
import time
import sounddevice as sd
from copy import copy

from tools import bandpassmask, lowpass_fir_filter
np.set_printoptions(precision=2)

# Close previous instances of the sdr object
try:
    sdr.close()
    print("Closed old SDR")
except NameError:
    print("No SDR instance found")

sdr = RtlSdr()  # Create a new sdr object (by keeping this in


sample_rate = 2*256*256*16  # =  ... about 2Msps...works

fc = 95.7e6  # Seattle
dt = 1.0/sample_rate  # time step size between samples
nyquist = sample_rate / 2.0

Tmax = 1        # 2.5 s

N = round(sample_rate*Tmax)  # N must be a multiple of 256

sdr.sample_rate = sample_rate
sdr.center_freq = fc
sdr.gain = 42.0  # This is max, according to sdr.valid_gains_db

faudiosps = 48000
faudionyquist = faudiosps/2.0

# Collect N samples...N must be multiple of 256
samples = sdr.read_samples(N)


filtered, N = lowpass_fir_filter(samples=samples)

# phase
theta = np.arctan2(filtered.imag, filtered.real)
abssignal = np.abs(filtered)
meanabssignal = np.mean(abssignal)
thetasquelched = copy(theta)
filteredsquelched = copy(filtered)
for i in range(N-1):
    if (abssignal[i] < (meanabssignal/3.0)):
        filteredsquelched[i] = 0.0
        thetasquelched[i] = 0.0


derivthetap0 = np.convolve([1, -1], thetasquelched, 'same')
derivthetapp = np.convolve([1, -1], (thetasquelched+np.pi) % (2*np.pi), 'same')


derivtheta = np.zeros(len(derivthetap0))
for i in range(len(derivthetap0)):
    if (abs(derivthetap0[i]) < abs(derivthetapp[i])):
        derivtheta[i] = derivthetap0[i]
    else:
        derivtheta[i] = derivthetapp[i]


# Clean spikes by averaging adjacent samples
spikethresh = 2
cdtheta = copy(derivtheta)
for i in range(1, len(derivtheta)-1):
    if (abs(derivtheta[i]) > spikethresh):
        cdtheta[i] = (derivtheta[i-1]+derivtheta[i+1])/2.0


freq_domain = np.abs(np.fft.fftshift(np.fft.fft(cdtheta)))
frequencies = np.linspace(-nyquist, nyquist, len(freq_domain))
rds_bandpassmask, (start_idx, end_idx) = bandpassmask(
    len(frequencies), nyquist, 57e3 - 2.4e3, 57e3 + 2.4e3)

rds_freq_domain = freq_domain * rds_bandpassmask

rds_time_domain = np.fft.ifft(np.fft.fftshift(rds_freq_domain))
time_stamps = np.linspace(0, 0.0022, int(sample_rate * 0.0022))
plt.figure()
three_t = len(time_stamps)
plt.plot(time_stamps, rds_time_domain[three_t * 4:three_t * 5])
plt.show()


threshold = np.percentile(rds_time_domain, 98)  # Adjust the threshold as needed
crossings = np.where(rds_time_domain > threshold)[0]


print(crossings.shape)
print(crossings)


bit_boundaries = np.diff(crossings) > np.median(np.diff(crossings))
print(bit_boundaries.shape)
print(bit_boundaries)

bits = []
for i in range(int(len(bit_boundaries) / 100) - 1):
    if bit_boundaries[i]:
        print(i)
        bits.append(int(rds_time_domain[crossings[i]] > 0))  # Adjust the polarity as needed

print(bits)

# Calculate bit boundaries
bit_boundaries = np.diff(crossings) > np.median(np.diff(crossings))


# Downsample by averaging blocks
dsf = round(sample_rate/faudiosps)
dscdtheta = np.mean(
    cdtheta[:len(cdtheta) - len(cdtheta) % dsf].reshape([-1, dsf]), 1)


myaudio = dscdtheta
sd.play(10*myaudio, faudiosps, blocking=True)
