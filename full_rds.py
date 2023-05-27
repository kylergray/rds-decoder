from scipy import signal
import matplotlib.pyplot as plt
import numpy as np

from rtlsdr import RtlSdr


F_station = int(94.9e6)  # KUOW

F_offset = 250000         # Offset to capture at, to avoid the DC spike
Fc = F_station - F_offset  # Capture center frequency
Fs = int(57e3*20)         # Sample rate
gain = 10                 # Gain
N = int(1024000*8)        # Number of samples to capture, this is ~8 seconds
# The goofy size is to help out RTL-SDR

sdr = RtlSdr()

# configure device
sdr.sample_rate = Fs      # Hz
sdr.center_freq = Fc      # Hz
sdr.freq_correction = -52  # PPM
sdr.gain = 0

samples = sdr.read_samples(N)

sdr.close()
del (sdr)


def band_pass_filter(sample_rate, center_freq, f_bw, samples):
    """
    Based on GNU radio
    """
    # Create a LPF for our target bandwidth
    taps = 100
    # filter shaped to remove 0-
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

    return sample_rate / dec_step, y


radio_samples_ps, radio_samples = band_pass_filter(Fs, F_offset, 200000, samples)



def decode_quad(samples, gain=42):
    xp = samples[1:] * samples[:-1].conjugate()
    return gain * np.arctan2(xp.imag, xp.real)


decoded_signal = decode_quad(radio_samples, 42.0)



n_taps = 400
# The center frequency that RDS is on
center_freq = 57e3

fwT0 = 2.0*np.pi*center_freq/radio_samples_ps  # The phase velocity of our center

#################
# Remember in the extract_channel(), we talked about the naive way
# being a simple downshift followed by filtering?  We could try that
# here, and also do it with the other method, then compare results.


# Both methods can use this base LPF
base_lpf = signal.remez(n_taps,
                              [0, 1250, 2500, radio_samples_ps/2.0],
                              [1, 0],
                              Hz=radio_samples_ps)



# Now, let's try with the shifted-LPF technique, and see how it does:

##################
# Generate our shifted LPF and apply it
#
# Note that we're multiplying by a simple cos here, not a complex
# exponential.  We only need the real cosine component when our
# underlying data isn't complex.
#
lpf_shifted = base_lpf * np.cos(fwT0 * np.arange(0, n_taps))

v_lpf_shift = signal.lfilter(lpf_shifted, 1.0, decoded_signal)
u_lpf_shift = v_lpf_shift * np.cos(fwT0 * np.arange(0, len(v_lpf_shift)))
u_lpf_shift = signal.lfilter(base_lpf, 1.0, u_lpf_shift)

# LPF shift, no output filter:
#    222, 96,  "THE BAY ____'S ORIGINAL KFOG\r   ________________________________"
# LPF shift, with output filter:
#    229, 104, "THE BAY ____'S ORIGINAL KFOG\r   ________________________________"

# It looks like the best performer is the LPF shifted up, followed by LPF of
# the output signal.

# Let's pick one to work with from here on out
u = u_lpf_shift

##################
# Now, to decimate the signal down.

# the bitrate of RDS
bits_ps = 1187.5
dec_u = int(radio_samples_ps / (4*bits_ps))
# the sample rate of decimated
rds_dec_ps = radio_samples_ps/dec_u

print(u.shape)

u = u[range(0, len(u), dec_u)]

print(u.shape)

dec_step = int(rds_dec_ps/bits_ps)
print(dec_step)

# calculate the phase and determine if it is in the -90deg range or +90deg range
# matches the BPSK protocol
bits = np.abs(np.arctan2(u.imag, u.real)) < np.pi / 2
bits = bits[range(0, len(bits), dec_step)]

# There is a differential coding
# we need to undo this so we xor the bits one off
# i.e. [1, 0, 0, 1, 1]
# [1 xor 0: 1, 0 xor 0: 0, 0 xor 1: 1, 1 xor 1: 0]
bitdec = bits[1:] != bits[:-1]


plt.figure()
plt.plot(bitdec[:200])
plt.title("Bits for RDS")
plt.ylim(-0.2, 1.2)
plt.show()

my_hits = []


def rds_syndrome(message, m_offset, mlen):
    POLY = 0x5B9 # 10110111001, g(x)=x^10+x^8+x^7+x^5+x^4+x^3+1
    PLEN = 10
    SYNDROME=[383, 14, 303, 663, 748]
    OFFSET_NAME=['A', 'B', 'C', 'D', 'C\'']
    reg = 0

    if((mlen!=16)and(mlen!=26)):
        raise ValueError
    # start calculation
    for i in range(mlen):
        reg=(reg<<1)|(message[m_offset+i])
        if(reg&(1<<PLEN)):
            reg=reg^POLY
    for i in range(PLEN,0,-1):
        reg=reg<<1
        if(reg&(1<<PLEN)):
            reg=reg^POLY
    checkword=reg&((1<<PLEN)-1)
    # end calculation
    for i in range(0,5):
            if(checkword==SYNDROME[i]):
                #print "checkword matches syndrome for offset", OFFSET_NAME[i]
                return OFFSET_NAME[i]

    return None

for i in range(len(bitdec)-26):
    h = rds_syndrome(bitdec, i, 26)
    if h:
        my_hits.append( (i, h) )

print((len(my_hits), my_hits[0:10]))

def _collect_bits(bitstream, offset, n):
    """Helper method to collect a string of n bits, MSB, into an int"""
    retval = 0
    for i in range(n):
        retval = retval*2 + bitstream[offset+i]
    return retval

def decode_A(bitstream, offset):
    """Trivial RDS block A decoder"""
    return _collect_bits(bitstream, offset, 16)

def decode_B(bitstream, offset):
    """Trivial RDS block B decoder"""
    retval = {}

    retval["group_type"] = _collect_bits(bitstream, offset, 4)
    retval["version_AB"] = "B" if bitstream[offset+4] else "A"
    retval["traffic_prog_code"] = bitstream[offset+5]
    retval["prog_type"] = _collect_bits(bitstream, offset+6,5)

    if retval["group_type"] == 2:
        retval["text_segment"] = _collect_bits(bitstream, offset+12, 4)
    elif retval["group_type"] == 0:
        retval["pi_segment"] = _collect_bits(bitstream, offset+14, 2)

    return retval

def decode_C(bitstream, offset):
    """Trivial RDS block C decoder"""
    c0 = _collect_bits(bitstream, offset, 8)
    c1 = _collect_bits(bitstream, offset+8, 8)

    return ( chr(c0), chr(c1))

def decode_Cp(bitstream, offset):
    """Stub RDS block C decoder"""
    return None

def decode_D(bitstream, offset):
    """Trivial RDS block D decoder"""
    return decode_C(bitstream, offset)

# A lookup table to make it easier to dispatch to subroutines in the code below
decoders = { "A": decode_A, "B": decode_B, "C": decode_C, "C'": decode_Cp, "D": decode_D }

def decode_one(bitstream, offset):
    s = rds_syndrome(bitstream, offset, 26)
    if None == s:
        return None

    return (s, decoders[s](bitstream, offset))

hit_parses = []
for i in range(len(my_hits)-3):
    if my_hits[i][1] == "A":
        bogus = False
        # for j,sp in enumerate("ABCD"):
        #     if 26*j != my_hits[i+j][0] - my_hits[i][0]:
        #         bogus = True
        #     if my_hits[i+j][1] != sp:
        #         bogus = True

        if not bogus:
            for j in range(4):
                hit_parses.append( (my_hits[i+j][0], decode_one(bitdec, my_hits[i+j][0])))


print(len(hit_parses), hit_parses[:20])

def accumulate_radiotext(parses):
    """A state machine that accumulates the radio text messages

    This takes in a whole list of packet-qualifying blocks (ie:
    a list of blocks, but which have been filtered down such that
    they always come in ABCD or ABC'D order, and each quad is
    adjacent in the bitstream).

    Returns a list of states of the radio text as it progresses
    through consuming the input packets.
    """
    cur_state = ["_"] * 64

    retval = [ "".join(cur_state) ]

    cursor = None
    for blkid, decode in parses:
        if blkid == "B":
            if decode['group_type'] == 2:
                cursor = decode['text_segment'] * 4
            else:
                cursor = None

        if None != cursor:
            if blkid == "C":
                cur_state[cursor] = decode[0]
                cur_state[cursor+1] = decode[1]
                retval.append("".join(cur_state))
            elif blkid == "D":
                cur_state[cursor+2] = decode[0]
                cur_state[cursor+3] = decode[1]
                retval.append("".join(cur_state))

            if blkid == "A" or blkid == "D":
                cursor = None

    return retval

print(accumulate_radiotext([ b for (a,b) in hit_parses]))


def accumulate_b0text(parses):
    cur_state = ["_"] * 8

    retval = [ "".join(cur_state) ]

    cursor = None
    for blkid, decode in parses:
        if blkid == "B":
            if decode['group_type'] == 0:
                cursor = decode['pi_segment'] * 2
            else:
                cursor = None

        if None != cursor:
            if blkid == "D":
                cur_state[cursor] = decode[0]
                cur_state[cursor+1] = decode[1]
                retval.append("".join(cur_state))
            if blkid == "A" or blkid == "D":
                cursor = None

    return retval
print(accumulate_b0text([ b for (a,b) in hit_parses]))

