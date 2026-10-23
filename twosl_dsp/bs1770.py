"""ITU-R BS.1770-5 loudness and true peak (references/itu-r-bs1770.md): the K-weighting pre-filter (its two 48 kHz
stages, Tables 1 and 2, redone at another rate for the same response), gated integrated loudness (400 ms blocks
overlapping 75 %, the absolute gate at -70 LKFS, the relative gate 10 LU under the absolute-gated loudness; equations
2-7), EBU Mode's momentary loudness (EBU Tech 3341: the same loudness over a sliding 400 ms window, not gated) and its
maximum, and Annex 2's true peak (4x over-sampling with its 48-tap interpolating FIR). Standard library only: a
device's tests measure its presets with it (twosl_dsp/preset_loudness.py).
"""
import math

# The pre-filter's two stages at 48 kHz (Tables 1 and 2): (b0, b1, b2), (a1, a2), a0 = 1.
STAGE_1_AT_48_KHZ = ((1.53512485958697, -2.69169618940638, 1.19839281085285), (-1.69065929318241, 0.73248077421585))
STAGE_2_AT_48_KHZ = ((1.0, -2.0, 1.0), (-1.99004745483398, 0.99007225036621))
# "Implementations at other sampling rates will require different coefficient values, which should be chosen to
# provide the same frequency response": each stage's analog prototype (a high shelf; a high pass), read back from the
# 48 kHz coefficients through the bilinear transform, then put through it again at our rate.
# tests/test_bs1770.py holds the result to the 48 kHz response.
STANDARD_RATE = 48000


def _high_shelf_prototype_of(b, a, rate):
    """(K, Vh, Vb, Q) of b = (Vh + Vb K/Q + K^2, 2 (K^2 - Vh), Vh - Vb K/Q + K^2) / a0,
    a = (2 (K^2 - 1), 1 - K/Q + K^2) / a0, a0 = 1 + K/Q + K^2 (the RBJ-style shelf of the bilinear transform)."""
    a1, a2 = a
    # from a1 and a2: (1 + K^2) / a0 and (K^2 - 1) / a0, so 1 / a0 and K^2, then K/Q = a0 - 1 - K^2
    k_squared_plus_one_over_a0 = (1 + a2) / 2                    # (1 + K^2) / a0
    k_squared_minus_one_over_a0 = a1 / 2                         # (K^2 - 1) / a0
    one_over_a0 = (k_squared_plus_one_over_a0 - k_squared_minus_one_over_a0) / 2
    a0 = 1 / one_over_a0
    k_squared = (k_squared_plus_one_over_a0 + k_squared_minus_one_over_a0) / 2 * a0
    k_over_q = a0 - 1 - k_squared
    k = math.sqrt(k_squared)
    q = k / k_over_q
    b0, b1, b2 = (coefficient * a0 for coefficient in b)
    vh = (b0 + b2) / 2 - k_squared
    vb = (b0 - b2) / 2 / (k / q)
    frequency = rate / math.pi * math.atan(k)
    return frequency, vh, vb, q


def _high_shelf_at(frequency, vh, vb, q, rate):
    k = math.tan(math.pi * frequency / rate)
    a0 = 1 + k / q + k * k
    b = ((vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0)
    a = (2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0)
    return b, a


def _high_pass_prototype_of(a, rate):
    """(frequency, Q) of a = (2 (K^2 - 1), 1 - K/Q + K^2) / a0, a0 = 1 + K/Q + K^2 (numerator 1, -2, 1 as Table 2)."""
    a1, a2 = a
    k_squared_plus_one_over_a0 = (1 + a2) / 2
    k_squared_minus_one_over_a0 = a1 / 2
    a0 = 1 / ((k_squared_plus_one_over_a0 - k_squared_minus_one_over_a0) / 2)
    k_squared = (k_squared_plus_one_over_a0 + k_squared_minus_one_over_a0) / 2 * a0
    k = math.sqrt(k_squared)
    q = k / (a0 - 1 - k_squared)
    return rate / math.pi * math.atan(k), q


def _high_pass_at(frequency, q, rate):
    """Table 2's form (numerator 1, -2, 1: unity at Nyquist, as the table's) at `rate`."""
    k = math.tan(math.pi * frequency / rate)
    a0 = 1 + k / q + k * k
    return (1.0, -2.0, 1.0), (2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0)


def k_weighting_stages(rate):
    """The two pre-filter stages at `rate`: [(b, a), (b, a)]; at 48 kHz exactly Tables 1 and 2."""
    if rate == STANDARD_RATE:
        return [STAGE_1_AT_48_KHZ, STAGE_2_AT_48_KHZ]
    shelf = _high_shelf_prototype_of(*STAGE_1_AT_48_KHZ, STANDARD_RATE)
    high_pass = _high_pass_prototype_of(STAGE_2_AT_48_KHZ[1], STANDARD_RATE)
    return [_high_shelf_at(*shelf, rate), _high_pass_at(*high_pass, rate)]


def biquad_response_db(b, a, frequency, rate):
    z = complex(math.cos(2 * math.pi * frequency / rate), math.sin(2 * math.pi * frequency / rate))
    numerator = b[0] + b[1] / z + b[2] / (z * z)
    denominator = 1 + a[0] / z + a[1] / (z * z)
    return 20 * math.log10(abs(numerator / denominator))


def _biquad(samples, b, a):
    b0, b1, b2 = b
    a1, a2 = a
    x1 = x2 = y1 = y2 = 0.0
    out = []
    append = out.append
    for x in samples:
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, x, y1, y
        append(y)
    return out


def _weighted_power_sums(channels, rate):
    """The running sum of the K-weighted channels' squares, the channels added (each weight 1.0, L and R):
    [0, x0^2, x0^2 + x1^2, ...], so any window's mean square is one subtraction."""
    stages = k_weighting_stages(rate)
    summed = None
    for channel in channels:
        weighted = channel
        for b, a in stages:
            weighted = _biquad(weighted, b, a)
        cumulative = [0.0]
        total = 0.0
        for y in weighted:
            total += y * y
            cumulative.append(total)
        summed = cumulative if summed is None else [p + q for p, q in zip(summed, cumulative)]
    return summed


def _loudness_of(power):
    """Equation 2: the loudness (LKFS) of a mean square summed over the channels."""
    return -0.691 + 10 * math.log10(power) if power > 0 else -math.inf


def _window_samples(channels, rate):
    """400 ms "to the nearest sample", failing loudly when a channel is shorter."""
    window = int(round(0.4 * rate))
    if any(len(channel) < window for channel in channels):
        raise ValueError(f"{min(map(len, channels))} samples: under one 400 ms window")
    return window


def integrated_loudness(channels, rate):
    """BS.1770-5 gated loudness (LKFS) of `channels` (lists of samples; L and R, each weight 1.0). Fails loudly when
    the signal is too short for one gating block or every block is under the absolute gate."""
    block = _window_samples(channels, rate)
    step = block // 4                                             # 75 % overlap
    sums = _weighted_power_sums(channels, rate)
    block_powers = [(sums[start + block] - sums[start]) / block for start in range(0, len(sums) - block, step)]
    absolute_gate = -70.0
    above_absolute = [power for power in block_powers if _loudness_of(power) > absolute_gate]
    if not above_absolute:
        raise ValueError("every gating block is under -70 LKFS: silence")
    relative_gate = _loudness_of(sum(above_absolute) / len(above_absolute)) - 10
    gated = [power for power in above_absolute if _loudness_of(power) > relative_gate]
    return _loudness_of(sum(gated) / len(gated))


def max_momentary_loudness(channels, rate):
    """The loudest moment of `channels` (LUFS): EBU Mode's Momentary Loudness (EBU Tech 3341 §2.2: BS.1770's
    loudness over "a sliding rectangular time window of length 0.4 s", "not gated") at its maximum, the window slid
    one sample at a time over every full 400 ms of the signal (a file meter's exact start, Tech 3341 test case 13).
    Fails loudly when the signal is shorter than one window or silent."""
    window = _window_samples(channels, rate)
    sums = _weighted_power_sums(channels, rate)
    loudest = max(sums[end] - sums[end - window] for end in range(window, len(sums)))
    if loudest <= 0:
        raise ValueError("every 400 ms window is silent")
    return _loudness_of(loudest / window)


# Annex 2: 4x over-sampling, the 48-tap interpolating FIR, one row per phase.
TRUE_PEAK_PHASES = [
    [0.0017089843750, 0.0109863281250, -0.0196533203125, 0.0332031250000, -0.0594482421875, 0.1373291015625,
     0.9721679687500, -0.1022949218750, 0.0476074218750, -0.0266113281250, 0.0148925781250, -0.0083007812500],
    [-0.0291748046875, 0.0292968750000, -0.0517578125000, 0.0891113281250, -0.1665039062500, 0.4650878906250,
     0.7797851562500, -0.2003173828125, 0.1015625000000, -0.0582275390625, 0.0330810546875, -0.0189208984375],
    [-0.0189208984375, 0.0330810546875, -0.0582275390625, 0.1015625000000, -0.2003173828125, 0.7797851562500,
     0.4650878906250, -0.1665039062500, 0.0891113281250, -0.0517578125000, 0.0292968750000, -0.0291748046875],
    [-0.0083007812500, 0.0148925781250, -0.0266113281250, 0.0476074218750, -0.1022949218750, 0.9721679687500,
     0.1373291015625, -0.0594482421875, 0.0332031250000, -0.0196533203125, 0.0109863281250, 0.0017089843750]]


def true_peak_db(channels):
    """BS.1770-5 Annex 2 true peak (dBTP) over `channels`, in floating point (no 12.04 dB attenuation needed)."""
    highest = 0.0
    taps = len(TRUE_PEAK_PHASES[0])
    for channel in channels:
        padded = [0.0] * (taps - 1) + list(channel)
        for index in range(len(channel)):
            window = padded[index:index + taps]
            for phase in TRUE_PEAK_PHASES:
                value = abs(sum(c * x for c, x in zip(phase, reversed(window))))
                if value > highest:
                    highest = value
    return 20 * math.log10(highest) if highest > 0 else -math.inf


def sample_peak_db(channels):
    highest = max(max(abs(x) for x in channel) for channel in channels)
    return 20 * math.log10(highest) if highest > 0 else -math.inf
