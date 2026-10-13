"""Deterministic, locale-aware interpretation of calculated pattern metrics."""

RAY_KIND_LABELS = {
    "pt-BR": {
        "direct": "diretas", "reflected": "refletidas", "diffracted": "difratadas",
        "reflected_diffracted": "com reflexão e difração", "double_diffracted": "com dupla difração",
        "reflected_double_diffracted": "com reflexão e dupla difração",
    },
    "en": {
        "direct": "direct", "reflected": "reflected", "diffracted": "diffracted",
        "reflected_diffracted": "with reflection and diffraction", "double_diffracted": "with double diffraction",
        "reflected_double_diffracted": "with reflection and double diffraction",
    },
    "es": {
        "direct": "directas", "reflected": "reflejadas", "diffracted": "difractadas",
        "reflected_diffracted": "con reflexión y difracción", "double_diffracted": "con doble difracción",
        "reflected_double_diffracted": "con reflexión y doble difracción",
    },
}

TEXT = {
    "pt-BR": {
        "ray_unavailable": "O traçado geométrico de raios não está disponível para esta análise.",
        "no_valid_paths": "nenhuma trajetória válida",
        "ray_count_observation": "O núcleo calculou {count_text}; a quantidade de linhas não representa, sozinha, a intensidade recebida.",
        "ray_angle_range": "Trajetórias {label}: ângulos de saída entre {min:.2f}° e {max:.2f}°.",
        "ray_contacts": "Foram identificadas {n} trajetórias com contato próximo ao terreno, dentro da tolerância de 4 m.",
        "ray_steep": "{n} trajetórias saem acima de 10°; elas devem ser comparadas com o objetivo do enlace e não tratadas automaticamente como sinais úteis de longa distância.",
        "ray_beginner": "O traçado mostra {total} trajetórias geométricas válidas: {count_text}. Ele ajuda a localizar caminhos diretos, reflexões e difrações sobre o relevo, mas não substitui o ganho do padrão nem mede sozinho a potência recebida.",
        "ray_technical": "Os ângulos informados são ângulos de saída armazenados pelo núcleo; caminhos geométricos podem ter pesos diferentes no padrão final por ganho de antena, fase, reflexão e difração.",
        "width_undetermined": "não determinada no intervalo analisado",
        "pattern_beginner": "O maior ganho é de {peak:.2f} dB em {angle:.2f}°. A largura aproximada do feixe em -3 dB é {width}. O ganho médio integrado no intervalo é {average:.2f} dB.",
        "pattern_technical": "Máximo global: {peak:.6f} dB @ {angle:.2f}°; mínimo amostrado: {null_value:.2f} dB @ {null_angle:.2f}°; limiar de meia potência: {threshold:.2f} dB.",
        "elevation_low": "O pico está em uma faixa de elevação baixa, normalmente associada a enlaces de maior alcance.",
        "elevation_mid": "O pico está em uma faixa de elevação intermediária.",
        "elevation_high": "O pico está em uma faixa de elevação alta; compare com o objetivo operacional do enlace.",
        "nulls_found": "Foram identificados {n} nulos locais entre os cinco principais valores reportados.",
        "pattern_headline": "Pico de {peak:.2f} dB em {angle:.2f}°",
        "no_scenarios_headline": "Comparação sem cenários",
        "no_scenarios_beginner": "Não há cenários suficientes para interpretar.",
        "scenario_summary": "{name} atinge pico de {peak:.2f} dB em {angle:.2f}° e média integrada de {average:.2f} dB",
        "comparison_beginner": "{scenario_text}. {best_name} tem o maior pico ({best_peak:.2f} dB). A diferença média da primeira comparação é de {rmse:.2f} dB.",
        "comparison_technical": "Foram analisados {n_scenarios} cenários e {n_pairwise} comparações par-a-par; RMSE da primeira comparação: {rmse:.4f} dB; maior diferença ponto a ponto nessa comparação: {max_delta:.4f} dB.",
        "scenario_peak_observation": "{name}: pico de {peak:.2f} dB em {angle:.2f}°.",
        "best_scenario_caution": "O melhor cenário não deve ser escolhido apenas pelo maior pico: compare também o ângulo do pico, a faixa de elevação desejada, os nulos e o terreno.",
        "comparison_beginner_suffix": " A comparação também considera o tipo e a distribuição geométrica dos trajetos de cada cenário; isso não transforma contagem de linhas em potência recebida.",
        "comparison_headline": "Comparação: {names}",
    },
    "en": {
        "ray_unavailable": "The geometric ray trace is not available for this analysis.",
        "no_valid_paths": "no valid paths",
        "ray_count_observation": "The core calculated {count_text}; the number of lines alone does not represent received signal strength.",
        "ray_angle_range": "{label} paths: departure angles between {min:.2f}° and {max:.2f}°.",
        "ray_contacts": "{n} paths were found with close contact to the terrain, within a 4 m tolerance.",
        "ray_steep": "{n} paths leave above 10°; they should be compared against the link's goal and not automatically treated as useful long-distance signals.",
        "ray_beginner": "The trace shows {total} valid geometric paths: {count_text}. It helps locate direct paths, reflections, and diffractions over the terrain, but it does not replace the pattern gain and does not by itself measure received power.",
        "ray_technical": "The reported angles are departure angles stored by the core; geometric paths can carry different weights in the final pattern due to antenna gain, phase, reflection, and diffraction.",
        "width_undetermined": "not determined within the analyzed range",
        "pattern_beginner": "The highest gain is {peak:.2f} dB at {angle:.2f}°. The approximate -3 dB beamwidth is {width}. The integrated average gain over the range is {average:.2f} dB.",
        "pattern_technical": "Global maximum: {peak:.6f} dB @ {angle:.2f}°; sampled minimum: {null_value:.2f} dB @ {null_angle:.2f}°; half-power threshold: {threshold:.2f} dB.",
        "elevation_low": "The peak is at a low elevation range, usually associated with longer-distance links.",
        "elevation_mid": "The peak is at an intermediate elevation range.",
        "elevation_high": "The peak is at a high elevation range; compare it against the link's operational goal.",
        "nulls_found": "{n} local nulls were found among the top five reported values.",
        "pattern_headline": "Peak of {peak:.2f} dB at {angle:.2f}°",
        "no_scenarios_headline": "Comparison with no scenarios",
        "no_scenarios_beginner": "There are not enough scenarios to interpret.",
        "scenario_summary": "{name} reaches a peak of {peak:.2f} dB at {angle:.2f}° and an integrated average of {average:.2f} dB",
        "comparison_beginner": "{scenario_text}. {best_name} has the highest peak ({best_peak:.2f} dB). The average difference from the first comparison is {rmse:.2f} dB.",
        "comparison_technical": "{n_scenarios} scenarios and {n_pairwise} pairwise comparisons were analyzed; RMSE of the first comparison: {rmse:.4f} dB; largest point-to-point difference in that comparison: {max_delta:.4f} dB.",
        "scenario_peak_observation": "{name}: peak of {peak:.2f} dB at {angle:.2f}°.",
        "best_scenario_caution": "The best scenario should not be chosen by peak gain alone: also compare the peak angle, the desired elevation range, the nulls, and the terrain.",
        "comparison_beginner_suffix": " The comparison also considers the type and geometric distribution of each scenario's paths; this does not turn line counts into received power.",
        "comparison_headline": "Comparison: {names}",
    },
    "es": {
        "ray_unavailable": "El trazado geométrico de rayos no está disponible para este análisis.",
        "no_valid_paths": "ninguna trayectoria válida",
        "ray_count_observation": "El núcleo calculó {count_text}; la cantidad de líneas por sí sola no representa la intensidad recibida.",
        "ray_angle_range": "Trayectorias {label}: ángulos de salida entre {min:.2f}° y {max:.2f}°.",
        "ray_contacts": "Se identificaron {n} trayectorias con contacto cercano al terreno, dentro de una tolerancia de 4 m.",
        "ray_steep": "{n} trayectorias salen por encima de 10°; deben compararse con el objetivo del enlace y no tratarse automáticamente como señales útiles de larga distancia.",
        "ray_beginner": "El trazado muestra {total} trayectorias geométricas válidas: {count_text}. Ayuda a localizar caminos directos, reflexiones y difracciones sobre el relieve, pero no sustituye la ganancia del patrón ni mide por sí sola la potencia recibida.",
        "ray_technical": "Los ángulos informados son ángulos de salida almacenados por el núcleo; las trayectorias geométricas pueden tener pesos diferentes en el patrón final según la ganancia de la antena, la fase, la reflexión y la difracción.",
        "width_undetermined": "no determinada en el intervalo analizado",
        "pattern_beginner": "La mayor ganancia es de {peak:.2f} dB en {angle:.2f}°. El ancho de haz aproximado en -3 dB es {width}. La ganancia media integrada en el intervalo es {average:.2f} dB.",
        "pattern_technical": "Máximo global: {peak:.6f} dB @ {angle:.2f}°; mínimo muestreado: {null_value:.2f} dB @ {null_angle:.2f}°; umbral de media potencia: {threshold:.2f} dB.",
        "elevation_low": "El pico está en un rango de elevación bajo, normalmente asociado a enlaces de mayor alcance.",
        "elevation_mid": "El pico está en un rango de elevación intermedio.",
        "elevation_high": "El pico está en un rango de elevación alto; compárelo con el objetivo operativo del enlace.",
        "nulls_found": "Se identificaron {n} nulos locales entre los cinco valores principales reportados.",
        "pattern_headline": "Pico de {peak:.2f} dB en {angle:.2f}°",
        "no_scenarios_headline": "Comparación sin escenarios",
        "no_scenarios_beginner": "No hay suficientes escenarios para interpretar.",
        "scenario_summary": "{name} alcanza un pico de {peak:.2f} dB en {angle:.2f}° y una media integrada de {average:.2f} dB",
        "comparison_beginner": "{scenario_text}. {best_name} tiene el mayor pico ({best_peak:.2f} dB). La diferencia media de la primera comparación es de {rmse:.2f} dB.",
        "comparison_technical": "Se analizaron {n_scenarios} escenarios y {n_pairwise} comparaciones por pares; RMSE de la primera comparación: {rmse:.4f} dB; mayor diferencia punto a punto en esa comparación: {max_delta:.4f} dB.",
        "scenario_peak_observation": "{name}: pico de {peak:.2f} dB en {angle:.2f}°.",
        "best_scenario_caution": "El mejor escenario no debe elegirse solo por el mayor pico: compare también el ángulo del pico, el rango de elevación deseado, los nulos y el terreno.",
        "comparison_beginner_suffix": " La comparación también considera el tipo y la distribución geométrica de las trayectorias de cada escenario; esto no convierte el conteo de líneas en potencia recibida.",
        "comparison_headline": "Comparación: {names}",
    },
}


def _text(locale: str) -> dict:
    return TEXT.get(locale, TEXT["pt-BR"])


def _ray_labels(locale: str) -> dict:
    return RAY_KIND_LABELS.get(locale, RAY_KIND_LABELS["pt-BR"])


def interpret_ray_trace(ray_trace: dict | None, profile: dict | None = None, locale: str = "pt-BR") -> dict[str, str | list[str]]:
    """Read the geometric trace without treating line count as received power."""
    text = _text(locale)
    if not ray_trace or not ray_trace.get("available"):
        return {"beginner": text["ray_unavailable"], "technical": "", "observations": []}

    paths = [path for path in ray_trace.get("paths", []) if len(path.get("distances_m", [])) >= 2]
    counts = ray_trace.get("counts", {})
    labels = _ray_labels(locale)
    total = len(paths)
    count_text = ", ".join(f"{int(counts.get(kind, 0))} {labels[kind]}" for kind in labels if counts.get(kind, 0)) or text["no_valid_paths"]
    observations = [text["ray_count_observation"].format(count_text=count_text)]

    for kind, label in labels.items():
        selected = [path for path in paths if path.get("kind") == kind]
        if not selected:
            continue
        angles = [float(path.get("angle_deg", 0.0)) for path in selected]
        observations.append(text["ray_angle_range"].format(label=label, min=min(angles), max=max(angles)))

    terrain_heights = (profile or {}).get("heights_m", [])
    terrain_distances = (profile or {}).get("distances_m", [])
    if terrain_heights and terrain_distances:
        contacts = 0
        for path in paths:
            if path.get("kind") not in ("reflected", "diffracted", "reflected_diffracted", "double_diffracted", "reflected_double_diffracted"):
                continue
            for x, y in zip(path.get("distances_m", []), path.get("heights_m", [])):
                nearest = min(range(len(terrain_distances)), key=lambda index: abs(terrain_distances[index] - x))
                if abs(y - terrain_heights[nearest]) <= 4:
                    contacts += 1
                    break
        if contacts:
            observations.append(text["ray_contacts"].format(n=contacts))

    steep = [path for path in paths if abs(float(path.get("angle_deg", 0.0))) > 10.0]
    if steep:
        observations.append(text["ray_steep"].format(n=len(steep)))
    beginner = text["ray_beginner"].format(total=total, count_text=count_text)
    technical = text["ray_technical"]
    return {"beginner": beginner, "technical": technical, "observations": observations}


def interpret_pattern(metrics: dict, ray_trace: dict | None = None, profile: dict | None = None, locale: str = "pt-BR") -> dict[str, str | list[str]]:
    text = _text(locale)
    peak = metrics["peak"]
    null = metrics["lowest_null"]
    beam = metrics["beamwidth_3db"]
    average = metrics["integrated_average_gain"]["average_db"]
    width = beam["width_deg"]
    width_text = text["width_undetermined"] if width is None else f"{width:.2f}°"
    beginner = text["pattern_beginner"].format(peak=peak["value_db"], angle=peak["angle_deg"], width=width_text, average=average)
    technical = text["pattern_technical"].format(peak=peak["value_db"], angle=peak["angle_deg"], null_value=null["value_db"], null_angle=null["angle_deg"], threshold=beam["threshold_db"])
    observations = []
    if peak["angle_deg"] <= 10:
        observations.append(text["elevation_low"])
    elif peak["angle_deg"] <= 20:
        observations.append(text["elevation_mid"])
    else:
        observations.append(text["elevation_high"])
    if len(metrics["nulls"]):
        observations.append(text["nulls_found"].format(n=len(metrics["nulls"])))
    ray_reading = interpret_ray_trace(ray_trace, profile, locale)
    beginner = f"{beginner} {ray_reading['beginner']}"
    technical = f"{technical} {ray_reading['technical']}".strip()
    observations.extend(ray_reading["observations"])
    return {"headline": text["pattern_headline"].format(peak=peak["value_db"], angle=peak["angle_deg"]), "beginner": beginner, "technical": technical, "observations": observations}


def interpret_comparison(scenarios: list[dict], comparison: dict, locale: str = "pt-BR") -> dict[str, str | list[str]]:
    """Describe every scenario in a comparison, not only the first pair."""
    text = _text(locale)
    if not scenarios:
        return {"headline": text["no_scenarios_headline"], "beginner": text["no_scenarios_beginner"], "technical": "", "observations": []}

    peaks = [(scenario["name"], scenario["metrics"]["peak"]) for scenario in scenarios]
    best_name, best_peak = max(peaks, key=lambda item: item[1]["value_db"])
    scenario_text = "; ".join(
        text["scenario_summary"].format(name=name, peak=peak["value_db"], angle=peak["angle_deg"], average=scenario["metrics"]["integrated_average_gain"]["average_db"])
        for scenario, (name, peak) in zip(scenarios, peaks)
    )
    beginner = text["comparison_beginner"].format(scenario_text=scenario_text, best_name=best_name, best_peak=best_peak["value_db"], rmse=comparison["rmse_db"])
    pairwise = comparison.get("pairwise", [])
    technical = text["comparison_technical"].format(n_scenarios=len(scenarios), n_pairwise=len(pairwise), rmse=comparison["rmse_db"], max_delta=comparison["max_absolute_delta_db"])
    observations = [
        text["scenario_peak_observation"].format(name=name, peak=peak["value_db"], angle=peak["angle_deg"])
        for name, peak in peaks
    ]
    observations.append(text["best_scenario_caution"])
    for scenario in scenarios:
        ray_reading = interpret_ray_trace(scenario.get("ray_trace"), scenario.get("profile"), locale)
        ray_observations = ray_reading.get("observations", [])
        if ray_observations:
            observations.append(f"{scenario['name']}: {ray_observations[0]}")
            observations.append(f"{scenario['name']}: {ray_observations[-1]}")
    beginner += text["comparison_beginner_suffix"]
    names = " × ".join(scenario["name"] for scenario in scenarios)
    return {"headline": text["comparison_headline"].format(names=names), "beginner": beginner, "technical": technical, "observations": observations}
