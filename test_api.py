import asyncio
import json
import os
import re
import unittest
import httpx
from pathlib import Path
from unittest.mock import patch

from api.main import app
import openhfta_core.ai as ai
from openhfta_core.exports import result_figure

ROOT = Path(__file__).parent


class TestAPI(unittest.TestCase):
    def request(self, method, url, **kwargs):
        async def run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, url, **kwargs)
        return asyncio.run(run())

    def test_health(self):
        response = self.request("GET", "/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(response.json()["core_available"])

    def test_bundled_prns_are_available(self):
        response = self.request("GET", "/api/prns")
        self.assertEqual(response.status_code, 200)
        files = response.json()["files"]
        self.assertEqual(files, sorted(
            path.name for path in (ROOT / "prns").glob("*.PRN")
            if not path.stem.lower().endswith("-smoke") and path.name != "PT9-FT8-OBS.PRN"
        ))
        for hidden in ("PT9-US-smoke.PRN", "PY5-EU-smoke.PRN", "PT9-FT8-OBS.PRN"):
            self.assertNotIn(hidden, files)
        for prefix in ("PP5", "PT9", "PY1", "PY5"):
            for target in ("AF", "AS", "EU", "JA", "OC", "SA", "US"):
                self.assertIn(f"{prefix}-{target}.PRN", files)

    def test_web_fallback_prn_list_matches_bundled_prns(self):
        source = (ROOT / "web/src/App.tsx").read_text(encoding="utf-8")
        block = re.search(r"const DEFAULT_PRN_OPTIONS = \[(.*?)\]", source, re.S).group(1)
        self.assertEqual(sorted(re.findall(r"'([^']+\.PRN)'", block)), self.request("GET", "/api/prns").json()["files"])

    def test_bundled_prns_are_well_formed(self):
        bands = ["80m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"]
        for name in self.request("GET", "/api/prns").json()["files"]:
            lines = (ROOT / "prns" / name).read_text(encoding="ascii").splitlines()
            self.assertEqual(lines[1].split(), ["Elev", *bands], name)
            rows = [line.split() for line in lines[2:] if line.strip()]
            self.assertEqual([int(row[0]) for row in rows], list(range(1, 71)), name)
            for column, band in enumerate(bands, start=1):
                total = sum(float(row[column]) for row in rows)
                # Each band is either a full distribution or has no statistics at all.
                self.assertTrue(total == 0 or abs(total - 100.0) <= 1.0, f"{name} {band}: {total:.1f}%")

    def test_default_prn_band_without_statistics_is_not_an_error(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        response = self.request(
            "POST", "/api/analyze", data={"frequency": "80m", "aoa_default": "PY1-JA.PRN"},
            files={"profile": (profile.name, profile.read_bytes(), "text/plain")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertNotIn("figure_of_merit_db", payload["metrics"])
        self.assertIsNone(payload["sources"]["prn_name"])

    def test_uploaded_prn_band_without_statistics_is_reported(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        prn = b"Test path\nElev      80m    20m\n 1        0.0   40.0\n 5        0.0   60.0\n"
        response = self.request(
            "POST", "/api/analyze", data={"frequency": "80m"},
            files={
                "profile": (profile.name, profile.read_bytes(), "text/plain"),
                "aoa_file": ("TEST.PRN", prn, "text/plain"),
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertFalse(payload["aoa"]["available"])
        self.assertIn("80m", payload["aoa"]["message"])
        self.assertNotIn("figure_of_merit_db", payload["metrics"])

    def test_feedback_is_sent_to_configured_mailer(self):
        with patch("api.main._send_feedback_email") as send_feedback:
            response = self.request(
                "POST",
                "/api/feedback",
                data={"name": "Maria", "email": "maria@example.com", "category": "Sugestão", "message": "A interface ficou muito útil."},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "sent")
        send_feedback.assert_called_once_with("Maria", "maria@example.com", "Sugestão", "A interface ficou muito útil.")

    def test_feedback_rejects_invalid_email(self):
        response = self.request(
            "POST",
            "/api/feedback",
            data={"email": "email-invalido", "message": "Mensagem"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("e-mail válido", response.json()["detail"])

    def test_exported_figure_contains_web_report_sections(self):
        payload = {
            "angles_deg": [0, 5, 10],
            "pattern_db": [1.0, 4.0, 2.0],
            "flat_pattern_db": [0.5, 2.5, 1.0],
            "aoa": {"available": True, "band": "20m", "angles_deg": [1, 5], "probabilities_pct": [20, 30]},
            "profile": {"points": 3, "distances_m": [0, 500, 1000], "heights_m": [100, 110, 105]},
            "configuration": {"frequency_mhz": 14.1, "polarization": "vertical", "antenna_heights_m": [10], "diffraction_disable": False},
            "sources": {"profile_name": "MORRO.PRO", "prn_name": "CAMPO.PRN"},
            "ray_trace": {"paths": [{"kind": "direct", "distances_m": [0, 1000], "heights_m": [110, 105]}]},
            "metrics": {"peak": {"value_db": 4, "angle_deg": 5}, "integrated_average_gain": {"average_db": 2}, "beamwidth_3db": {"width_deg": 8}},
            "limitations": ["Modelo bidimensional."],
        }
        svg = result_figure(payload, "svg")
        png = result_figure(payload, "png")
        self.assertIn(b"OpenHFTA", svg)
        self.assertIn(b"PADR", svg)
        self.assertIn(b"PERFIL DO TERRENO", svg)
        self.assertIn(b"TRA", svg)
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_invalid_profile_is_rejected(self):
        response = self.request(
            "POST",
            "/api/analyze",
            data={"frequency": "20m"},
            files={"profile": ("bad.PRO", b"feet\n0 1\n0 2\n", "text/plain")},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("increasing", response.json()["detail"])

    def test_reference_analysis(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        response = self.request(
            "POST",
            "/api/analyze",
            data={"frequency": "20m", "units": "meters", "heights": "10"},
            files={"profile": (profile.name, profile.read_bytes(), "text/plain")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(payload["angles_deg"]), 140)
        self.assertAlmostEqual(max(payload["pattern_db"]), 9.999393, places=4)
        self.assertEqual(payload["configuration"]["antenna_phases"], [1, 1, 1, 1])
        self.assertIn("beamwidth_3db", payload["metrics"])
        self.assertAlmostEqual(payload["metrics"]["peak"]["angle_deg"], 27.25)
        self.assertIn("beginner", payload["interpretation"])
        ray_counts = payload["ray_trace"]["counts"]
        self.assertTrue(payload["ray_trace"]["available"])
        self.assertIn("direct", ray_counts)
        self.assertIn("reflected", ray_counts)
        self.assertTrue(any(kind in ray_counts for kind in ("reflected_diffracted", "double_diffracted", "reflected_double_diffracted")))

    def test_vertical_polarization_is_rejected(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        response = self.request("POST", "/api/analyze", data={"frequency": "20m", "polarization": "vertical"}, files={"profile": (profile.name, profile.read_bytes(), "text/plain")})
        self.assertEqual(response.status_code, 422)
        self.assertIn("polarization", response.json()["detail"])

    def test_invalid_polarization_is_rejected(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        response = self.request("POST", "/api/analyze", data={"frequency": "20m", "polarization": "circular"}, files={"profile": (profile.name, profile.read_bytes(), "text/plain")})
        self.assertEqual(response.status_code, 422)
        self.assertIn("polarization", response.json()["detail"])

    def test_csv_export(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        response = self.request("POST", "/api/analyze", data={"frequency": "20m", "export_format": "csv"}, files={"profile": (profile.name, profile.read_bytes(), "text/plain")})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"angle_deg,pattern_db"))

    def test_analysis_with_aoa_and_flat_reference(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        prn = b"Test path\nElev      20m\n 1        10.0\n 5        20.0\n10        30.0\n"
        response = self.request(
            "POST", "/api/analyze", data={"frequency": "20m"},
            files={
                "profile": (profile.name, profile.read_bytes(), "text/plain"),
                "aoa_file": ("TEST.PRN", prn, "text/plain"),
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["aoa"]["band"], "20m")
        self.assertEqual(len(payload["flat_pattern_db"]), len(payload["pattern_db"]))
        self.assertIn("figure_of_merit_db", payload["metrics"])

    def test_compare_scenarios(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        response = self.request("POST", "/api/compare", data={"frequency": "20m", "heights_a": "10", "antenna_type_a": "Dipole", "heights_b": "10 20", "antenna_type_b": "2-Ele"}, files={"profile": (profile.name, profile.read_bytes(), "text/plain")})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(payload["scenarios"]), 2)
        self.assertIn("rmse_db", payload["comparison"])
        self.assertIn("headline", payload["interpretation"])

    def test_compare_four_scenarios_and_profiles(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        profile_bytes = profile.read_bytes()
        configs = [
            {"name": "Norte", "heights": "10", "antenna_type": "Dipole"},
            {"name": "Leste", "heights": "15", "antenna_type": "Dipole"},
            {"name": "Sul", "heights": "10 20", "antenna_type": "2-Ele", "polarization": "horizontal"},
            {"name": "Oeste", "heights": "12 22*", "antenna_type": "2-Ele"},
        ]
        files = [
            ("profiles", (f"{name}.PRO", profile_bytes, "text/plain"))
            for name in ("north", "east", "south", "west")
        ]
        response = self.request(
            "POST", "/api/compare",
            data={"frequency": "20m", "scenario_configs": json.dumps(configs)},
            files=files,
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(payload["scenarios"]), 4)
        self.assertEqual(payload["scenarios"][2]["polarization"], "horizontal")
        self.assertEqual(len(payload["comparison"]["pairwise"]), 3)
        self.assertEqual(len(payload["scenarios"][0]["profile"]["distances_m"]), 148)
        self.assertTrue(payload["limitations"])

    def test_compare_accepts_more_than_four_scenarios(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        configs = [{"name": f"Cenário {index + 1}", "heights": str(8 + 2 * index), "antenna_type": "Dipole"} for index in range(6)]
        response = self.request(
            "POST", "/api/compare",
            data={"frequency": "20m", "scenario_configs": json.dumps(configs)},
            files={"profile": (profile.name, profile.read_bytes(), "text/plain")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual([scenario["name"] for scenario in payload["scenarios"]], [config["name"] for config in configs])
        self.assertEqual(len(payload["comparison"]["pairwise"]), 5)
        exported = self.request(
            "POST", "/api/compare",
            data={"frequency": "20m", "scenario_configs": json.dumps(configs), "export_format": "png"},
            files={"profile": (profile.name, profile.read_bytes(), "text/plain")},
        )
        self.assertEqual(exported.status_code, 200, exported.text[:300])
        self.assertTrue(exported.content.startswith(b"\x89PNG"))

    def test_compare_requires_at_least_two_scenarios(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        response = self.request(
            "POST", "/api/compare",
            data={"frequency": "20m", "scenario_configs": json.dumps([{"name": "Só um", "heights": "10", "antenna_type": "Dipole"}])},
            files={"profile": (profile.name, profile.read_bytes(), "text/plain")},
        )
        self.assertEqual(response.status_code, 422)

    def test_compare_rejects_vertical_scenario(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        configs = [
            {"name": "Norte", "heights": "10", "antenna_type": "Dipole"},
            {"name": "Sul", "heights": "10 20", "antenna_type": "2-Ele", "polarization": "vertical"},
        ]
        response = self.request(
            "POST", "/api/compare",
            data={"frequency": "20m", "scenario_configs": json.dumps(configs)},
            files={"profile": (profile.name, profile.read_bytes(), "text/plain")},
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_compare_scenarios_with_individual_prns(self):
        profile = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        profile_bytes = profile.read_bytes()
        prn_20m = b"North\nElev      20m\n 1        10.0\n 5        20.0\n10        30.0\n"
        prn_10m = b"South\nElev      20m\n 1        30.0\n 5        20.0\n10        10.0\n"
        configs = [
            {"name": "Norte", "heights": "10", "antenna_type": "Dipole", "prn_upload_index": 0},
            {"name": "Sul", "heights": "10", "antenna_type": "Dipole", "prn_upload_index": 1},
        ]
        response = self.request(
            "POST", "/api/compare",
            data={"frequency": "20m", "scenario_configs": json.dumps(configs)},
            files=[
                ("profile", (profile.name, profile_bytes, "text/plain")),
                ("scenario_prns", ("NORTE.PRN", prn_20m, "text/plain")),
                ("scenario_prns", ("SUL.PRN", prn_10m, "text/plain")),
            ],
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual([scenario["prn_name"] for scenario in payload["scenarios"]], ["NORTE.PRN", "SUL.PRN"])
        self.assertEqual([scenario["heights_input"] for scenario in payload["scenarios"]], ["10", "10"])
        self.assertEqual([scenario["antenna_type"] for scenario in payload["scenarios"]], ["Dipole", "Dipole"])
        self.assertTrue(all(scenario["profile_name"] for scenario in payload["scenarios"]))
        self.assertEqual(payload["scenarios"][0]["aoa"]["probabilities_pct"], [10.0, 20.0, 30.0])
        self.assertEqual(payload["scenarios"][1]["aoa"]["probabilities_pct"], [30.0, 20.0, 10.0])

    def test_compare_scenarios_with_explicit_profile_indexes(self):
        first = ROOT / "test/pro/PR1T-torre1-332.00.PRO"
        second = ROOT / "test/pro/PR1T-torre1-333.00.PRO"
        configs = [
            {"name": "Perfil 1", "heights": "10", "antenna_type": "Dipole", "profile_upload_index": 0},
            {"name": "Perfil 2", "heights": "10", "antenna_type": "Dipole", "profile_upload_index": 1},
        ]
        response = self.request(
            "POST", "/api/compare",
            data={"frequency": "20m", "scenario_configs": json.dumps(configs)},
            files=[
                ("profiles", ("NORTE.PRO", first.read_bytes(), "text/plain")),
                ("profiles", ("SUL.PRO", second.read_bytes(), "text/plain")),
            ],
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([scenario["profile_name"] for scenario in response.json()["scenarios"]], ["NORTE.PRO", "SUL.PRO"])

    def test_ai_status_without_key(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}), patch.object(ai, "_DOTENV_VALUES", {**ai._DOTENV_VALUES, "OPENROUTER_API_KEY": ""}):
            response = self.request("GET", "/api/ai/status")
        self.assertEqual(response.status_code, 200)
        self.assertIn("enabled", response.json())

    def test_ai_explain_requires_configuration(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}), patch.object(ai, "_DOTENV_VALUES", {**ai._DOTENV_VALUES, "OPENROUTER_API_KEY": ""}):
            response = self.request("POST", "/api/ai/explain", json={"analysis": {"metrics": {}}})
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
