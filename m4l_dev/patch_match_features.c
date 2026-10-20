/* The patch matcher's analysis (m4l_dev/patch_match_score.py, architecture/patch-matcher.md,
 * references/sound-matching.md): a hit is aligned at its onset, loudness-normalised (BS.1770 K-weighting,
 * EBU Tech 3341's loudest 400 ms window), and turned into features:
 *   - a log-mel spectrogram at each of several FFT sizes (the multi-scale spectral comparison of DDSP / Parallel
 *     WaveGAN, on a mel scale),
 *   - an amplitude envelope in dB (a peak follower: the attack's fine timing),
 *   - a YIN pitch track (f0, aperiodicity, level per frame) for the tonal part of a hit.
 * match_distance compares two feature vectors of the same analysis length and rate.
 * Built by patch_match_score.py with the system C compiler into the kit's cache; plain C99, no fast-math.
 * Every layout decision lives here (match_feature_size): Python never computes an offset.
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>

/* four sizes, not DDSP's six: 256 and 128 (5.3 and 2.7 ms at 48 kHz) are shorter than a kick's cycle all through its
 * attack, so they score where in the cycle the tone is, not how it sounds (measured on the fixture drum voice: a 0.24
 * semitone change of pitch sweep moved their difference from 3 to 10 dB while 512 .. 4096 moved under 0.2 dB). The
 * attack's fine timing is the envelope's (instant attack). Mel bands: about one per 1.5 .. 3 bins at the low end. */
#define RESOLUTION_COUNT 4
static const long FFT_SIZES[RESOLUTION_COUNT] = {4096, 2048, 1024, 512};
static const long MEL_BAND_COUNTS[RESOLUTION_COUNT] = {48, 40, 32, 24};
#define MEL_LOWEST_HZ 20.0
#define MEL_HIGHEST_HZ 16000.0
/* the lowest band edge of a resolution is at least this many of its bins: a short FFT says nothing about the lows */
#define MEL_LOWEST_BIN 1.5

/* the FFT sizes under this see only the attack: the first ATTACK_SECONDS. Past the attack, a short window of a low
 * tone sees where in its cycle it is (measured: 0.25 semitone more pitch sweep on a 42 Hz driven kick moved the 128-point
 * spectrogram's difference from 3.6 to 6.7 dB), the cycle's phase, which is not what a hit sounds like. */
#define ATTACK_ONLY_BELOW_SIZE 1024
#define ATTACK_SECONDS 0.05
/* the envelope: a peak follower of the squared signal (instant attack, exponential release), read every hop. The
 * release bridges the troughs of a low tone's cycle (25 Hz: 20 ms half cycles), so the envelope is the hit's, not the
 * cycle's; decays shorter than the release are left to the spectrograms. */
#define ENVELOPE_RELEASE_SECONDS 0.05
#define ENVELOPE_HOP_SECONDS 0.0025

#define PITCH_WINDOW_SECONDS 0.02
#define PITCH_HOP_SECONDS 0.01
#define PITCH_LOWEST_HZ 25.0
#define PITCH_HIGHEST_HZ 2000.0
#define PITCH_ANALYSIS_RATE 12000.0     /* YIN runs on the hit decimated to about this rate (whole factor) */
#define PITCH_THRESHOLD 0.3             /* YIN suggests 0.1 ("not critical"); 0.3: see pitch_track */

#define DECIBEL_OF_ZERO -200.0

/* the distance's choices */
#define SPECTRAL_DYNAMIC_RANGE_DB 70.0  /* cells more than this under the target's loudest cell are "floor" */
#define ENVELOPE_DYNAMIC_RANGE_DB 70.0
/* how much a target frame's pitch counts: 1 under FULLY_TONAL, 0 over NOT_TONAL, linear between, times the same ramp
 * on its level (1 within TONAL_RANGE_DB of the loudest frame, 0 at twice that). Soft, so a frame on the edge of
 * tonal does not flip the score between two renders of one sound with different noise. */
#define FULLY_TONAL_APERIODICITY 0.1
#define NOT_TONAL_APERIODICITY 0.3
#define TONAL_RANGE_DB 20.0
#define PITCH_ERROR_CAP_SEMITONES 12.0  /* a wrong pitch costs at most an octave per frame */

enum {
    MATCH_OK = 0,
    MATCH_SILENT = 1,
    MATCH_NOT_FINITE = 2,
    MATCH_OUT_OF_MEMORY = 3,
    MATCH_BAD_ARGUMENT = 4
};

/* ------------------------------------------------------------------ the FFT (radix 2, in place, cached twiddles) */

static long twiddle_size = 0;
static double *twiddle_cosines = NULL;
static double *twiddle_sines = NULL;

static int prepare_twiddles(long size)
{
    if (size <= twiddle_size) {
        return MATCH_OK;
    }
    double *cosines = (double *)malloc(sizeof(double) * (size_t)(size / 2));
    double *sines = (double *)malloc(sizeof(double) * (size_t)(size / 2));
    if (cosines == NULL || sines == NULL) {
        free(cosines);
        free(sines);
        return MATCH_OUT_OF_MEMORY;
    }
    for (long index = 0; index < size / 2; index++) {
        cosines[index] = cos(2.0 * M_PI * (double)index / (double)size);
        sines[index] = -sin(2.0 * M_PI * (double)index / (double)size);
    }
    free(twiddle_cosines);
    free(twiddle_sines);
    twiddle_cosines = cosines;
    twiddle_sines = sines;
    twiddle_size = size;
    return MATCH_OK;
}

/* forward transform of size `size` (a power of two <= twiddle_size); inverse = conjugate in and out */
static void fft_in_place(double *real, double *imaginary, long size)
{
    for (long index = 1, reversed = 0; index < size; index++) {
        long bit = size >> 1;
        for (; reversed & bit; bit >>= 1) {
            reversed ^= bit;
        }
        reversed ^= bit;
        if (index < reversed) {
            double swap = real[index]; real[index] = real[reversed]; real[reversed] = swap;
            swap = imaginary[index]; imaginary[index] = imaginary[reversed]; imaginary[reversed] = swap;
        }
    }
    for (long length = 2; length <= size; length <<= 1) {
        long stride = twiddle_size / length;
        long half = length / 2;
        for (long start = 0; start < size; start += length) {
            for (long offset = 0; offset < half; offset++) {
                double w_real = twiddle_cosines[offset * stride];
                double w_imaginary = twiddle_sines[offset * stride];
                long upper = start + offset;
                long lower = upper + half;
                double t_real = real[lower] * w_real - imaginary[lower] * w_imaginary;
                double t_imaginary = real[lower] * w_imaginary + imaginary[lower] * w_real;
                real[lower] = real[upper] - t_real;
                imaginary[lower] = imaginary[upper] - t_imaginary;
                real[upper] += t_real;
                imaginary[upper] += t_imaginary;
            }
        }
    }
}

/* ------------------------------------------------------------------ layout */

static long frames_of(long analysis_length, long hop)
{
    return (analysis_length + hop - 1) / hop;
}

/* a resolution's frames: the whole hit, or (a short FFT) its attack */
static long resolution_frames(long analysis_length, double rate, int resolution)
{
    long span = analysis_length;
    if (FFT_SIZES[resolution] < ATTACK_ONLY_BELOW_SIZE) {
        long attack = lround(ATTACK_SECONDS * rate);
        span = attack < analysis_length ? attack : analysis_length;
    }
    return frames_of(span, FFT_SIZES[resolution] / 4);
}

static long envelope_hop(double rate) { long hop = lround(ENVELOPE_HOP_SECONDS * rate); return hop < 1 ? 1 : hop; }
static long pitch_hop(double rate) { long hop = lround(PITCH_HOP_SECONDS * rate); return hop < 1 ? 1 : hop; }
static long pitch_window(double rate) { long w = lround(PITCH_WINDOW_SECONDS * rate); return w < 2 ? 2 : w; }
static long pitch_longest_lag(double rate) { return (long)ceil(rate / PITCH_LOWEST_HZ); }
static long pitch_shortest_lag(double rate) { long lag = (long)floor(rate / PITCH_HIGHEST_HZ); return lag < 2 ? 2 : lag; }

static long pitch_decimation(double rate) { long factor = (long)floor(rate / PITCH_ANALYSIS_RATE); return factor < 1 ? 1 : factor; }

static long pitch_fft_size(double rate)
{
    long needed = 2 * pitch_window(rate) + pitch_longest_lag(rate);
    long size = 1;
    while (size < needed) {
        size <<= 1;
    }
    return size;
}

/* the feature vector: per resolution [frames x bands] dB, then envelope [frames] dB, then pitch [frames x 3]
 * (f0 Hz or 0, aperiodicity, level dB) */
long match_feature_size(long analysis_length, double rate)
{
    if (analysis_length <= 0 || !(rate > 0)) {
        return -1;
    }
    long size = 0;
    for (int resolution = 0; resolution < RESOLUTION_COUNT; resolution++) {
        size += resolution_frames(analysis_length, rate, resolution) * MEL_BAND_COUNTS[resolution];
    }
    size += frames_of(analysis_length, envelope_hop(rate));
    size += 3 * frames_of(analysis_length, pitch_hop(rate));
    return size;
}

/* ------------------------------------------------------------------ onset, alignment, loudness */

/* the first sample at least threshold_db under the peak (relative), or -1 when the signal is silent */
long match_onset(const double *signal, long length, double threshold_db)
{
    double peak = 0.0;
    for (long index = 0; index < length; index++) {
        double magnitude = fabs(signal[index]);
        if (magnitude > peak) {
            peak = magnitude;
        }
    }
    if (!(peak > 0.0)) {
        return -1;
    }
    double threshold = peak * pow(10.0, threshold_db / 20.0);
    for (long index = 0; index < length; index++) {
        if (fabs(signal[index]) >= threshold) {
            return index;
        }
    }
    return -1;
}

/* EBU Tech 3341's maximum momentary loudness (LUFS) of one channel: the two K-weighting biquads
 * (k_weights = b0 b1 b2 a1 a2 of stage 1, then of stage 2, from m4l_dev/bs1770.py), the mean square over a sliding
 * 400 ms window, a signal shorter than one window counted as zero-padded to it. -inf when silent. */
double match_max_momentary_loudness(const double *signal, long length, double rate, const double *k_weights)
{
    long window = lround(0.4 * rate);
    long padded_length = length < window ? window : length;
    double *cumulative = (double *)malloc(sizeof(double) * (size_t)(padded_length + 1));
    if (cumulative == NULL) {
        return NAN;
    }
    double x1a = 0, x2a = 0, y1a = 0, y2a = 0, x1b = 0, x2b = 0, y1b = 0, y2b = 0;
    cumulative[0] = 0.0;
    for (long index = 0; index < padded_length; index++) {
        double x = index < length ? signal[index] : 0.0;
        double ya = k_weights[0] * x + k_weights[1] * x1a + k_weights[2] * x2a - k_weights[3] * y1a - k_weights[4] * y2a;
        x2a = x1a; x1a = x; y2a = y1a; y1a = ya;
        double yb = k_weights[5] * ya + k_weights[6] * x1b + k_weights[7] * x2b - k_weights[8] * y1b - k_weights[9] * y2b;
        x2b = x1b; x1b = ya; y2b = y1b; y1b = yb;
        cumulative[index + 1] = cumulative[index] + yb * yb;
    }
    double loudest = 0.0;
    for (long end = window; end <= padded_length; end++) {
        double power = cumulative[end] - cumulative[end - window];
        if (power > loudest) {
            loudest = power;
        }
    }
    free(cumulative);
    if (!(loudest > 0.0)) {
        return -INFINITY;
    }
    return -0.691 + 10.0 * log10(loudest / (double)window);
}

/* ------------------------------------------------------------------ the features */

static double hertz_to_mel(double hertz) { return 2595.0 * log10(1.0 + hertz / 700.0); }
static double mel_to_hertz(double mel) { return 700.0 * (pow(10.0, mel / 2595.0) - 1.0); }

static double decibels_of_power(double power)
{
    return power > 0.0 ? 10.0 * log10(power) : DECIBEL_OF_ZERO;
}

static void mel_bands_of_power(const double *power, long bins, double bin_hertz, const double *edges, long bands,
                               long size, double *out)
{
    for (long band = 0; band < bands; band++) {
        double left = edges[band], centre = edges[band + 1], right = edges[band + 2];
        long first_bin = (long)ceil(left / bin_hertz);
        long last_bin = (long)floor(right / bin_hertz);
        double energy = 0.0, weight_total = 0.0;
        for (long bin = first_bin; bin <= last_bin && bin < bins; bin++) {
            double hertz = (double)bin * bin_hertz;
            double weight = hertz <= centre ? (hertz - left) / (centre - left) : (right - hertz) / (right - centre);
            if (weight > 0.0) {
                energy += weight * power[bin];
                weight_total += weight;
            }
        }
        if (weight_total <= 0.0) {
            /* a band narrower than a bin: the triangle's value at its centre, from the nearest bin */
            long nearest = lround(centre / bin_hertz);
            energy = nearest < bins ? power[nearest] : 0.0;
            weight_total = 1.0;
        }
        out[band] = decibels_of_power(energy / weight_total / (double)size);
    }
}

static int log_mel_spectrogram(const double *aligned, long length, double rate, int resolution, double *out,
                               double *real, double *imaginary)
{
    long size = FFT_SIZES[resolution];
    long hop = size / 4;
    long bands = MEL_BAND_COUNTS[resolution];
    long frames = resolution_frames(length, rate, resolution);
    long bins = size / 2 + 1;
    double bin_hertz = rate / (double)size;
    double lowest = MEL_LOWEST_HZ > MEL_LOWEST_BIN * bin_hertz ? MEL_LOWEST_HZ : MEL_LOWEST_BIN * bin_hertz;
    double highest = MEL_HIGHEST_HZ < 0.5 * rate ? MEL_HIGHEST_HZ : 0.5 * rate;
    double lowest_mel = hertz_to_mel(lowest);
    double highest_mel = hertz_to_mel(highest);
    double *edges = (double *)malloc(sizeof(double) * (size_t)(bands + 2));
    double *window = (double *)malloc(sizeof(double) * (size_t)size);
    double *power = (double *)malloc(sizeof(double) * (size_t)bins);
    if (edges == NULL || window == NULL || power == NULL) {
        free(edges); free(window); free(power);
        return MATCH_OUT_OF_MEMORY;
    }
    for (long edge = 0; edge < bands + 2; edge++) {
        edges[edge] = mel_to_hertz(lowest_mel + (highest_mel - lowest_mel) * (double)edge / (double)(bands + 1));
    }
    for (long index = 0; index < size; index++) {
        window[index] = 0.5 - 0.5 * cos(2.0 * M_PI * (double)index / (double)size);   /* periodic Hann */
    }
    /* two real frames per complex FFT: frame a in the real part, frame b in the imaginary part */
    double *power_b = (double *)malloc(sizeof(double) * (size_t)bins);
    if (power_b == NULL) {
        free(edges); free(window); free(power);
        return MATCH_OUT_OF_MEMORY;
    }
    for (long frame = 0; frame < frames; frame += 2) {
        long start_a = frame * hop - size / 2;   /* frames centred on frame * hop, zeros outside the signal */
        long start_b = start_a + hop;
        int has_b = frame + 1 < frames;
        for (long index = 0; index < size; index++) {
            long source_a = start_a + index;
            long source_b = start_b + index;
            real[index] = (source_a >= 0 && source_a < length) ? aligned[source_a] * window[index] : 0.0;
            imaginary[index] = (has_b && source_b >= 0 && source_b < length) ? aligned[source_b] * window[index] : 0.0;
        }
        fft_in_place(real, imaginary, size);
        for (long bin = 0; bin < bins; bin++) {
            long mirror = (size - bin) % size;
            double zr = real[bin], zi = imaginary[bin], wr = real[mirror], wi = imaginary[mirror];
            power[bin] = 0.25 * ((zr + wr) * (zr + wr) + (zi - wi) * (zi - wi));
            power_b[bin] = 0.25 * ((zi + wi) * (zi + wi) + (zr - wr) * (zr - wr));
        }
        mel_bands_of_power(power, bins, bin_hertz, edges, bands, size, out + frame * bands);
        if (has_b) {
            mel_bands_of_power(power_b, bins, bin_hertz, edges, bands, size, out + (frame + 1) * bands);
        }
    }
    free(power_b);
    free(edges); free(window); free(power);
    return MATCH_OK;
}

static void amplitude_envelope(const double *aligned, long length, double rate, double *out)
{
    long hop = envelope_hop(rate);
    long frames = frames_of(length, hop);
    double release = exp(-1.0 / (ENVELOPE_RELEASE_SECONDS * rate));
    double follower = 0.0;
    for (long index = 0, frame = 0; index < length && frame < frames; index++) {
        double power = aligned[index] * aligned[index];
        follower = power > follower ? power : follower * release;
        if (index == frame * hop) {
            out[frame++] = decibels_of_power(follower);
        }
    }
}

/* YIN (de Cheveigne & Kawahara 2002): the difference function from one cross-correlation by FFT, the cumulative mean
 * normalised difference, the first dip under the absolute threshold (else the global minimum), parabolic
 * interpolation. Per frame: f0 (Hz), aperiodicity (the normalised difference at the chosen lag), level (dB of the
 * frame's mean square). The threshold is 0.3, not YIN's 0.1: on noisy hits (measured: the fixture drum voice, noise
 * 0.84, a 357 Hz tone) frames whose dip was over 0.1 fell to the global minimum, a subharmonic (178, 89 Hz), and which
 * one changed with the noise's realisation; the first dip under 0.3 is the tone. */
static int pitch_track(const double *full_rate_signal, long full_length, double full_rate, double *out)
{
    /* decimated first (Hann-windowed sinc low-pass at 0.8 of the new Nyquist, 8 x factor + 1 taps): pitches up to
     * PITCH_HIGHEST_HZ need no more, and the transforms get factor^2 cheaper */
    long factor = pitch_decimation(full_rate);
    double rate = full_rate / (double)factor;
    long length = full_length / factor;
    double *aligned = (double *)malloc(sizeof(double) * (size_t)(length > 0 ? length : 1));
    long half_taps = 4 * factor;
    double *taps = (double *)malloc(sizeof(double) * (size_t)(2 * half_taps + 1));
    if (aligned == NULL || taps == NULL) {
        free(aligned); free(taps);
        return MATCH_OUT_OF_MEMORY;
    }
    double cutoff = 0.8 * 0.5 / (double)factor, tap_total = 0.0;
    for (long tap = -half_taps; tap <= half_taps; tap++) {
        double sinc = tap == 0 ? 1.0 : sin(2.0 * M_PI * cutoff * (double)tap) / (2.0 * M_PI * cutoff * (double)tap);
        double hann = 0.5 + 0.5 * cos(M_PI * (double)tap / (double)(half_taps + 1));
        taps[tap + half_taps] = factor == 1 ? (tap == 0 ? 1.0 : 0.0) : sinc * hann;
        tap_total += taps[tap + half_taps];
    }
    for (long index = 0; index < length; index++) {
        double sum = 0.0;
        for (long tap = -half_taps; tap <= half_taps; tap++) {
            long source = index * factor + tap;
            if (source >= 0 && source < full_length) {
                sum += taps[tap + half_taps] * full_rate_signal[source];
            }
        }
        aligned[index] = sum / tap_total;
    }
    free(taps);
    long full_hop = pitch_hop(full_rate);
    long window = pitch_window(rate);
    long longest_lag = pitch_longest_lag(rate);
    long shortest_lag = pitch_shortest_lag(rate);
    long size = pitch_fft_size(rate);
    long frames = frames_of(full_length, full_hop);
    long span = window + longest_lag;
    double *frame_real = (double *)malloc(sizeof(double) * (size_t)size);
    double *frame_imaginary = (double *)malloc(sizeof(double) * (size_t)size);
    double *span_real = (double *)malloc(sizeof(double) * (size_t)size);
    double *span_imaginary = (double *)malloc(sizeof(double) * (size_t)size);
    double *squares = (double *)malloc(sizeof(double) * (size_t)(span + 1));
    double *normalised = (double *)malloc(sizeof(double) * (size_t)(longest_lag + 2));
    if (!frame_real || !frame_imaginary || !span_real || !span_imaginary || !squares || !normalised) {
        free(frame_real); free(frame_imaginary); free(span_real); free(span_imaginary); free(squares); free(normalised);
        free(aligned);
        return MATCH_OUT_OF_MEMORY;
    }
    for (long frame = 0; frame < frames; frame++) {
        long start = frame * full_hop / factor;
        squares[0] = 0.0;
        for (long index = 0; index < size; index++) {
            long source = start + index;
            double value = (index < span && source < length) ? aligned[source] : 0.0;
            span_real[index] = index < window ? value : 0.0;   /* the frame in the real part, */
            span_imaginary[index] = value;                     /* the span in the imaginary part: one FFT for both */
            if (index < span) {
                squares[index + 1] = squares[index] + value * value;
            }
        }
        double frame_energy = squares[window];
        double *result = out + 3 * frame;
        result[2] = decibels_of_power(frame_energy / (double)window);
        if (!(frame_energy > 0.0)) {
            result[0] = 0.0;
            result[1] = 1.0;
            continue;
        }
        fft_in_place(span_real, span_imaginary, size);
        /* F = (Z[k] + conj Z[-k]) / 2, S = (Z[k] - conj Z[-k]) / 2i; correlation r(lag) = sum_j frame[j] span[j + lag]
         * is the inverse transform of conj(F) S, done as the forward transform of its conjugate */
        for (long index = 0; index < size; index++) {
            long mirror = (size - index) % size;
            double zr = span_real[index], zi = span_imaginary[index], wr = span_real[mirror], wi = span_imaginary[mirror];
            double f_real = 0.5 * (zr + wr), f_imaginary = 0.5 * (zi - wi);
            double s_real = 0.5 * (zi + wi), s_imaginary = -0.5 * (zr - wr);
            frame_real[index] = f_real * s_real + f_imaginary * s_imaginary;
            frame_imaginary[index] = -(f_real * s_imaginary - f_imaginary * s_real);
        }
        fft_in_place(frame_real, frame_imaginary, size);
        double running_sum = 0.0;
        normalised[0] = 1.0;
        for (long lag = 1; lag <= longest_lag; lag++) {
            double correlation = frame_real[lag] / (double)size;
            double lagged_energy = squares[lag + window] - squares[lag];
            double difference = frame_energy + lagged_energy - 2.0 * correlation;
            if (difference < 0.0) {
                difference = 0.0;
            }
            running_sum += difference;
            normalised[lag] = running_sum > 0.0 ? difference * (double)lag / running_sum : 1.0;
        }
        long chosen = -1;
        for (long lag = shortest_lag; lag < longest_lag; lag++) {
            if (normalised[lag] < PITCH_THRESHOLD) {
                while (lag + 1 < longest_lag && normalised[lag + 1] < normalised[lag]) {
                    lag++;
                }
                chosen = lag;
                break;
            }
        }
        if (chosen < 0) {
            chosen = shortest_lag;
            for (long lag = shortest_lag; lag < longest_lag; lag++) {
                if (normalised[lag] < normalised[chosen]) {
                    chosen = lag;
                }
            }
        }
        double refined = (double)chosen;
        if (chosen > shortest_lag && chosen + 1 < longest_lag) {
            double before = normalised[chosen - 1], at = normalised[chosen], after = normalised[chosen + 1];
            double curvature = before - 2.0 * at + after;
            if (curvature > 0.0) {
                refined += 0.5 * (before - after) / curvature;
            }
        }
        result[0] = rate / refined;
        result[1] = normalised[chosen];
    }
    free(aligned);
    free(frame_real); free(frame_imaginary); free(span_real); free(span_imaginary); free(squares); free(normalised);
    return MATCH_OK;
}

/* signal -> features. The analysed hit is `analysis_length` samples from `preroll` before the onset (zeros before the
 * signal's start), scaled so its loudest 400 ms reads reference_lufs. *gain_out: the gain applied (for the A/B file).
 * Returns MATCH_SILENT when the signal is silent, MATCH_NOT_FINITE when it holds a NaN or infinity. */
int match_analyse(const double *signal, long length, double rate, double onset_threshold_db, long preroll,
                  long analysis_length, const double *k_weights, double reference_lufs, double *features,
                  double *gain_out)
{
    if (length <= 0 || analysis_length <= 0 || !(rate > 0) || preroll < 0) {
        return MATCH_BAD_ARGUMENT;
    }
    for (long index = 0; index < length; index++) {
        if (!isfinite(signal[index])) {
            return MATCH_NOT_FINITE;
        }
    }
    long onset = match_onset(signal, length, onset_threshold_db);
    if (onset < 0) {
        return MATCH_SILENT;
    }
    long pitch_size = pitch_fft_size(rate / (double)pitch_decimation(rate));
    long largest_size = FFT_SIZES[0] > pitch_size ? FFT_SIZES[0] : pitch_size;
    if (prepare_twiddles(largest_size) != MATCH_OK) {
        return MATCH_OUT_OF_MEMORY;
    }
    double *aligned = (double *)malloc(sizeof(double) * (size_t)analysis_length);
    double *real = (double *)malloc(sizeof(double) * (size_t)FFT_SIZES[0]);
    double *imaginary = (double *)malloc(sizeof(double) * (size_t)FFT_SIZES[0]);
    if (!aligned || !real || !imaginary) {
        free(aligned); free(real); free(imaginary);
        return MATCH_OUT_OF_MEMORY;
    }
    long first = onset - preroll;
    for (long index = 0; index < analysis_length; index++) {
        long source = first + index;
        aligned[index] = (source >= 0 && source < length) ? signal[source] : 0.0;
    }
    double loudness = match_max_momentary_loudness(aligned, analysis_length, rate, k_weights);
    if (!(loudness > -INFINITY)) {
        free(aligned); free(real); free(imaginary);
        return isnan(loudness) ? MATCH_OUT_OF_MEMORY : MATCH_SILENT;
    }
    double gain = pow(10.0, (reference_lufs - loudness) / 20.0);
    for (long index = 0; index < analysis_length; index++) {
        aligned[index] *= gain;
    }
    *gain_out = gain;
    double *cursor = features;
    int status = MATCH_OK;
    for (int resolution = 0; resolution < RESOLUTION_COUNT && status == MATCH_OK; resolution++) {
        status = log_mel_spectrogram(aligned, analysis_length, rate, resolution, cursor, real, imaginary);
        cursor += resolution_frames(analysis_length, rate, resolution) * MEL_BAND_COUNTS[resolution];
    }
    if (status == MATCH_OK) {
        amplitude_envelope(aligned, analysis_length, rate, cursor);
        cursor += frames_of(analysis_length, envelope_hop(rate));
        status = pitch_track(aligned, analysis_length, rate, cursor);
    }
    free(aligned); free(real); free(imaginary);
    return status;
}

/* ------------------------------------------------------------------ the distance */

/* mean |difference| in dB over the cells where either is above the target's loudest cell minus the range */
static double floored_mean_difference(const double *target, const double *candidate, long count, double range_db)
{
    double loudest = DECIBEL_OF_ZERO;
    for (long index = 0; index < count; index++) {
        if (target[index] > loudest) {
            loudest = target[index];
        }
    }
    double floor_db = loudest - range_db;
    double total = 0.0;
    long cells = 0;
    for (long index = 0; index < count; index++) {
        double t = target[index] > floor_db ? target[index] : floor_db;
        double c = candidate[index] > floor_db ? candidate[index] : floor_db;
        if (t > floor_db || c > floor_db) {
            total += fabs(t - c);
            cells++;
        }
    }
    return cells > 0 ? total / (double)cells : 0.0;
}

/* components_out: [spectral dB, envelope dB, pitch semitones (the weighted mean), the target's tonal weight per frame].
 * The spectral term is the mean over resolutions of each resolution's floored mean difference. */
int match_distance(const double *target, const double *candidate, long analysis_length, double rate,
                   double *components_out)
{
    if (analysis_length <= 0 || !(rate > 0)) {
        return MATCH_BAD_ARGUMENT;
    }
    long offset = 0;
    double spectral = 0.0;
    for (int resolution = 0; resolution < RESOLUTION_COUNT; resolution++) {
        long count = resolution_frames(analysis_length, rate, resolution) * MEL_BAND_COUNTS[resolution];
        spectral += floored_mean_difference(target + offset, candidate + offset, count, SPECTRAL_DYNAMIC_RANGE_DB);
        offset += count;
    }
    spectral /= (double)RESOLUTION_COUNT;
    long envelope_frames = frames_of(analysis_length, envelope_hop(rate));
    double envelope = floored_mean_difference(target + offset, candidate + offset, envelope_frames,
                                              ENVELOPE_DYNAMIC_RANGE_DB);
    offset += envelope_frames;
    long pitch_frames = frames_of(analysis_length, pitch_hop(rate));
    const double *target_pitch = target + offset;
    const double *candidate_pitch = candidate + offset;
    double loudest_frame = DECIBEL_OF_ZERO;
    for (long frame = 0; frame < pitch_frames; frame++) {
        if (target_pitch[3 * frame + 2] > loudest_frame) {
            loudest_frame = target_pitch[3 * frame + 2];
        }
    }
    double pitch_total = 0.0, weight_total = 0.0;
    for (long frame = 0; frame < pitch_frames; frame++) {
        const double *t = target_pitch + 3 * frame;
        const double *c = candidate_pitch + 3 * frame;
        double tonal_weight = (NOT_TONAL_APERIODICITY - t[1]) / (NOT_TONAL_APERIODICITY - FULLY_TONAL_APERIODICITY);
        double level_weight = (t[2] - (loudest_frame - 2.0 * TONAL_RANGE_DB)) / TONAL_RANGE_DB;
        tonal_weight = tonal_weight < 0.0 ? 0.0 : (tonal_weight > 1.0 ? 1.0 : tonal_weight);
        level_weight = level_weight < 0.0 ? 0.0 : (level_weight > 1.0 ? 1.0 : level_weight);
        double weight = t[0] > 0.0 ? tonal_weight * level_weight : 0.0;
        if (weight <= 0.0) {
            continue;
        }
        /* the candidate's best period whether or not it is tonal there: noise where the target sings costs its
         * (random) pitch error, at most the cap */
        double error = PITCH_ERROR_CAP_SEMITONES;
        if (c[0] > 0.0) {
            error = fabs(12.0 * log2(c[0] / t[0]));
            if (error > PITCH_ERROR_CAP_SEMITONES) {
                error = PITCH_ERROR_CAP_SEMITONES;
            }
        }
        pitch_total += weight * error;
        weight_total += weight;
    }
    components_out[0] = spectral;
    components_out[1] = envelope;
    components_out[2] = weight_total > 0.0 ? pitch_total / weight_total : 0.0;
    components_out[3] = pitch_frames > 0 ? weight_total / (double)pitch_frames : 0.0;
    return MATCH_OK;
}
