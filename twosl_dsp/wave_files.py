"""WAV files in and out (the patch matcher's targets and its A/B renders): RIFF WAVE, PCM 8 / 16 / 24 / 32 bit, IEEE
float 32 / 64 bit, plain or WAVE_FORMAT_EXTENSIBLE, any rate and channel count. Written as 32-bit float. Anything
else (compressed formats, a truncated or malformed file) fails loudly, naming the file and what is wrong.
"""
import struct

from twosl_dsp.build_error import BuildError

FORMAT_PCM = 0x0001
FORMAT_IEEE_FLOAT = 0x0003
FORMAT_EXTENSIBLE = 0xFFFE


def read_wave_file(path):
    """(channels, rate): one list of floats per channel (PCM scaled to [-1, 1), float as stored)."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as problem:
        raise BuildError(f"{path}: cannot read: {problem}") from problem
    if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise BuildError(f"{path}: not a RIFF WAVE file")
    position = 12
    format_chunk = None
    sample_bytes = None
    while position + 8 <= len(data):
        chunk_id = data[position:position + 4]
        (chunk_size,) = struct.unpack_from("<I", data, position + 4)
        body = data[position + 8:position + 8 + chunk_size]
        if len(body) < chunk_size:
            if chunk_id == b"data":
                raise BuildError(f"{path}: the data chunk is truncated ({len(body)} of {chunk_size} bytes)")
            raise BuildError(f"{path}: the '{chunk_id.decode('latin-1')}' chunk is truncated")
        if chunk_id == b"fmt ":
            format_chunk = body
        elif chunk_id == b"data":
            sample_bytes = body
        position += 8 + chunk_size + (chunk_size & 1)
    if format_chunk is None or len(format_chunk) < 16:
        raise BuildError(f"{path}: no (complete) fmt chunk")
    if sample_bytes is None:
        raise BuildError(f"{path}: no data chunk")
    format_tag, channel_count, rate, _, block_align, bits = struct.unpack_from("<HHIIHH", format_chunk, 0)
    if format_tag == FORMAT_EXTENSIBLE:
        if len(format_chunk) < 40:
            raise BuildError(f"{path}: WAVE_FORMAT_EXTENSIBLE without its 22-byte extension")
        (format_tag,) = struct.unpack_from("<H", format_chunk, 24)   # the sub-format GUID's first two bytes
    if channel_count < 1 or rate < 1:
        raise BuildError(f"{path}: {channel_count} channels at {rate} Hz")
    if format_tag == FORMAT_PCM and bits in (8, 16, 24, 32):
        pass
    elif format_tag == FORMAT_IEEE_FLOAT and bits in (32, 64):
        pass
    else:
        raise BuildError(f"{path}: format {format_tag:#06x} at {bits} bits is not read here (PCM 8/16/24/32 or "
                            "float 32/64 only): export the target as one of those")
    bytes_per_sample = bits // 8
    if block_align != bytes_per_sample * channel_count:
        raise BuildError(f"{path}: block align {block_align} is not {bytes_per_sample} x {channel_count} channels")
    frame_count = len(sample_bytes) // block_align
    sample_count = frame_count * channel_count
    if format_tag == FORMAT_IEEE_FLOAT:
        values = struct.unpack_from(f"<{sample_count}{'f' if bits == 32 else 'd'}", sample_bytes, 0)
    elif bits == 8:
        values = [(byte - 128) / 128.0 for byte in sample_bytes[:sample_count]]
    elif bits == 16:
        values = [value / 32768.0 for value in struct.unpack_from(f"<{sample_count}h", sample_bytes, 0)]
    elif bits == 32:
        values = [value / 2147483648.0 for value in struct.unpack_from(f"<{sample_count}i", sample_bytes, 0)]
    else:
        values = [int.from_bytes(sample_bytes[3 * index:3 * index + 3], "little", signed=True) / 8388608.0
                  for index in range(sample_count)]
    channels = [list(values[channel::channel_count]) for channel in range(channel_count)]
    return channels, rate


def write_wave_file(path, channels, rate):
    """`channels` (lists of floats, equal lengths) as a 32-bit float WAV at `rate`. A NaN or infinity fails."""
    if not channels or any(len(channel) != len(channels[0]) for channel in channels):
        raise BuildError(f"{path}: channels must be non-empty and of equal length")
    frame_count = len(channels[0])
    interleaved = [channel[index] for index in range(frame_count) for channel in channels]
    if any(value != value or value in (float("inf"), float("-inf")) for value in interleaved):
        raise BuildError(f"{path}: the samples hold a NaN or infinity")
    channel_count = len(channels)
    sample_bytes = struct.pack(f"<{len(interleaved)}f", *interleaved)
    format_chunk = struct.pack("<HHIIHHH", FORMAT_IEEE_FLOAT, channel_count, int(rate), int(rate) * 4 * channel_count,
                               4 * channel_count, 32, 0)
    fact_chunk = struct.pack("<I", frame_count)
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(format_chunk)) + format_chunk
            + b"fact" + struct.pack("<I", len(fact_chunk)) + fact_chunk
            + b"data" + struct.pack("<I", len(sample_bytes)) + sample_bytes + (b"\0" if len(sample_bytes) & 1 else b""))
    try:
        with open(path, "wb") as handle:
            handle.write(b"RIFF" + struct.pack("<I", len(body)) + body)
    except OSError as problem:
        raise BuildError(f"{path}: cannot write: {problem}") from problem
