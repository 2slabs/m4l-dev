"""Reads the LTC1060 datasheet's four Q-error-vs-clock graphs (Graphs 3 and 4: mode 1; 16 and 17: mode 3) out of the
PDF's own drawing operators and fits the module's Q-enhancement law to them; writes q-error-graphs.json beside itself
(references/circuits/ltc1060-mf10.md, "Q enhancement", cites it).

    uv run --python 3.14.7 --with numpy==2.5.2 --with pymupdf==1.26.5 python \
        references/circuits/ltc1060-q-error-graphs/read_and_fit_ltc1060_q_error_graphs.py \
        references/circuits/sources/ltc1060-1060fb.pdf <monitoring repo>/tools/figures

THE READING is the figure-extractor pipeline's vector-PDF reader (the monitoring repo's
tools/figures/extract_vector_pdf_figures.py, its second argument here): the datasheet prints its graphs as vector
drawing (`pdfimages` finds no bitmap), so every number is a coordinate the PDF already holds. Its primitives are used
as they are (read_page_drawings, read_page_text, x_tick_labels_under, y_tick_labels_left_of, place_labels_on_ticks,
calibrate_axis, value_at, position_at, open_verified_pdf); what differs is the plot box, because Linear drafted these
by hand, not with MATLAB: the box is the graph's 0.6 pt frame and its ticks are the 0.35 pt grid lines (no tick stubs,
which the reader's own box finder requires), and the calibration proof's tolerance is DATASHEET_CALIBRATION_TOLERANCE_PT
(a hand-placed grid misses MATLAB's 0.05 pt; the worst residual is printed and stored per graph).

Each graph is two stacked halves, 100:1 above and 50:1 below, each 0 / 10 / 20 % on the y axis, fCLK 0.2 to 2 MHz on
x. A curve is a 1.2 pt black stroke: the shared zero baseline (kept as the curve's knee, its last vertex at 0) and
straight lines up to 20 % (the drafter's; their vertices are the data). WHICH Q a curve is, and which supply: DECLARED
below per half from the labels printed in it, left to right, assigned by rank: within a supply's group (the groups
split by their knee clocks) a higher Q reaches 5 % error at a lower clock, the order the labels are printed in. A
drawn curve count unlike the declared one is a refusal.

THE FIT: the excess loop phase of op amps that settle less and less completely within a clock period, as a damping
offset independent of Q:  q' = q - A exp(-a / f_clk)  (so Q' / Q - 1 = dq / (q - dq)). Each drawn vertex with >= 1 %
error gives dq = (1/Q) dev / (1 + dev); ln dq = ln A - a / f by least squares, per graph half and supply. Its error:
the deviation it predicts at each vertex's clock against the drawn one (%-points), the clock at which it reaches each
vertex's drawn deviation against the drawn clock (kHz), and what it predicts at the drawn knees (drawn as 0).
"""
import json
import math
import os
import sys

import numpy as np

LTC1060_SHA256 = "4114b99dbe5fef8ed1ef7520f69f27209bbbf7cae50a88ef507bd95fb960bf25"
DATASHEET_CALIBRATION_TOLERANCE_PT = 0.6
LOWEST_FITTED_DEVIATION_PERCENT = 1.0      # below this a vertex is the drawn zero (the baseline's thickness)
RANKING_DEVIATION_PERCENT = 5.0

# graph -> its PDF page (1-based), its frame's corners (to find it by, within 2 pt), the chip's mode as captioned, and
# per half (upper 100:1, lower 50:1) the supply groups left to right with the Qs their labels print, highest first
GRAPHS = {
    "3": {"page": 4, "near": (428, 151, 561, 284), "mode": "1",
          "upper": [("±2.5V", [50, 20, 10, 5]), ("±5V", [100, 50, 20, 10, 5])],
          "lower": [("±2.5V", [50, 20, 10, 5]), ("±5V", [100, 50, 20, 10, 5])]},
    "4": {"page": 4, "near": (76, 356, 208, 489), "mode": "1",
          "upper": [("±7.5V", [400, 200, 100, 50, 10, 5])], "lower": [("±7.5V", [400, 200, 100, 50, 10, 5])]},
    "16": {"page": 5, "near": (75, 574, 207, 706), "mode": "3",
           "upper": [("±2.5V", [50, 20, 10, 5]), ("±5V", [50, 20, 10, 5])],
           "lower": [("±2.5V", [50, 20, 10, 5]), ("±5V", [50, 20, 10, 5])]},
    "17": {"page": 5, "near": (255, 574, 387, 706), "mode": "3 (R2 = R4)",
           "upper": [("±7.5V", [50, 10, 5])], "lower": [("±7.5V", [50, 10, 5])]},
}
CLOCK_RATIO_OF_HALF = {"upper": 100, "lower": 50}


class GraphReadingRefused(Exception):
    pass


def frame_of(drawings, near):
    """The graph's frame: the 0.6 pt closed rectangle at `near`."""
    for path in drawings["stroked_paths"]:
        points = [point for polyline in path["polylines"] for point in polyline]
        box = (min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points))
        if 0.55 <= path["width_pt"] <= 0.65 and all(abs(found - expected) < 2 for found, expected in zip(box, near)):
            return {"left": box[0], "top": box[1], "right": box[2], "bottom": box[3]}
    raise GraphReadingRefused(f"no 0.6 pt frame near {near}")


def grid_lines(drawings, frame):
    """The 0.35 pt grid inside the frame: its columns (x) and rows (y)."""
    segments = list(drawings["straight_segments"])
    for path in drawings["stroked_paths"]:
        for polyline in path["polylines"]:
            segments += [{"start": start, "end": end, "width_pt": path["width_pt"]} for start, end in zip(polyline, polyline[1:])]
    columns, rows = set(), set()
    for segment in segments:
        if not 0.33 <= segment["width_pt"] <= 0.37:
            continue
        (x0, y0), (x1, y1) = segment["start"], segment["end"]
        if abs(x0 - x1) < 0.05 and abs(y1 - y0) > 0.9 * (frame["bottom"] - frame["top"]) and frame["left"] < x0 < frame["right"]:
            columns.add(round(x0, 3))
        if abs(y0 - y1) < 0.05 and abs(x1 - x0) > 0.9 * (frame["right"] - frame["left"]) and frame["top"] < y0 < frame["bottom"]:
            rows.add(round(y0, 3))
    return sorted(columns), sorted(rows)


def calibrate(vector_reader, axis_name, labels, ticks, label_axis):
    placed = vector_reader.place_labels_on_ticks(axis_name, labels, ticks, label_axis)
    pipeline_tolerance = vector_reader.CALIBRATION_WORST_RESIDUAL_TOLERANCE_PT
    vector_reader.CALIBRATION_WORST_RESIDUAL_TOLERANCE_PT = DATASHEET_CALIBRATION_TOLERANCE_PT
    try:
        return vector_reader.calibrate_axis(axis_name, placed, logarithmic=False)
    finally:
        vector_reader.CALIBRATION_WORST_RESIDUAL_TOLERANCE_PT = pipeline_tolerance


def clock_at_deviation(points, deviation_percent):
    deviations = [deviation for _, deviation in points]
    if deviation_percent > max(deviations):
        return None
    return float(np.interp(deviation_percent, deviations, [clock for clock, _ in points]))


def read_graph(vector_reader, document, graph_name, declaration):
    """The graph's curves: [{half, clock_ratio, supply, q, points [[fCLK MHz, deviation %]]}] and its calibration."""
    page = document[declaration["page"] - 1]
    drawings = vector_reader.read_page_drawings(page)
    labels = vector_reader.read_page_text(page)
    frame = frame_of(drawings, declaration["near"])
    columns, rows = grid_lines(drawings, frame)
    x_calibration = calibrate(vector_reader, f"graph {graph_name} x", vector_reader.x_tick_labels_under(frame, labels),
                              [frame["left"]] + columns + [frame["right"]], 0)
    y_labels = sorted(vector_reader.y_tick_labels_left_of(frame, labels), key=lambda label: label["centre"][1])
    if [label["text"] for label in y_labels] != ["20", "10", "0", "20", "10", "0"]:
        raise GraphReadingRefused(f"graph {graph_name}: y labels {[label['text'] for label in y_labels]}, "
                                  "expected two stacked halves of 20 / 10 / 0")
    y_ticks = rows + [frame["bottom"]]
    y_calibrations = {"upper": calibrate(vector_reader, f"graph {graph_name} upper y", y_labels[:3], y_ticks, 1),
                      "lower": calibrate(vector_reader, f"graph {graph_name} lower y", y_labels[3:], y_ticks, 1)}
    halves_split_at = (vector_reader.position_at(y_calibrations["upper"], 0) +
                       vector_reader.position_at(y_calibrations["lower"], 20)) / 2
    drawn = {"upper": [], "lower": []}
    for path in drawings["stroked_paths"]:
        if not 1.1 <= path["width_pt"] <= 1.3 or path["colour"] is None or max(path["colour"]) > 0.1:
            continue
        for polyline in path["polylines"]:
            xs, ys = [x for x, _ in polyline], [y for _, y in polyline]
            if not (frame["left"] - 1 <= min(xs) and max(xs) <= frame["right"] + 1 and
                    frame["top"] - 1 <= min(ys) and max(ys) <= frame["bottom"] + 1):
                continue
            half = "upper" if (min(ys) + max(ys)) / 2 < halves_split_at else "lower"
            points = sorted(zip(vector_reader.value_at(x_calibration, np.array(xs)),
                                vector_reader.value_at(y_calibrations[half], np.array(ys))))
            rising = [point for point in points if point[1] > 0.6]
            if not rising:
                continue      # a stretch of baseline alone
            knee = max([point for point in points if point[1] <= 0.6], default=None)
            drawn[half].append([[round(float(clock), 4), round(float(deviation), 3)]
                                for clock, deviation in ([knee] if knee else []) + rising])
    curves = []
    for half in ("upper", "lower"):
        groups = declaration[half]
        declared_count = sum(len(qs) for _, qs in groups)
        if len(drawn[half]) != declared_count:
            raise GraphReadingRefused(f"graph {graph_name} {half}: {len(drawn[half])} curves drawn, {declared_count} "
                                      "declared from its labels")
        by_knee = sorted(drawn[half], key=lambda points: points[0][0])
        start = 0
        for supply, qs in groups:
            group = by_knee[start:start + len(qs)]
            start += len(qs)
            if start < len(by_knee) and by_knee[start][0][0] < max(points[0][0] for points in group):
                raise GraphReadingRefused(f"graph {graph_name} {half}: the supply groups overlap in knee clock")
            unranked = [points for points in group if clock_at_deviation(points, RANKING_DEVIATION_PERCENT) is None]
            if unranked:
                raise GraphReadingRefused(f"graph {graph_name} {half} {supply}: a curve never reaches "
                                          f"{RANKING_DEVIATION_PERCENT} %, it cannot be ranked: {unranked}")
            for q, points in zip(qs, sorted(group, key=lambda points: clock_at_deviation(points, RANKING_DEVIATION_PERCENT))):
                curves.append({"half": half, "clock_ratio": CLOCK_RATIO_OF_HALF[half], "supply": supply, "q": q,
                               "points_fclk_mhz_deviation_percent": points})
    return curves, {"x_worst_residual_pt": x_calibration["worst_residual_pt"],
                    "y_worst_residual_pt": max(c["worst_residual_pt"] for c in y_calibrations.values())}


def fit_family(curves):
    """q' = q - A exp(-a / f): A, a (Hz) and the fit's error over the family's drawn vertices."""
    inverse_clocks, log_offsets = [], []
    for curve in curves:
        for clock, deviation in curve["points_fclk_mhz_deviation_percent"]:
            if deviation >= LOWEST_FITTED_DEVIATION_PERCENT:
                inverse_clocks.append(1 / clock)
                log_offsets.append(math.log((1 / curve["q"]) * (deviation / 100) / (1 + deviation / 100)))
    slope, intercept = np.polyfit(inverse_clocks, log_offsets, 1)
    amplitude, settling_mhz = math.exp(intercept), -slope
    deviation_errors, clock_errors_khz, knee_deviations = [], [], []
    for curve in curves:
        damping = 1 / curve["q"]
        for clock, deviation in curve["points_fclk_mhz_deviation_percent"]:
            offset = amplitude * math.exp(-settling_mhz / clock)
            predicted = 100 * offset / (damping - offset) if offset < damping else math.inf
            if deviation >= LOWEST_FITTED_DEVIATION_PERCENT:
                deviation_errors.append(predicted - deviation)
                drawn_offset = damping * (deviation / 100) / (1 + deviation / 100)
                clock_errors_khz.append(1000 * (settling_mhz / math.log(amplitude / drawn_offset) - clock))
            else:
                knee_deviations.append(predicted)
    highest_clock = max(clock for curve in curves for clock, _ in curve["points_fclk_mhz_deviation_percent"])
    return {"amplitude": amplitude, "settling_clock_hz": settling_mhz * 1e6, "fitted_vertices": len(deviation_errors),
            "highest_drawn_clock_hz": highest_clock * 1e6,
            "rms_deviation_error_percent_points": float(np.sqrt(np.mean(np.square(deviation_errors)))),
            "worst_deviation_error_percent_points": float(max(deviation_errors, key=abs)),
            "rms_clock_error_khz": float(np.sqrt(np.mean(np.square(clock_errors_khz)))),
            "worst_clock_error_khz": float(max(clock_errors_khz, key=abs)),
            "worst_deviation_at_drawn_knees_percent": float(max(knee_deviations))}


def main(pdf_path, figures_tools_directory):
    if not os.path.isfile(os.path.join(figures_tools_directory, "extract_vector_pdf_figures.py")):
        raise GraphReadingRefused(f"{figures_tools_directory} holds no extract_vector_pdf_figures.py: give the "
                                  "monitoring repo's tools/figures")
    sys.path.insert(0, figures_tools_directory)
    import extract_vector_pdf_figures as vector_reader
    document = vector_reader.open_verified_pdf(pdf_path, LTC1060_SHA256)
    graphs = []
    for graph_name, declaration in GRAPHS.items():
        curves, calibration = read_graph(vector_reader, document, graph_name, declaration)
        families = {}
        for curve in curves:
            families.setdefault((curve["clock_ratio"], curve["supply"]), []).append(curve)
        fits = [dict({"clock_ratio": ratio, "supply": supply}, **fit_family(family_curves))
                for (ratio, supply), family_curves in families.items()]
        graphs.append({"graph": graph_name, "pdf_page": declaration["page"], "mode": declaration["mode"],
                       "calibration": calibration, "fits": fits, "curves": curves})
    output = {"source": "LTC1060 datasheet rev. 1060fb, sha256 " + LTC1060_SHA256,
              "reader": "the monitoring repo's tools/figures/extract_vector_pdf_figures.py primitives, "
                        f"calibration tolerance {DATASHEET_CALIBRATION_TOLERANCE_PT} pt",
              "law": "q' = q - amplitude * exp(-settling_clock_hz / f_clk)", "graphs": graphs}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "q-error-graphs.json"), "w") as handle:
        json.dump(output, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print("graph mode          ratio  supply  amplitude  settling (MHz)  n  dev err rms / worst (%-pts)  "
          "clock err rms / worst (kHz)  at drawn knees (worst %)  drawn to (MHz)  calibration worst x / y (pt)")
    for graph in graphs:
        for fit in graph["fits"]:
            print(f"{graph['graph']:>5} {graph['mode']:<12} {fit['clock_ratio']:>3}:1  {fit['supply']:6} "
                  f"{fit['amplitude']:9.3f}  {fit['settling_clock_hz'] / 1e6:13.3f}  {fit['fitted_vertices']:2d}  "
                  f"{fit['rms_deviation_error_percent_points']:5.2f} / {fit['worst_deviation_error_percent_points']:+6.2f}"
                  f"               {fit['rms_clock_error_khz']:5.1f} / {fit['worst_clock_error_khz']:+6.1f}"
                  f"              {fit['worst_deviation_at_drawn_knees_percent']:5.2f}"
                  f"                  {fit['highest_drawn_clock_hz'] / 1e6:5.3f}"
                  f"           {graph['calibration']['x_worst_residual_pt']} / {graph['calibration']['y_worst_residual_pt']}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
