/* The patch matcher's analysis (twosl_dsp/patch_match_score.py, architecture/patch-matcher.md,
 * references/sound-matching.md): a hit is aligned at its onset, loudness-normalised (BS.1770 K-weighting,
 * EBU Tech 3341's loudest 400 ms window), and turned into features:
 *   - a log-mel spectrogram at each of several FFT sizes (the multi-scale spectral comparison of DDSP / Parallel
 *     WaveGAN, on a mel scale),
 *   - an amplitude envelope in dB (a peak follower: the attack's fine timing).
 * match_distance compares two feature vectors of the same analysis length and rate: the spectrograms cell by cell, the
 * envelopes, and each frame's log-frequency spectral centroid (the ordering of pitch and brightness, which a cell by
 * cell distance lacks).
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

#define DECIBEL_OF_ZERO -200.0

/* the distance's choices */
#define SPECTRAL_DYNAMIC_RANGE_DB 70.0  /* cells more than this under the target's loudest cell are "floor" */
#define ENVELOPE_DYNAMIC_RANGE_DB 70.0
/* the centroid term: a target frame counts fully within CENTROID_FULL_RANGE_DB of the loudest frame (its floored
 * mel power, per resolution), not at all CENTROID_ZERO_RANGE_DB under it, linearly between: a frame of the decay's
 * floor has no meaningful centroid */
#define CENTROID_FULL_RANGE_DB 20.0
#define CENTROID_ZERO_RANGE_DB 40.0

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
/* the feature vector: per resolution [frames x bands] dB, then envelope [frames] dB */
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
 * (k_weights = b0 b1 b2 a1 a2 of stage 1, then of stage 2, from twosl_dsp/bs1770.py), the mean square over a sliding
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

/* a resolution's mel triangle edges (bands + 2 of them, Hz): band b spans edges[b] .. edges[b + 2], centred on
 * edges[b + 1] */
static void mel_band_edges(double rate, int resolution, double *edges)
{
    long size = FFT_SIZES[resolution];
    long bands = MEL_BAND_COUNTS[resolution];
    double bin_hertz = rate / (double)size;
    double lowest = MEL_LOWEST_HZ > MEL_LOWEST_BIN * bin_hertz ? MEL_LOWEST_HZ : MEL_LOWEST_BIN * bin_hertz;
    double highest = MEL_HIGHEST_HZ < 0.5 * rate ? MEL_HIGHEST_HZ : 0.5 * rate;
    double lowest_mel = hertz_to_mel(lowest);
    double highest_mel = hertz_to_mel(highest);
    for (long edge = 0; edge < bands + 2; edge++) {
        edges[edge] = mel_to_hertz(lowest_mel + (highest_mel - lowest_mel) * (double)edge / (double)(bands + 1));
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
    double *edges = (double *)malloc(sizeof(double) * (size_t)(bands + 2));
    double *window = (double *)malloc(sizeof(double) * (size_t)size);
    double *power = (double *)malloc(sizeof(double) * (size_t)bins);
    if (edges == NULL || window == NULL || power == NULL) {
        free(edges); free(window); free(power);
        return MATCH_OUT_OF_MEMORY;
    }
    mel_band_edges(rate, resolution, edges);
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
    if (prepare_twiddles(FFT_SIZES[0]) != MATCH_OK) {
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

/* The log-frequency spectral centroid term of one resolution's [frames x bands] dB block, accumulated into *total and
 * *weight_total: per frame, both spectra floored at the target block's loudest cell minus the spectral range (as the
 * spectral term floors them), each band's power at the log2 of its centre frequency, the centroid's difference in
 * semitones, weighted by the target frame's level. Turian & Henry 2020 (references/sound-matching.md, D): the log2
 * spectral centroid ordered pitch differences perfectly at +-30 and +-600 cents where cell by cell spectral
 * distances did not; it is a smooth function of the hit, so a derivative-free search can follow it. */
static int accumulate_centroid_term(const double *target, const double *candidate, long frames, long bands,
                                    const double *log2_centres, double *total, double *weight_total)
{
    long count = frames * bands;
    double loudest_cell = DECIBEL_OF_ZERO;
    for (long index = 0; index < count; index++) {
        if (target[index] > loudest_cell) {
            loudest_cell = target[index];
        }
    }
    double floor_db = loudest_cell - SPECTRAL_DYNAMIC_RANGE_DB;
    double *frame_levels = (double *)malloc(sizeof(double) * (size_t)(frames > 0 ? frames : 1));
    if (frame_levels == NULL) {
        return MATCH_OUT_OF_MEMORY;
    }
    double loudest_frame = DECIBEL_OF_ZERO;
    for (long frame = 0; frame < frames; frame++) {
        double power = 0.0;
        for (long band = 0; band < bands; band++) {
            double t = target[frame * bands + band];
            power += pow(10.0, (t > floor_db ? t : floor_db) / 10.0);
        }
        frame_levels[frame] = decibels_of_power(power);
        if (frame_levels[frame] > loudest_frame) {
            loudest_frame = frame_levels[frame];
        }
    }
    for (long frame = 0; frame < frames; frame++) {
        double weight = (frame_levels[frame] - (loudest_frame - CENTROID_ZERO_RANGE_DB))
                        / (CENTROID_ZERO_RANGE_DB - CENTROID_FULL_RANGE_DB);
        weight = weight < 0.0 ? 0.0 : (weight > 1.0 ? 1.0 : weight);
        if (weight <= 0.0) {
            continue;
        }
        double target_power = 0.0, target_moment = 0.0, candidate_power = 0.0, candidate_moment = 0.0;
        for (long band = 0; band < bands; band++) {
            double t = target[frame * bands + band];
            double c = candidate[frame * bands + band];
            double tp = pow(10.0, (t > floor_db ? t : floor_db) / 10.0);
            double cp = pow(10.0, (c > floor_db ? c : floor_db) / 10.0);
            target_power += tp;
            target_moment += tp * log2_centres[band];
            candidate_power += cp;
            candidate_moment += cp * log2_centres[band];
        }
        double difference = target_moment / target_power - candidate_moment / candidate_power;
        *total += weight * 12.0 * fabs(difference);
        *weight_total += weight;
    }
    free(frame_levels);
    return MATCH_OK;
}

/* components_out: [spectral dB, envelope dB, centroid semitones]. The spectral term is the mean over resolutions of
 * each resolution's floored mean difference; the centroid term is the level-weighted mean over the frames of the
 * whole-hit resolutions (the attack-only ones are left out: their few frames would count as much as a long one's). */
int match_distance(const double *target, const double *candidate, long analysis_length, double rate,
                   double *components_out)
{
    if (analysis_length <= 0 || !(rate > 0)) {
        return MATCH_BAD_ARGUMENT;
    }
    long offset = 0;
    double spectral = 0.0, centroid_total = 0.0, centroid_weight = 0.0;
    double edges[64 + 2], log2_centres[64];
    for (int resolution = 0; resolution < RESOLUTION_COUNT; resolution++) {
        long frames = resolution_frames(analysis_length, rate, resolution);
        long bands = MEL_BAND_COUNTS[resolution];
        long count = frames * bands;
        spectral += floored_mean_difference(target + offset, candidate + offset, count, SPECTRAL_DYNAMIC_RANGE_DB);
        if (FFT_SIZES[resolution] >= ATTACK_ONLY_BELOW_SIZE) {
            if (bands > 64) {
                return MATCH_BAD_ARGUMENT;
            }
            mel_band_edges(rate, resolution, edges);
            for (long band = 0; band < bands; band++) {
                log2_centres[band] = log2(edges[band + 1]);
            }
            int status = accumulate_centroid_term(target + offset, candidate + offset, frames, bands, log2_centres,
                                                  &centroid_total, &centroid_weight);
            if (status != MATCH_OK) {
                return status;
            }
        }
        offset += count;
    }
    spectral /= (double)RESOLUTION_COUNT;
    long envelope_frames = frames_of(analysis_length, envelope_hop(rate));
    double envelope = floored_mean_difference(target + offset, candidate + offset, envelope_frames,
                                              ENVELOPE_DYNAMIC_RANGE_DB);
    components_out[0] = spectral;
    components_out[1] = envelope;
    components_out[2] = centroid_weight > 0.0 ? centroid_total / centroid_weight : 0.0;
    return MATCH_OK;
}
