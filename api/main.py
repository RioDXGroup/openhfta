"""FastAPI adapter around the reusable OpenHFTA core.

The API intentionally contains no numerical formulas. It validates transport
input, builds an ``AnalysisConfig`` and serializes ``AnalysisResult``.
"""
from pathlib import Path
import json
import logging
import os
import re
import smtplib
import tempfile
import urllib.parse
import urllib.request
from email.message import EmailMessage
from typing import Annotated
import numpy as np

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from openhfta_core.analysis import analyze
from openhfta_core.aoa import parse_frequency, parse_prn_multiband, frequency_to_band
from openhfta_core.exceptions import OpenHFTAError
from openhfta_core.library import find_ytw_core_library
from openhfta_core.metrics import summarize_pattern, compare_patterns, compute_fom
from openhfta_core.interpretation import interpret_pattern, interpret_comparison
from openhfta_core.exports import comparison_csv, comparison_figure, result_csv, result_figure, result_json
from openhfta_core.ai import AIUnavailable, ai_status, explain_with_ai
from openhfta_core.models import AnalysisConfig
from openhfta_core.profiles import parse_height_and_phase, parse_profile
from openhfta_core.terrain import summarize_terrain

app = FastAPI(title="OpenHFTA API", version="0.1.0")
logger = logging.getLogger("openhfta.feedback")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.[0-9]+\.[0-9]+)(:[0-9]+)?$",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

ANTENNA_TYPES = {
    "Dipole": 1, "2-Ele": 2, "3-Ele": 3, "4-Ele": 4,
    "5-Ele": 5, "6-Ele": 6, "8-Ele": 7,
}
POLARIZATIONS = {"horizontal": 0}
# The portal does not cap the scenario count; this only bounds the work a
# single request can demand from the public server (two analyses per scenario).
MAX_SCENARIOS = 50

class AIExplanationRequest(BaseModel):
    analysis: dict
MAX_PROFILE_BYTES = 5 * 1024 * 1024
DEFAULT_PRN_DIR = Path(__file__).resolve().parent.parent / "prns"
MAX_FEEDBACK_MESSAGE = 4000


@app.get("/health")
def health() -> dict:
    """Return process health without executing a numerical analysis."""
    library = find_ytw_core_library()
    return {
        "status": "ok",
        "service": "openhfta-api",
        "core_library": str(Path(library).name) if library else None,
        "core_available": library is not None,
    }


@app.get("/api/prns")
def available_prns() -> dict:
    """List bundled PRN files that can be selected by the web client."""
    # PT9-FT8-OBS holds too few observations to serve as a reference statistic.
    excluded = {"EXEMPLO-20.PRN", "EXEMPLO-20M.PRN", "PT9-FT8-OBS.PRN"}
    files = sorted(
        path.name
        for path in DEFAULT_PRN_DIR.glob("*.PRN")
        # "-smoke" files are generator smoke-test outputs, not reference statistics.
        if path.name.upper() not in excluded and not path.stem.lower().endswith("-smoke")
    ) if DEFAULT_PRN_DIR.is_dir() else []
    return {"files": files}


@app.get("/api/ai/status")
def ai_configuration_status() -> dict:
    return ai_status()


@app.post("/api/ai/explain")
def ai_explain(request: AIExplanationRequest) -> dict:
    try:
        return explain_with_ai(request.analysis)
    except AIUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _send_feedback_email(name: str, sender_email: str, category: str, message: str) -> None:
    host = os.getenv("FEEDBACK_SMTP_HOST", "").strip()
    recipient = os.getenv("FEEDBACK_TO_EMAIL", "").strip()
    copies = [item.strip() for item in os.getenv("FEEDBACK_CC_EMAIL", "").split(",") if item.strip()]
    username = os.getenv("FEEDBACK_SMTP_USER", "").strip()
    password = os.getenv("FEEDBACK_SMTP_PASSWORD", "")
    if not host or not recipient:
        raise RuntimeError("feedback email is not configured")
    port = int(os.getenv("FEEDBACK_SMTP_PORT", "587"))
    sender = os.getenv("FEEDBACK_FROM_EMAIL", "").strip() or username or recipient
    subject = f"[OpenHFTA] {category}"
    body = (
        "Nova mensagem enviada pelo formulário de colaboração do OpenHFTA.\n\n"
        f"Nome: {name or 'Não informado'}\n"
        f"E-mail: {sender_email}\n"
        f"Categoria: {category}\n\n"
        f"Mensagem:\n{message}\n"
    )
    email = EmailMessage()
    email["From"] = sender
    email["To"] = recipient
    if copies:
        email["Cc"] = ", ".join(copies)
    email["Reply-To"] = sender_email
    email["Subject"] = subject
    email.set_content(body)
    timeout = float(os.getenv("FEEDBACK_SMTP_TIMEOUT", "15"))
    if _env_bool("FEEDBACK_SMTP_SSL"):
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as client:
            if username:
                client.login(username, password)
            client.send_message(email, to_addrs=[recipient, *copies])
        return
    with smtplib.SMTP(host, port, timeout=timeout) as client:
        client.ehlo()
        if _env_bool("FEEDBACK_SMTP_STARTTLS", True):
            client.starttls()
            client.ehlo()
        if username:
            client.login(username, password)
        client.send_message(email, to_addrs=[recipient, *copies])


def _verify_turnstile(token: str | None, remote_ip: str | None) -> bool:
    secret = os.getenv("TURNSTILE_SECRET", "").strip()
    if not secret or not token:
        return False
    form = {"secret": secret, "response": token, "remoteip": remote_ip or ""}
    request = urllib.request.Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=urllib.parse.urlencode(form).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result.get("success") is True
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("turnstile validation failed: %s", exc)
        return False


@app.post("/api/feedback")
async def feedback_endpoint(
    request: Request,
    message: Annotated[str, Form()],
    email: Annotated[str, Form()],
    name: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "Sugestão",
    turnstile_token: Annotated[str | None, Form(alias="cf-turnstile-response")] = None,
    website: Annotated[str, Form()] = "",
) -> dict:
    """Send a user suggestion to the address configured by the operator."""
    if not _verify_turnstile(turnstile_token, request.client.host if request.client else None):
        raise HTTPException(422, "Confirme a verificação anti-robô e tente novamente.")
    if website.strip():
        return {"status": "sent", "message": "Obrigado pela colaboração! Sua mensagem foi enviada."}
    clean_name = " ".join(name.split())[:120]
    clean_email = email.strip()
    clean_category = " ".join(category.split())[:80] or "Sugestão"
    clean_message = message.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", clean_email):
        raise HTTPException(422, "Informe um e-mail válido para podermos responder.")
    if not clean_message:
        raise HTTPException(422, "Escreva uma mensagem antes de enviar.")
    if len(clean_message) > MAX_FEEDBACK_MESSAGE:
        raise HTTPException(422, f"A mensagem deve ter no máximo {MAX_FEEDBACK_MESSAGE} caracteres.")
    try:
        await run_in_threadpool(_send_feedback_email, clean_name, clean_email, clean_category, clean_message)
    except (OSError, smtplib.SMTPException, ValueError, RuntimeError) as exc:
        logger.warning("feedback email could not be sent: %s", exc)
        raise HTTPException(503, "No momento não foi possível enviar a mensagem. Tente novamente mais tarde.") from exc
    return {"status": "sent", "message": "Obrigado pela colaboração! Sua mensagem foi enviada."}


def _parse_heights(value: str, units: str) -> tuple[tuple[float, ...], tuple[int, ...]]:
    raw = [part for part in value.replace(",", " ").split() if part]
    if not raw:
        raise ValueError("heights must contain at least one value")
    if len(raw) > 4:
        raise ValueError("the core supports at most four antenna elements")
    parsed = [parse_height_and_phase(item, units) for item in raw]
    return tuple(height for height, _ in parsed), tuple(phase for _, phase in parsed)


def _validate_polarization(value: str) -> str:
    if value not in POLARIZATIONS:
        raise ValueError("polarization must be 'horizontal'")
    return value


def _serialize_result(result, locale: str = "pt-BR") -> dict:
    effective_points = min(
        int(result.metadata.get("profile_points", len(result.profile.distances_ft))),
        len(result.profile.distances_ft),
        len(result.profile.heights_ft),
    )
    distances_ft = result.profile.distances_ft[:effective_points]
    heights_ft = result.profile.heights_ft[:effective_points]
    distances_m = (distances_ft / 3.28084).tolist()
    heights_m = (heights_ft / 3.28084).tolist()
    trace_paths = []
    trace_counts: dict[str, int] = {}
    profile_end_ft = float(distances_ft[-1]) if len(distances_ft) else 0.0
    for path in result.trace_paths:
        kind = str(path.get("kind", "other"))
        raw_distances_ft = [float(value) for value in path.get("distances_ft", [])]
        raw_heights_ft = [float(value) for value in path.get("heights_ft", [])]
        points = min(len(raw_distances_ft), len(raw_heights_ft))
        if points < 2:
            continue
        distances_path_ft = raw_distances_ft[:points]
        heights_path_ft = raw_heights_ft[:points]
        # The legacy Fortran workspace can retain an extra endpoint beyond
        # the effective profile. A ray plot must never render that stale tail.
        clipped = [(x, y) for x, y in zip(distances_path_ft, heights_path_ft) if x <= profile_end_ft + 0.01]
        if len(clipped) < 2:
            continue
        distances_path_ft = [x for x, _ in clipped]
        heights_path_ft = [y for _, y in clipped]
        trace_counts[kind] = trace_counts.get(kind, 0) + 1
        trace_paths.append({
            "kind": kind,
            "angle_deg": float(path.get("angle_deg", 0.0)),
            "distances_m": [value / 3.28084 for value in distances_path_ft],
            "heights_m": [value / 3.28084 for value in heights_path_ft],
        })
    full_trace = {
        "available": bool(trace_paths),
        "paths": trace_paths,
        "counts": trace_counts,
    }
    client_trace = {
        "available": bool(trace_paths),
        "paths": trace_paths,
        "counts": trace_counts,
        "truncated": False,
    }
    metrics = summarize_pattern(result.angles_deg, result.pattern_db)
    return {
        "angles_deg": result.angles_deg.tolist(),
        "pattern_db": result.pattern_db.tolist(),
        "profile": {
            "source_units": result.profile.source_units,
            "points": effective_points,
            "distances_m": distances_m,
            "heights_m": heights_m,
            "distances_ft": distances_ft.tolist(),
            "heights_ft": heights_ft.tolist(),
            "terrain": summarize_terrain(distances_ft, heights_ft, result.config.antenna_heights_ft[0]),
        },
        "configuration": {
            "frequency_mhz": result.config.frequency_mhz,
            "antenna_heights_ft": list(result.config.antenna_heights_ft),
            "antenna_heights_m": [height / 3.28084 for height in result.config.antenna_heights_ft],
            "antenna_phases": list(result.config.antenna_phases),
            "soil_epsr": result.config.soil_epsr,
            "soil_sigma": result.config.soil_sigma,
            "diffraction_disable": result.config.diffraction_disable,
            "move_tower_ft": result.config.move_tower_ft,
            "move_tower_m": result.config.move_tower_ft / 3.28084,
            "antenna_pattern_type": result.config.antenna_pattern_type,
            "polarization": result.config.polarization,
        },
        "warnings": result.warnings,
        "metadata": result.metadata,
        "ray_trace": client_trace,
        "limitations": _model_limitations(result.config.polarization, locale),
        "metrics": metrics,
        "interpretation": interpret_pattern(metrics, full_trace, {"distances_m": distances_m, "heights_m": heights_m}, locale),
    }


_MODEL_LIMITATIONS_TEXT = {
    "pt-BR": [
        "O modelo representa um perfil bidimensional por azimute; não é uma simulação 3D completa.",
        "O núcleo trabalha com polarização {polarization} e modelos simplificados de antena.",
        "O modelo de empilhamento não calcula acoplamento mútuo entre elementos muito próximos.",
        "A análise é uma estimativa de padrão de elevação, não uma garantia de enlace ou de intensidade recebida.",
        "A precisão depende da qualidade do DEM/perfil e pode apresentar artefatos em passos de 0,25°.",
    ],
    "en": [
        "The model represents a two-dimensional profile per azimuth; it is not a full 3D simulation.",
        "The core works with {polarization} polarization and simplified antenna models.",
        "The stacking model does not compute mutual coupling between elements that are very close together.",
        "The analysis is an elevation-pattern estimate, not a guarantee of link performance or received signal strength.",
        "Accuracy depends on the quality of the DEM/profile and may show artifacts at 0.25° steps.",
    ],
    "es": [
        "El modelo representa un perfil bidimensional por azimut; no es una simulación 3D completa.",
        "El núcleo trabaja con polarización {polarization} y modelos simplificados de antena.",
        "El modelo de apilamiento no calcula el acoplamiento mutuo entre elementos muy próximos.",
        "El análisis es una estimación del patrón de elevación, no una garantía de enlace ni de intensidad recibida.",
        "La precisión depende de la calidad del DEM/perfil y puede presentar artefactos en pasos de 0,25°.",
    ],
}


def _model_limitations(polarization: str = "horizontal", locale: str = "pt-BR") -> list[str]:
    lines = _MODEL_LIMITATIONS_TEXT.get(locale, _MODEL_LIMITATIONS_TEXT["pt-BR"])
    return [line.format(polarization=polarization) if "{polarization}" in line else line for line in lines]


def _flat_profile_content(content: bytes, units: str) -> bytes:
    """Create a flat reference profile with the same distances as the input."""
    with tempfile.NamedTemporaryFile(suffix=".PRO", mode="wb") as temporary:
        temporary.write(content)
        temporary.flush()
        distances_ft, heights_ft = parse_profile(temporary.name)
    factor = 3.28084 if units == "meters" else 1.0
    lines = [units]
    base_height = float(heights_ft[0]) / factor
    lines.extend(f"{float(distance) / factor:.6f} {base_height:.6f}" for distance in distances_ft)
    return ("\n".join(lines) + "\n").encode()


def _default_aoa_for_band(band: str | None, filename: str | None = None) -> tuple[dict[int, float] | None, str | None]:
    """Load a selected bundled PRN containing the requested band."""
    if not band or not filename or not DEFAULT_PRN_DIR.is_dir():
        return None, None
    path = DEFAULT_PRN_DIR / Path(filename).name
    if path.suffix.lower() != ".prn" or not path.is_file():
        return None, None
    try:
        data = parse_prn_multiband(path.read_text(encoding="utf-8", errors="replace"), band)
    except OSError:
        return None, None
    if data:
        return data, path.name
    return None, None


def _parse_aoa_content(content: bytes | None, filename: str | None, band: str | None) -> tuple[dict[int, float] | None, str | None]:
    """Parse an uploaded PRN, preserving its filename as the result source."""
    if not content or not filename:
        return None, None
    data = parse_prn_multiband(content.decode("utf-8", errors="replace"), band)
    return data, filename


def _scenario_aoa(
    config: dict,
    band: str | None,
    uploaded_prns: list[tuple[str, bytes]],
    shared_aoa: tuple[dict[int, float] | None, str | None],
) -> tuple[dict[int, float] | None, str | None]:
    """Resolve one scenario's PRN, falling back to the shared PRN."""
    upload_index = config.get("prn_upload_index")
    if upload_index is not None:
        if not isinstance(upload_index, int) or not 0 <= upload_index < len(uploaded_prns):
            raise ValueError("prn_upload_index does not reference an uploaded .PRN")
        filename, content = uploaded_prns[upload_index]
        return _parse_aoa_content(content, filename, band)
    if config.get("prn_default"):
        return _default_aoa_for_band(band, str(config["prn_default"]))
    return shared_aoa


def _attach_plot_data(payload: dict, flat_result=None, aoa_data: dict[int, float] | None = None,
                      aoa_band: str | None = None, aoa_source: str | None = None) -> dict:
    if flat_result is not None:
        payload["flat_pattern_db"] = flat_result.pattern_db.tolist()
    if aoa_data is not None:
        sorted_angles = sorted(aoa_data)
        payload["aoa"] = {
            "band": aoa_band,
            "source": aoa_source,
            "angles_deg": sorted_angles,
            "probabilities_pct": [aoa_data[angle] * 100.0 for angle in sorted_angles],
            "available": bool(aoa_data),
            "message": None if aoa_data else f"A banda {aoa_band or 'correspondente'} não foi encontrada ou não possui estatística no arquivo .PRN",
        }
        if aoa_data:
            payload["metrics"]["figure_of_merit_db"] = compute_fom(np.asarray(payload["pattern_db"], dtype=float), aoa_data)
    return payload


def _run_uploaded_analysis(content: bytes, frequency: str, units: str, heights: str,
                           antenna_type: str, soil_epsr: float, soil_sigma: float,
                           no_diffraction: bool, move_tower: float, polarization: str = "horizontal"):
    if units not in ("meters", "feet"):
        raise ValueError("units must be 'meters' or 'feet'")
    if antenna_type not in ANTENNA_TYPES:
        raise ValueError(f"invalid antenna_type: {antenna_type}")
    polarization = _validate_polarization(polarization)
    frequency_mhz = parse_frequency(frequency)
    antenna_heights, antenna_phases = _parse_heights(heights, units)
    move_tower_ft = move_tower * (3.28084 if units == "meters" else 1.0)
    with tempfile.NamedTemporaryFile(suffix=".PRO", mode="wb") as temporary:
        temporary.write(content)
        temporary.flush()
        parse_profile(temporary.name)
        return analyze(AnalysisConfig(
            profile_path=temporary.name, frequency_mhz=frequency_mhz,
            antenna_heights_ft=antenna_heights, antenna_phases=antenna_phases,
            soil_epsr=soil_epsr, soil_sigma=soil_sigma,
            diffraction_disable=no_diffraction, move_tower_ft=move_tower_ft,
            antenna_pattern_type=ANTENNA_TYPES[antenna_type],
            polarization=polarization,
        ))


@app.post("/api/analyze")
async def analyze_endpoint(
    profile: Annotated[UploadFile, File(description="Terrain profile in .PRO format")],
    frequency: Annotated[str, Form()],
    aoa_file: Annotated[UploadFile | None, File(description="Optional angle-of-arrival statistics .PRN")]=None,
    aoa_default: Annotated[str | None, Form()] = None,
    units: Annotated[str, Form()] = "meters",
    polarization: Annotated[str, Form()] = "horizontal",
    heights: Annotated[str, Form()] = "10",
    antenna_type: Annotated[str, Form()] = "Dipole",
    soil_epsr: Annotated[float, Form()] = 13.0,
    soil_sigma: Annotated[float, Form()] = 0.005,
    no_diffraction: Annotated[bool, Form()] = False,
    move_tower: Annotated[float, Form()] = 0.0,
    export_format: Annotated[str, Form()] = "json",
    locale: Annotated[str, Form()] = "pt-BR",
):
    """Validate one profile and run one synchronous core analysis."""
    if units not in ("meters", "feet"):
        raise HTTPException(422, "units must be 'meters' or 'feet'")
    try:
        polarization = _validate_polarization(polarization)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if antenna_type not in ANTENNA_TYPES:
        raise HTTPException(422, f"invalid antenna_type: {antenna_type}")
    if not profile.filename:
        raise HTTPException(422, "profile must have a filename")
    content = await profile.read()
    if len(content) > MAX_PROFILE_BYTES:
        raise HTTPException(413, "profile file is too large")
    try:
        frequency_mhz = parse_frequency(frequency)
        aoa_data = None
        aoa_band = frequency_to_band(frequency_mhz)
        aoa_source = None
        if aoa_file is not None and aoa_file.filename:
            aoa_content = await aoa_file.read()
            if len(aoa_content) > MAX_PROFILE_BYTES:
                raise ValueError("arquivo .PRN muito grande")
            aoa_data = parse_prn_multiband(aoa_content.decode("utf-8", errors="replace"), aoa_band)
            aoa_source = aoa_file.filename
        else:
            aoa_data, aoa_source = _default_aoa_for_band(aoa_band, aoa_default)
        antenna_heights, antenna_phases = _parse_heights(heights, units)
        move_tower_ft = move_tower * (3.28084 if units == "meters" else 1.0)
        with tempfile.NamedTemporaryFile(suffix=".PRO", mode="wb") as temporary:
            temporary.write(content)
            temporary.flush()
            # Parse once here to report malformed profiles as input errors,
            # before entering the numerical library.
            parse_profile(temporary.name)
            result = analyze(AnalysisConfig(
                profile_path=temporary.name,
                frequency_mhz=frequency_mhz,
                antenna_heights_ft=antenna_heights,
                antenna_phases=antenna_phases,
                soil_epsr=soil_epsr,
                soil_sigma=soil_sigma,
                diffraction_disable=no_diffraction,
                move_tower_ft=move_tower_ft,
                antenna_pattern_type=ANTENNA_TYPES[antenna_type],
                polarization=polarization,
            ))
            flat_result = _run_uploaded_analysis(_flat_profile_content(content, units), frequency, units, heights, antenna_type, soil_epsr, soil_sigma, no_diffraction, move_tower, polarization)
    except (ValueError, OpenHFTAError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(400, f"could not read profile: {exc}") from exc
    payload = _attach_plot_data(_serialize_result(result, locale), flat_result, aoa_data, aoa_band, aoa_source)
    payload["sources"] = {"profile_name": profile.filename, "prn_name": aoa_source}
    if export_format == "json":
        return JSONResponse(payload)
    if export_format == "csv":
        return Response(result_csv(payload), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=openhfta-pattern.csv"})
    if export_format in ("png", "svg", "pdf"):
        media = {"png": "image/png", "svg": "image/svg+xml", "pdf": "application/pdf"}[export_format]
        return Response(result_figure(payload, export_format, locale), media_type=media, headers={"Content-Disposition": f"attachment; filename=openhfta-pattern.{export_format}"})
    raise HTTPException(422, "export_format must be json, csv, png, svg or pdf")


@app.post("/api/compare")
async def compare_endpoint(
    frequency: Annotated[str, Form()],
    profile: Annotated[UploadFile | None, File(description="Terrain profile in .PRO format")]=None,
    profiles: Annotated[list[UploadFile] | None, File(description="Terrain profiles in .PRO format, shared or one per scenario")]=None,
    scenario_prns: Annotated[list[UploadFile] | None, File(description="Scenario-specific .PRN files, indexed by scenario_configs")]=None,
    aoa_file: Annotated[UploadFile | None, File(description="Optional angle-of-arrival statistics .PRN")]=None,
    aoa_default: Annotated[str | None, Form()] = None,
    heights_a: Annotated[str, Form()] = "10",
    antenna_type_a: Annotated[str, Form()] = "Dipole",
    heights_b: Annotated[str, Form()] = "10 20",
    antenna_type_b: Annotated[str, Form()] = "2-Ele",
    units: Annotated[str, Form()] = "meters",
    polarization: Annotated[str, Form()] = "horizontal",
    soil_epsr: Annotated[float, Form()] = 13.0,
    soil_sigma: Annotated[float, Form()] = 0.005,
    no_diffraction: Annotated[bool, Form()] = False,
    move_tower: Annotated[float, Form()] = 0.0,
    scenario_configs: Annotated[str | None, Form()] = None,
    export_format: Annotated[str, Form()] = "json",
    locale: Annotated[str, Form()] = "pt-BR",
):
    """Run two or more antenna/height/profile scenarios and compare them."""
    uploaded_profiles = list(profiles or [])
    if profile is not None:
        uploaded_profiles.insert(0, profile)
    uploaded_profiles = [item for item in uploaded_profiles if item.filename]
    if not uploaded_profiles:
        raise HTTPException(422, "at least one profile must have a filename")
    if len(uploaded_profiles) > MAX_SCENARIOS:
        raise HTTPException(422, f"at most {MAX_SCENARIOS} terrain profiles are supported per request")
    default_configs = [
        {"name": f"{antenna_type_a} / {heights_a}", "heights": heights_a, "antenna_type": antenna_type_a},
        {"name": f"{antenna_type_b} / {heights_b}", "heights": heights_b, "antenna_type": antenna_type_b},
    ]
    try:
        polarization = _validate_polarization(polarization)
        configs = json.loads(scenario_configs) if scenario_configs else default_configs
        if not isinstance(configs, list) or len(configs) < 2:
            raise ValueError("scenario_configs must contain at least two scenarios")
        if len(configs) > MAX_SCENARIOS:
            raise ValueError(f"scenario_configs accepts at most {MAX_SCENARIOS} scenarios per request")
        for config in configs:
            if not isinstance(config, dict) or config.get("antenna_type") not in ANTENNA_TYPES or not config.get("heights"):
                raise ValueError("each scenario needs antenna_type and heights")
            profile_index = config.get("profile_upload_index")
            if profile_index is not None and (not isinstance(profile_index, int) or profile_index < 0):
                raise ValueError("profile_upload_index must be a non-negative integer")
        if len(uploaded_profiles) not in (1, len(configs)):
            raise ValueError("Envie um único perfil .PRO para todos os cenários ou um perfil .PRO para cada cenário")
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    try:
        frequency_mhz = parse_frequency(frequency)
        shared_aoa = (None, None)
        aoa_band = frequency_to_band(frequency_mhz)
        if aoa_file is not None and aoa_file.filename:
            aoa_content = await aoa_file.read()
            if len(aoa_content) > MAX_PROFILE_BYTES:
                raise ValueError("arquivo .PRN muito grande")
            shared_aoa = _parse_aoa_content(aoa_content, aoa_file.filename, aoa_band)
        else:
            shared_aoa = _default_aoa_for_band(aoa_band, aoa_default)
        uploaded_prns: list[tuple[str, bytes]] = []
        for prn in scenario_prns or []:
            if not prn.filename:
                continue
            content = await prn.read()
            if len(content) > MAX_PROFILE_BYTES:
                raise ValueError("arquivo .PRN muito grande")
            uploaded_prns.append((prn.filename, content))
        profile_contents = [await source.read() for source in uploaded_profiles]
        flat_contents = [_flat_profile_content(content, units) for content in profile_contents]
        results = []
        for index, config in enumerate(configs):
            source_index = config.get("profile_upload_index", 0 if len(profile_contents) == 1 else index)
            if source_index >= len(profile_contents):
                raise ValueError("profile_upload_index does not reference an uploaded .PRO")
            scenario_polarization = _validate_polarization(config.get("polarization", polarization))
            real_result = _run_uploaded_analysis(profile_contents[source_index], frequency, units, config["heights"], config["antenna_type"], soil_epsr, soil_sigma, no_diffraction, move_tower, scenario_polarization)
            flat_result = _run_uploaded_analysis(flat_contents[source_index], frequency, units, config["heights"], config["antenna_type"], soil_epsr, soil_sigma, no_diffraction, move_tower, scenario_polarization)
            results.append((real_result, flat_result, config, uploaded_profiles[source_index].filename))
        first = results[0][0]
        pairwise = [compare_patterns(first.angles_deg, first.pattern_db, item[0].angles_deg, item[0].pattern_db) for item in results[1:]]
        comparison = dict(pairwise[0])
        comparison["pairwise"] = pairwise
        scenario_payload = []
        for result, flat_result, config, filename in results:
            metrics = summarize_pattern(result.angles_deg, result.pattern_db)
            aoa_data, aoa_source = _scenario_aoa(config, aoa_band, uploaded_prns, shared_aoa)
            serialized = _attach_plot_data(_serialize_result(result, locale), flat_result, aoa_data, aoa_band, aoa_source)
            scenario_payload.append({
                "name": config.get("name") or f"{config['antenna_type']} / {config['heights']}",
                "heights_input": config["heights"],
                "antenna_type": config["antenna_type"],
                "polarization": result.config.polarization,
                "profile_name": filename,
                "prn_name": aoa_source,
                "angles_deg": result.angles_deg.tolist(),
                "pattern_db": result.pattern_db.tolist(),
                "metrics": serialized["metrics"],
                "interpretation": interpret_pattern(serialized["metrics"], serialized["ray_trace"], serialized["profile"], locale),
                "configuration": serialized["configuration"],
                "metadata": serialized["metadata"],
                "warnings": serialized["warnings"],
                "flat_pattern_db": serialized.get("flat_pattern_db"),
                "aoa": serialized.get("aoa"),
                # Keep the same field name used by /api/analyze so the web
                # client can render terrain profiles in both modes.
                "profile": serialized["profile"],
                "ray_trace": serialized["ray_trace"],
            })
        payload = {
            "angles_deg": first.angles_deg.tolist(),
            "scenarios": scenario_payload,
            "comparison": comparison,
            "interpretation": interpret_comparison(scenario_payload, comparison, locale),
            "limitations": _model_limitations(polarization, locale),
        }
    except (ValueError, OpenHFTAError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(400, f"could not read profile: {exc}") from exc
    if export_format == "json":
        return JSONResponse(payload)
    if export_format == "csv":
        return Response(comparison_csv(payload), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=openhfta-comparison.csv"})
    if export_format in ("png", "svg", "pdf"):
        media = {"png": "image/png", "svg": "image/svg+xml", "pdf": "application/pdf"}[export_format]
        return Response(comparison_figure(payload, export_format, locale), media_type=media, headers={"Content-Disposition": f"attachment; filename=openhfta-comparison.{export_format}"})
    raise HTTPException(422, "export_format must be json, csv, png, svg or pdf")


# When the production bundle exists, the same process serves both the API and
# the web UI. API routes are declared before this mount and keep precedence.
web_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
if web_dist.is_dir():
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
