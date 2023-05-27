import numpy as np
import matplotlib.pyplot as plt
from rtlsdr import RtlSdr

# RDS parameters
RDS_FREQUENCY = 59000  # RDS subcarrier frequency in Hz
SAMPLE_RATE = 240000  # Sample rate in Hz
BIT_RATE = 1187.5  # RDS bit rate in bits per second

# Configure RTL-SDR
sdr = RtlSdr()
sdr.sample_rate = SAMPLE_RATE
sdr.center_freq = 94.9e6

# Calculate the number of samples per bit
samples_per_bit = int(SAMPLE_RATE / BIT_RATE)

try:
    # Read samples
    samples = sdr.read_samples(samples_per_bit * 200)  # Adjust the number of samples as needed

    # Perform FM demodulation
    fm_demod = np.abs(samples)

    # Low-pass filter to extract the baseband signal
    cutoff_freq = BIT_RATE * 2  # Adjust the cutoff frequency as needed
    filtered_signal = np.convolve(fm_demod, np.ones(int(SAMPLE_RATE / cutoff_freq)) / (SAMPLE_RATE / cutoff_freq), mode='same')

    # Calculate phase differences
    phase_diff = np.angle(filtered_signal[1:] * np.conj(filtered_signal[:-1]))

    # Find phase reversals
    threshold = np.percentile(phase_diff, 90)  # Adjust the threshold as needed
    crossings = np.where(phase_diff > threshold)[0]

    # Calculate bit boundaries
    bit_boundaries = np.diff(crossings) > np.median(np.diff(crossings))

    # Extract bits
    bits = []
    for i in range(len(bit_boundaries) - 1):
        if bit_boundaries[i]:
            bits.append(int(phase_diff[crossings[i]] > 0))  # Adjust the polarity as needed

    # Group bits into 16-bit blocks
    groups = [bits[i:i+16] for i in range(0, len(bits), 16)]

    # Print decoded groups
    for group in groups:
        print('Decoded group:', group)

    # Plot phase differences for visualization
    plt.plot(phase_diff)
    plt.xlabel('Sample Index')
    plt.ylabel('Phase Difference')
    plt.title('Phase Differences')
    plt.show()

finally:
    # Close the RTL-SDR device
    sdr.close()
