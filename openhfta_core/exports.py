import csv
import io
import json
import textwrap
import matplotlib.pyplot as plt
import numpy as np


WEB = {
    "background": "#071521",
    "panel": "#0d1e2a",
    "grid": "#263943",
    "text": "#d5e0e2",
    "muted": "#91a5ad",
    "orange": "#f2a65a",
    "green": "#6bd48b",
    "blue": "#287bb0",
    "flat": "#d93636",
    "aoa": "#d92fc4",
    "rays": {
        "direct": "#287bb0",
        "reflected": "#78b7d9",
        "diffracted": "#174f91",
        "reflected_diffracted": "#f2a65a",
        "double_diffracted": "#102f59",
        "reflected_double_diffracted": "#c58cff",
    },
}
RAY_LABELS_BY_LOCALE = {
    "pt-BR": {
        "direct": "Direto",
        "reflected": "Reflexão",
        "diffracted": "Difração",
        "reflected_diffracted": "Reflexão + difração",
        "double_diffracted": "Difração dupla",
        "reflected_double_diffracted": "Reflexão + dupla difração",
    },
    "en": {
        "direct": "Direct",
        "reflected": "Reflection",
        "diffracted": "Diffraction",
        "reflected_diffracted": "Reflection + diffraction",
        "double_diffracted": "Double diffraction",
        "reflected_double_diffracted": "Reflection + double diffraction",
    },
    "es": {
        "direct": "Directo",
        "reflected": "Reflexión",
        "diffracted": "Difracción",
        "reflected_diffracted": "Reflexión + difracción",
        "double_diffracted": "Doble difracción",
        "reflected_double_diffracted": "Reflexión + doble difracción",
    },
}
RAY_LABELS = RAY_LABELS_BY_LOCALE["pt-BR"]
TEXT_BY_LOCALE = {
    "pt-BR": {
        "report_label": "RELATÓRIO DE ANÁLISE", "horizontal": "Horizontal (H/TE)", "vertical": "Vertical (V/TM)",
        "diffraction_on": "incluída", "diffraction_off": "desativada", "heights_label": "alturas",
        "loaded_profile": "perfil carregado", "shared_default": "compartilhado/padrão",
        "elevation_stats": "Estatística de elevação (%)", "elevation": "Elevação (°)", "gain": "Ganho (dB)",
        "pattern_title": "PADRÃO DE ELEVAÇÃO", "distance_m": "Distância (m)", "altitude_m": "Altitude (m)",
        "terrain_title": "PERFIL DO TERRENO", "terrain_label": "TERRENO", "antenna_label": "Antena",
        "distance_km": "Distância (km)", "height_m": "Altura (m)", "ray_trace_title": "TRAÇADO DE RAIOS DO NÚCLEO",
        "peak_of_pattern": "PICO DO PADRÃO", "peak_angle": "ÂNGULO DO PICO", "integrated_average": "MÉDIA INTEGRADA",
        "beamwidth": "LARGURA −3 dB", "model_limits": "LIMITES DO MODELO", "not_available": "n/d",
        "profile_points": "PONTOS DO PERFIL", "scenarios_compared": "cenários comparados",
        "comparison_with_a": "Comparação com o cenário A", "max_difference": "MAIOR DIFERENÇA",
        "peak_difference": "DIFERENÇA DE PICO", "integrated_avg_diff": "DIF. MÉDIA INTEGRADA",
        "metrics_by_scenario": "MÉTRICAS POR CENÁRIO", "pairwise_comparison": "COMPARAÇÃO ENTRE CENÁRIOS",
        "automatic_reading": "LEITURA AUTOMÁTICA",
    },
    "en": {
        "report_label": "ANALYSIS REPORT", "horizontal": "Horizontal (H/TE)", "vertical": "Vertical (V/TM)",
        "diffraction_on": "included", "diffraction_off": "disabled", "heights_label": "heights",
        "loaded_profile": "loaded profile", "shared_default": "shared/default",
        "elevation_stats": "Elevation statistics (%)", "elevation": "Elevation (°)", "gain": "Gain (dB)",
        "pattern_title": "ELEVATION PATTERN", "distance_m": "Distance (m)", "altitude_m": "Altitude (m)",
        "terrain_title": "TERRAIN PROFILE", "terrain_label": "TERRAIN", "antenna_label": "Antenna",
        "distance_km": "Distance (km)", "height_m": "Height (m)", "ray_trace_title": "CORE RAY TRACE",
        "peak_of_pattern": "PATTERN PEAK", "peak_angle": "PEAK ANGLE", "integrated_average": "INTEGRATED AVERAGE",
        "beamwidth": "−3 dB BEAMWIDTH", "model_limits": "MODEL LIMITS", "not_available": "n/a",
        "profile_points": "PROFILE POINTS", "scenarios_compared": "scenarios compared",
        "comparison_with_a": "Comparison with scenario A", "max_difference": "MAXIMUM DIFFERENCE",
        "peak_difference": "PEAK DIFFERENCE", "integrated_avg_diff": "INTEGRATED AVG. DIFF.",
        "metrics_by_scenario": "METRICS BY SCENARIO", "pairwise_comparison": "SCENARIO COMPARISON",
        "automatic_reading": "AUTOMATIC READING",
    },
    "es": {
        "report_label": "INFORME DE ANÁLISIS", "horizontal": "Horizontal (H/TE)", "vertical": "Vertical (V/TM)",
        "diffraction_on": "incluida", "diffraction_off": "desactivada", "heights_label": "alturas",
        "loaded_profile": "perfil cargado", "shared_default": "compartido/predeterminado",
        "elevation_stats": "Estadística de elevación (%)", "elevation": "Elevación (°)", "gain": "Ganancia (dB)",
        "pattern_title": "PATRÓN DE ELEVACIÓN", "distance_m": "Distancia (m)", "altitude_m": "Altitud (m)",
        "terrain_title": "PERFIL DEL TERRENO", "terrain_label": "TERRENO", "antenna_label": "Antena",
        "distance_km": "Distancia (km)", "height_m": "Altura (m)", "ray_trace_title": "TRAZADO DE RAYOS DEL NÚCLEO",
        "peak_of_pattern": "PICO DEL PATRÓN", "peak_angle": "ÁNGULO DEL PICO", "integrated_average": "MEDIA INTEGRADA",
        "beamwidth": "ANCHO DE HAZ −3 dB", "model_limits": "LÍMITES DEL MODELO", "not_available": "n/d",
        "profile_points": "PUNTOS DEL PERFIL", "scenarios_compared": "escenarios comparados",
        "comparison_with_a": "Comparación con el escenario A", "max_difference": "DIFERENCIA MÁXIMA",
        "peak_difference": "DIFERENCIA DE PICO", "integrated_avg_diff": "DIF. MEDIA INTEGRADA",
        "metrics_by_scenario": "MÉTRICAS POR ESCENARIO", "pairwise_comparison": "COMPARACIÓN ENTRE ESCENARIOS",
        "automatic_reading": "LECTURA AUTOMÁTICA",
    },
}


def _text(locale: str) -> dict:
    return TEXT_BY_LOCALE.get(locale, TEXT_BY_LOCALE["pt-BR"])
ACCESSIBLE_RAY_COLORS = {
    "direct": "#0072b2",
    "reflected": "#56b4e9",
    "diffracted": "#d55e00",
    "reflected_diffracted": "#e69f00",
    "double_diffracted": "#cc79a7",
    "reflected_double_diffracted": "#f0e442",
}
SCENARIO_COLORS = ["#f2a65a", "#6bd48b", "#78b7d9", "#c58cff", "#ff7a8a", "#f0e06a", "#4fd1c5", "#b0bec5"]
FLAT_SCENARIO_COLORS = ["#c76b5a", "#4f9f78", "#5f8fa8", "#9a6bc0", "#b85563", "#b3a64a", "#38958c", "#7f8c91"]
SCENARIO_LINE_STYLES = ["-", (0, (6, 3)), (0, (1, 1)), (0, (5, 1, 1, 1))]
RAY_LINE_STYLES = {
    "direct": "-",
    "reflected": "--",
    "diffracted": ":",
    "reflected_diffracted": "-.",
    "double_diffracted": (0, (1, 1)),
    "reflected_double_diffracted": (0, (5, 1, 1, 1)),
}


def result_json(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def result_csv(payload: dict) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["angle_deg", "pattern_db"])
    writer.writerows(zip(payload["angles_deg"], payload["pattern_db"]))
    return output.getvalue().encode("utf-8")


def comparison_csv(payload: dict) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    angles = payload.get("angles_deg", [])
    scenarios = payload.get("scenarios", [])
    writer.writerow(["angle_deg"] + [f"{scenario.get('name') or f'scenario_{index + 1}'}_pattern_db" for index, scenario in enumerate(scenarios)])
    columns = [scenario.get("pattern_db", []) for scenario in scenarios]
    for row_index, angle in enumerate(angles):
        writer.writerow([angle] + [(column[row_index] if row_index < len(column) else "") for column in columns])
    return output.getvalue().encode("utf-8")


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _configuration_text(payload: dict, locale: str) -> str:
    text = _text(locale)
    config = payload.get("configuration", {})
    heights = config.get("antenna_heights_m") or []
    height_text = " / ".join(f"{_safe_float(height):.1f} m" for height in heights) or text["not_available"]
    polarization = text["vertical"] if config.get("polarization") == "vertical" else text["horizontal"]
    diffraction = text["diffraction_off"] if config.get("diffraction_disable") else text["diffraction_on"]
    return (
        f"{_safe_float(config.get('frequency_mhz')):.2f} MHz  ·  {polarization}  ·  "
        f"{text['heights_label']} {height_text}  ·  {diffraction}"
    )


def _sources_text(payload: dict, locale: str) -> str:
    text = _text(locale)
    sources = payload.get("sources", {})
    profile = sources.get("profile_name") or text["loaded_profile"]
    prn = sources.get("prn_name") or text["shared_default"]
    return f"PRO: {profile}  ·  PRN: {prn}"


def _style_axis(axis, *, x_label: str, y_label: str, title: str | None = None) -> None:
    axis.set_facecolor(WEB["panel"])
    axis.grid(color=WEB["grid"], alpha=.8, linewidth=.7)
    axis.tick_params(colors=WEB["muted"], labelsize=9)
    for spine in axis.spines.values():
        spine.set_color(WEB["grid"])
    axis.set_xlabel(x_label, color=WEB["muted"], fontsize=10)
    axis.set_ylabel(y_label, color=WEB["muted"], fontsize=10)
    if title:
        axis.set_title(title, loc="left", color=WEB["orange"], fontsize=12, fontweight="bold", pad=12)


def _plot_pattern(axis, payload: dict, locale: str) -> None:
    text = _text(locale)
    angles = np.asarray(payload.get("angles_deg", []), dtype=float)
    pattern = np.asarray(payload.get("pattern_db", []), dtype=float)
    if not len(angles):
        return
    axis.plot(angles, pattern, color=WEB["orange"], linewidth=2.2, label="PRO", zorder=3)
    axis.fill_between(angles, pattern, -10, color=WEB["orange"], alpha=.08)
    flat = payload.get("flat_pattern_db")
    if flat is not None:
        axis.plot(angles, flat, color=WEB["flat"], linewidth=1.7, linestyle="--", label="FLAT.PRO", zorder=2)
    aoa = payload.get("aoa") or {}
    if aoa.get("available") and aoa.get("angles_deg"):
        twin = axis.twinx()
        twin.bar(aoa["angles_deg"], aoa["probabilities_pct"], width=.72, color=WEB["aoa"], alpha=.28, label=f"PRN · {aoa.get('band') or ''}")
        twin.set_ylim(0, 20)
        twin.set_ylabel(text["elevation_stats"], color=WEB["muted"], fontsize=10)
        twin.tick_params(colors=WEB["muted"], labelsize=9)
        for spine in twin.spines.values():
            spine.set_color(WEB["grid"])
        handles, labels = axis.get_legend_handles_labels()
        twin_handles, twin_labels = twin.get_legend_handles_labels()
        axis.legend(handles + twin_handles, labels + twin_labels, loc="upper right", facecolor=WEB["panel"], edgecolor=WEB["grid"], labelcolor=WEB["text"], fontsize=9)
    else:
        axis.legend(loc="upper right", facecolor=WEB["panel"], edgecolor=WEB["grid"], labelcolor=WEB["text"], fontsize=9)
    axis.set_xlim(0, 36)
    axis.set_ylim(-10, 20)
    axis.set_xticks(range(0, 37, 5))
    _style_axis(axis, x_label=text["elevation"], y_label=text["gain"], title=text["pattern_title"])


def _plot_terrain(axis, payload: dict, locale: str) -> None:
    text = _text(locale)
    profile = payload.get("profile") or {}
    distances = np.asarray(profile.get("distances_m", []), dtype=float)
    heights = np.asarray(profile.get("heights_m", []), dtype=float)
    points = min(len(distances), len(heights), int(profile.get("points", len(distances))))
    if points:
        axis.fill_between(distances[:points], heights[:points], min(heights[:points]), color=WEB["green"], alpha=.12)
        axis.plot(distances[:points], heights[:points], color=WEB["green"], linewidth=1.8, label=text["terrain_label"])
        axis.legend(loc="upper right", facecolor=WEB["panel"], edgecolor=WEB["grid"], labelcolor=WEB["text"], fontsize=9)
    _style_axis(axis, x_label=text["distance_m"], y_label=text["altitude_m"], title=text["terrain_title"])


def _plot_rays(axis, payload: dict, locale: str) -> None:
    text = _text(locale)
    ray_labels = RAY_LABELS_BY_LOCALE.get(locale, RAY_LABELS_BY_LOCALE["pt-BR"])
    profile = payload.get("profile") or {}
    distances = np.asarray(profile.get("distances_m", []), dtype=float)
    heights = np.asarray(profile.get("heights_m", []), dtype=float)
    points = min(len(distances), len(heights), int(profile.get("points", len(distances))))
    if points:
        axis.fill_between(distances[:points] / 1000, heights[:points], min(heights[:points]), color="#c2aea2", alpha=.25)
        axis.plot(distances[:points] / 1000, heights[:points], color="#d5c2b7", linewidth=1.8, label=text["terrain_label"], zorder=4)
        antenna_height = (payload.get("configuration", {}).get("antenna_heights_m") or [0])[0]
        axis.scatter([0], [heights[0] + _safe_float(antenna_height)], color=WEB["orange"], marker="^", s=48, label=text["antenna_label"], zorder=5)
    trace = payload.get("ray_trace") or {}
    terrain_end = float(distances[points - 1]) if points else 0.0

    def terrain_at(distance: float) -> float:
        if not points:
            return 0.0
        return float(np.interp(distance, distances[:points], heights[:points]))

    def gain_at(angle: float) -> float:
        angles = np.asarray(payload.get("angles_deg", []), dtype=float)
        pattern = np.asarray(payload.get("flat_pattern_db") or payload.get("pattern_db", []), dtype=float)
        if not len(angles) or not len(pattern):
            return 0.0
        index = int(np.argmin(np.abs(angles - abs(float(angle)))))
        return float(pattern[min(index, len(pattern) - 1)])

    candidates = []
    for path in trace.get("paths", []):
        kind = path.get("kind", "other")
        raw_x = np.asarray(path.get("distances_m", []), dtype=float)
        raw_y = np.asarray(path.get("heights_m", []), dtype=float)
        count = min(len(raw_x), len(raw_y))
        if count < 2:
            continue
        raw_x, raw_y = raw_x[:count], raw_y[:count]
        frame = raw_x <= terrain_end + 0.01
        if not frame.any() or float(np.max(raw_y[frame])) > 1000:
            continue
        clipped = [(float(x), float(y)) for x, y in zip(raw_x, raw_y) if x <= terrain_end]
        crossing = np.flatnonzero(raw_x > terrain_end)
        if crossing.size and len(clipped) and crossing[0] > 0:
            index = int(crossing[0])
            x0, x1 = raw_x[index - 1], raw_x[index]
            y0, y1 = raw_y[index - 1], raw_y[index]
            ratio = 0.0 if x1 == x0 else (terrain_end - x0) / (x1 - x0)
            clipped.append((terrain_end, float(y0 + (y1 - y0) * ratio)))
        if len(clipped) < 2:
            continue
        if kind == "double_diffracted" and not any(abs(y - terrain_at(x)) < 4 for x, y in clipped):
            continue
        candidates.append({"kind": kind, "angle": float(path.get("angle_deg", 0.0)), "points": clipped})

    # Every calculated path is plotted (nothing is dropped); thin, low-alpha
    # lines keep dense bundles from turning into a solid block while the
    # gain-based weight still makes the strongest paths stand out.
    gains = [gain_at(path["angle"]) for path in candidates]
    low_gain = min(gains, default=0.0)
    high_gain = max(gains, default=1.0)
    shown = set()
    for path, gain in zip(candidates, gains):
        weight = .45 if high_gain == low_gain else .14 + .38 * ((gain - low_gain) / (high_gain - low_gain))
        label = ray_labels.get(path["kind"], path["kind"])
        x = [point[0] / 1000 for point in path["points"]]
        y = [point[1] for point in path["points"]]
        axis.plot(x, y, color=ACCESSIBLE_RAY_COLORS.get(path["kind"], WEB["blue"]), linewidth=(.75 if path["kind"] == "direct" else .55) + .4 * weight, alpha=.25 + .35 * weight, linestyle=RAY_LINE_STYLES.get(path["kind"], "-"), label=label if path["kind"] not in shown else "")
        shown.add(path["kind"])
    _style_axis(axis, x_label=text["distance_km"], y_label=text["height_m"], title=text["ray_trace_title"])
    if points:
        axis.set_xlim(0, max(0.5, distances[points - 1] / 1000))
        axis.set_ylim(max(0, min(heights[:points]) - 30), 1000)
    degrees_axis = axis.twinx()
    degrees_axis.set_ylim(0, 10)
    degrees_axis.set_yticks(range(0, 11, 1))
    degrees_axis.set_ylabel(text["elevation"], color=WEB["muted"], fontsize=10, labelpad=10)
    degrees_axis.tick_params(axis="y", colors=WEB["muted"], labelsize=9, direction="out", pad=4)
    degrees_axis.spines["right"].set_color(WEB["grid"])
    degrees_axis.spines["top"].set_visible(False)
    degrees_axis.spines["left"].set_visible(False)
    degrees_axis.spines["bottom"].set_visible(False)
    if shown or points:
        axis.legend(loc="upper center", bbox_to_anchor=(.5, -0.16), ncol=4, facecolor=WEB["panel"], edgecolor=WEB["grid"], labelcolor=WEB["text"], fontsize=9, handlelength=2.2, handletextpad=.6, columnspacing=1.2, borderpad=.6)


def _add_metrics(figure, payload: dict, locale: str, y, top_in: float) -> None:
    text = _text(locale)
    metrics = payload.get("metrics") or {}
    peak = metrics.get("peak") or {}
    beamwidth = metrics.get("beamwidth_3db") or {}
    average = metrics.get("integrated_average_gain") or {}
    values = [
        (text["peak_of_pattern"], f"{_safe_float(peak.get('value_db')):.2f} dB"),
        (text["peak_angle"], f"{_safe_float(peak.get('angle_deg')):.2f}°"),
        (text["integrated_average"], f"{_safe_float(average.get('average_db')):.2f} dB"),
        (text["beamwidth"], "—" if beamwidth.get("width_deg") is None else f"{_safe_float(beamwidth.get('width_deg')):.2f}°"),
    ]
    for index, (label, value) in enumerate(values):
        figure.text(.08 + index * .22, y(top_in), label, color=WEB["muted"], fontsize=8, family="DejaVu Sans", va="top")
        figure.text(.08 + index * .22, y(top_in + .32), value, color=WEB["orange"], fontsize=15, fontweight="bold", family="DejaVu Sans", va="top")


def result_figure(payload: dict, image_format: str, locale: str = "pt-BR") -> bytes:
    """Render the same information hierarchy shown by the web result panel.

    Like comparison_figure, the layout is computed in inches from a top-down
    cursor instead of hand-picked figure fractions: a fixed-fraction header
    previously left too little room for the config/sources/metrics text and
    it silently overlapped the pattern chart below it.
    """
    text = _text(locale)
    limitations = payload.get("limitations") or []

    width_in = 26.0
    pattern_h, terrain_h, ray_h, chart_gap, ray_gap = 5.4, 4.8, 7.2, 0.55, 1.9

    cursor = 0.5 + 0.5 + 0.34 + 0.32 + 0.30 + 0.20  # top margin, title, subtitle, config, sources, gap
    metrics_top = cursor
    cursor += 0.62 + 0.45  # metrics row, gap before charts (axis titles need headroom above the axes box)

    pattern_top = cursor
    cursor += pattern_h + chart_gap
    terrain_top = cursor
    cursor += terrain_h + chart_gap
    ray_top = cursor
    cursor += ray_h + ray_gap

    limits_top = cursor if limitations else None
    if limitations:
        cursor += 0.3
    total_h = cursor + 0.4

    figure = plt.figure(figsize=(width_in, total_h), facecolor=WEB["background"])

    def y(top_in: float) -> float:
        return 1 - top_in / total_h

    cy = 0.5
    figure.text(.08, y(cy), "OpenHFTA", color=WEB["text"], fontsize=24, fontweight="bold", va="top")
    cy += 0.5
    figure.text(.08, y(cy), f"HF TERRAIN ANALYSIS  ·  {text['report_label']}", color=WEB["orange"], fontsize=10, fontweight="bold", va="top")
    cy += 0.34
    figure.text(.08, y(cy), _configuration_text(payload, locale), color=WEB["muted"], fontsize=10, va="top")
    cy += 0.32
    figure.text(.08, y(cy), _sources_text(payload, locale), color=WEB["muted"], fontsize=9, va="top")

    _add_metrics(figure, payload, locale, y, metrics_top)
    pattern_axis = figure.add_axes([.08, y(pattern_top + pattern_h), .84, pattern_h / total_h])
    terrain_axis = figure.add_axes([.08, y(terrain_top + terrain_h), .84, terrain_h / total_h])
    ray_axis = figure.add_axes([.08, y(ray_top + ray_h), .84, ray_h / total_h])
    _plot_pattern(pattern_axis, payload, locale)
    _plot_terrain(terrain_axis, payload, locale)
    _plot_rays(ray_axis, payload, locale)
    if limits_top is not None:
        figure.text(.08, y(limits_top), f"{text['model_limits']}  ·  " + "  ·  ".join(limitations[:2]), color=WEB["muted"], fontsize=7.5, wrap=True, va="top")
    output = io.BytesIO()
    figure.savefig(output, format=image_format, dpi=170, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)
    return output.getvalue()


def comparison_figure(payload: dict, image_format: str, locale: str = "pt-BR") -> bytes:
    """Render a comparison report for two or more scenarios: overlaid pattern and
    terrain charts, one ray-trace chart per scenario, per-scenario and pairwise
    metrics, and the automatic interpretation shown on the web comparison panel.

    The figure height is computed from the actual content (scenario count,
    pairwise rows, wrapped interpretation text) so the report neither cuts off
    long content nor leaves large empty gaps for short ones.
    """
    text = _text(locale)
    scenarios = payload.get("scenarios", [])
    angles = payload.get("angles_deg", [])
    pairwise = (payload.get("comparison") or {}).get("pairwise") or []
    interpretation = payload.get("interpretation") or {}
    limitations = payload.get("limitations") or []

    def wrap(value, width=175):
        return textwrap.wrap(value or "", width=width) or [""]

    beginner_lines = wrap(interpretation.get("beginner"))
    technical_lines = wrap(interpretation.get("technical"))
    observations = interpretation.get("observations") or []

    width_in = 26.0
    pattern_h, terrain_h, chart_gap = 5.4, 4.8, 0.55
    ray_chart_h, ray_gap = 5.6, 1.9  # extra gap reserves room for _plot_rays' below-axis legend
    section_header_h, line_h, section_gap = 0.34, 0.30, 0.35

    cursor = 0.5 + 0.5 + 0.3 + 0.32 + 0.45  # top margin, title, subtitle, config line, gap (axis titles need headroom)
    pattern_top = cursor
    cursor += pattern_h + chart_gap
    terrain_top = cursor
    cursor += terrain_h + chart_gap

    ray_tops = []
    for _scenario in scenarios:
        ray_tops.append(cursor)
        cursor += ray_chart_h + ray_gap

    metrics_top = cursor
    cursor += section_header_h + line_h * max(len(scenarios), 1) + section_gap

    pairwise_top = cursor if pairwise else None
    if pairwise:
        cursor += section_header_h + line_h * len(pairwise) + section_gap

    interpretation_top = cursor if interpretation else None
    if interpretation:
        cursor += (
            section_header_h + 0.34
            + line_h * len(beginner_lines) + line_h * len(technical_lines) + line_h * len(observations)
            + section_gap
        )

    limits_top = cursor if limitations else None
    if limitations:
        cursor += 0.3
    total_h = cursor + 0.4

    figure = plt.figure(figsize=(width_in, total_h), facecolor=WEB["background"])

    def y(top_in: float) -> float:
        return 1 - top_in / total_h

    figure.text(.08, y(0.5), "OpenHFTA", color=WEB["text"], fontsize=24, fontweight="bold", va="top")
    figure.text(.08, y(1.0), f"HF TERRAIN ANALYSIS  ·  {text['report_label']}", color=WEB["orange"], fontsize=10, fontweight="bold", va="top")
    first_config = (scenarios[0].get("configuration") if scenarios else {}) or {}
    frequency_mhz = _safe_float(first_config.get("frequency_mhz"))
    figure.text(.08, y(1.3), f"{frequency_mhz:.2f} MHz  ·  {len(scenarios)} {text['scenarios_compared']}", color=WEB["muted"], fontsize=10, va="top")

    pattern_axis = figure.add_axes([.08, y(pattern_top + pattern_h), .84, pattern_h / total_h])
    for index, scenario in enumerate(scenarios):
        name = scenario.get("name") or f"#{index + 1}"
        pattern = scenario.get("pattern_db") or []
        if pattern:
            pattern_axis.plot(angles, pattern, color=SCENARIO_COLORS[index % len(SCENARIO_COLORS)], linewidth=2.2, label=f"{name} · PRO", zorder=3)
        flat = scenario.get("flat_pattern_db")
        if flat:
            pattern_axis.plot(angles, flat, color=FLAT_SCENARIO_COLORS[index % len(FLAT_SCENARIO_COLORS)], linewidth=1.5, linestyle="--", label=f"{name} · FLAT.PRO", zorder=2)
    pattern_axis.set_xlim(0, 36)
    pattern_axis.set_ylim(-10, 20)
    pattern_axis.set_xticks(range(0, 37, 5))
    pattern_axis.legend(loc="upper right", facecolor=WEB["panel"], edgecolor=WEB["grid"], labelcolor=WEB["text"], fontsize=8, ncol=2)
    _style_axis(pattern_axis, x_label=text["elevation"], y_label=text["gain"], title=text["pattern_title"])

    # Scenarios frequently share the exact same uploaded .PRO profile (only
    # antenna height/type differ), so identical terrain curves would overlap
    # pixel-for-pixel and the later scenario would visually hide the earlier
    # one. Distinct dash styles per scenario keep every curve visible even
    # when the underlying values are identical.
    terrain_axis = figure.add_axes([.08, y(terrain_top + terrain_h), .84, terrain_h / total_h])
    has_terrain = False
    for index, scenario in enumerate(scenarios):
        profile = scenario.get("profile") or {}
        distances = np.asarray(profile.get("distances_m", []), dtype=float)
        heights = np.asarray(profile.get("heights_m", []), dtype=float)
        points = min(len(distances), len(heights), int(profile.get("points", len(distances))))
        if points:
            has_terrain = True
            terrain_axis.plot(distances[:points], heights[:points], color=SCENARIO_COLORS[index % len(SCENARIO_COLORS)], linewidth=1.8, linestyle=SCENARIO_LINE_STYLES[index % len(SCENARIO_LINE_STYLES)], label=scenario.get("name") or f"#{index + 1}")
    if has_terrain:
        terrain_axis.legend(loc="upper right", facecolor=WEB["panel"], edgecolor=WEB["grid"], labelcolor=WEB["text"], fontsize=8, ncol=2)
    _style_axis(terrain_axis, x_label=text["distance_m"], y_label=text["altitude_m"], title=text["terrain_title"])

    for index, scenario in enumerate(scenarios):
        name = scenario.get("name") or f"#{index + 1}"
        ray_top = ray_tops[index]
        ray_axis = figure.add_axes([.08, y(ray_top + ray_chart_h), .84, ray_chart_h / total_h])
        _plot_rays(ray_axis, scenario, locale)
        ray_axis.set_title(f"{name} · {text['ray_trace_title']}", loc="left", color=WEB["orange"], fontsize=12, fontweight="bold", pad=12)

    figure.text(.08, y(metrics_top), text["metrics_by_scenario"], color=WEB["orange"], fontsize=11, fontweight="bold", va="top")
    for index, scenario in enumerate(scenarios):
        metrics = scenario.get("metrics") or {}
        peak = metrics.get("peak") or {}
        beamwidth = metrics.get("beamwidth_3db") or {}
        average = metrics.get("integrated_average_gain") or {}
        profile = scenario.get("profile") or {}
        points = min(len(profile.get("distances_m", [])), len(profile.get("heights_m", [])), int(profile.get("points", 0) or 0))
        fom = metrics.get("figure_of_merit_db")
        beamwidth_text = "—" if beamwidth.get("width_deg") is None else f"{_safe_float(beamwidth.get('width_deg')):.2f}°"
        fom_text = "" if fom is None else f"  ·  FIGURE OF MERIT {_safe_float(fom):.2f} dB"
        line = (
            f"{scenario.get('name') or f'#{index + 1}'}  ·  {text['peak_of_pattern']} {_safe_float(peak.get('value_db')):.2f} dB"
            f"  ·  {text['peak_angle']} {_safe_float(peak.get('angle_deg')):.2f}°"
            f"  ·  {text['integrated_average']} {_safe_float(average.get('average_db')):.2f} dB"
            f"  ·  {text['beamwidth']} {beamwidth_text}"
            f"  ·  {text['profile_points']} {points}{fom_text}"
        )
        figure.text(.08, y(metrics_top + section_header_h + index * line_h), line, color=WEB["text"], fontsize=9, family="DejaVu Sans", va="top")

    if pairwise_top is not None:
        figure.text(.08, y(pairwise_top), text["pairwise_comparison"], color=WEB["orange"], fontsize=11, fontweight="bold", va="top")
        for index, pair in enumerate(pairwise):
            line = (
                f"A × {chr(66 + index)}  ·  {text['comparison_with_a']}  ·  RMSE {_safe_float(pair.get('rmse_db')):.2f} dB"
                f"  ·  {text['max_difference']} {_safe_float(pair.get('max_absolute_delta_db')):.2f} dB"
                f"  ·  {text['peak_difference']} {_safe_float(pair.get('peak_delta_db')):.2f} dB"
                f"  ·  {text['integrated_avg_diff']} {_safe_float(pair.get('integrated_average_delta_db')):.2f} dB"
            )
            figure.text(.08, y(pairwise_top + section_header_h + index * line_h), line, color=WEB["text"], fontsize=9, family="DejaVu Sans", va="top")

    if interpretation_top is not None:
        cy = interpretation_top
        figure.text(.08, y(cy), text["automatic_reading"], color=WEB["orange"], fontsize=11, fontweight="bold", va="top")
        cy += section_header_h
        headline = interpretation.get("headline") or ""
        if headline:
            figure.text(.08, y(cy), headline, color=WEB["text"], fontsize=10, fontweight="bold", va="top")
        cy += 0.34
        for bline in beginner_lines:
            figure.text(.08, y(cy), bline, color=WEB["text"], fontsize=9, va="top")
            cy += line_h
        for tline in technical_lines:
            figure.text(.08, y(cy), tline, color=WEB["muted"], fontsize=8.5, style="italic", va="top")
            cy += line_h
        for observation in observations:
            figure.text(.09, y(cy), f"• {observation}", color=WEB["text"], fontsize=8.5, va="top")
            cy += line_h

    if limits_top is not None:
        figure.text(.08, y(limits_top), f"{text['model_limits']}  ·  " + "  ·  ".join(limitations[:2]), color=WEB["muted"], fontsize=7.5, wrap=True, va="top")

    output = io.BytesIO()
    figure.savefig(output, format=image_format, dpi=170, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)
    return output.getvalue()
