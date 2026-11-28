import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class TestCryptoUtils(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip_and_config_levels(self):
        from controlador.auth.crypto_utils import (
            encrypt_str,
            decrypt_str,
            process_config_for_save,
            process_config_for_load,
        )

        enc = encrypt_str("secreto123")
        self.assertTrue(enc.startswith("ENC:"))
        self.assertEqual(decrypt_str(enc), "secreto123")

        cfg = {
            "usuario": "demo",
            "correo": "demo@example.com",
            "login": True,
            "nivel_seguridad": "avanzado",
        }
        saved = process_config_for_save(cfg)
        self.assertFalse(saved["login"])
        self.assertTrue(saved["usuario"].startswith("ENC:"))
        self.assertTrue(saved["correo"].startswith("ENC:"))

        loaded = process_config_for_load(saved)
        self.assertEqual(loaded["usuario"], "demo")
        self.assertEqual(loaded["correo"], "demo@example.com")

    def test_legacy_decrypt_fallback(self):
        from controlador.auth.crypto_utils import _get_legacy_fernet, decrypt_str

        legacy_token = _get_legacy_fernet().encrypt(b"legacy_value").decode("utf-8")
        self.assertEqual(decrypt_str(f"ENC:{legacy_token}"), "legacy_value")


class TestAuthValidationAndController(unittest.TestCase):
    def test_hash_and_verify_password(self):
        from controlador.auth.validation import AuthValidator

        hashed = AuthValidator.hash_password("mi_clave_segura")
        self.assertIn(":", hashed)
        self.assertTrue(AuthValidator.verify_password(hashed, "mi_clave_segura"))
        self.assertFalse(AuthValidator.verify_password(hashed, "otra_clave"))

    def test_lockout_after_max_attempts(self):
        from controlador.auth.validation import AuthValidator, MAX_INTENTOS_LOGIN

        intentos = {}
        for _ in range(MAX_INTENTOS_LOGIN):
            AuthValidator._registrar_fallo("user_test", intentos)
        bloqueado, msg = AuthValidator.verificar_bloqueo("user_test", intentos)
        self.assertTrue(bloqueado)
        self.assertIn("bloqueada", msg.lower())

    def test_autenticar_y_registrar_validacion_basica(self):
        from controlador.auth.autenticacion import autenticar_usuario, registrar_usuario

        ok, estado, msg, _, _ = autenticar_usuario("", "")
        self.assertFalse(ok)
        self.assertEqual(estado, "error")

        ok_reg, msg_reg = registrar_usuario("p", "u", "123", "456")
        self.assertFalse(ok_reg)
        self.assertIn("coinciden", msg_reg)


class TestJsonLogger(unittest.TestCase):
    def test_jsonl_append_and_thread_safety(self):
        from vistas.utils.logs import JsonLogger

        orig_stdout, orig_stderr = sys.stdout, sys.stderr
        try:
            with tempfile.TemporaryDirectory() as td:
                logger = JsonLogger(td)
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr

                def worker(tid):
                    for i in range(10):
                        logger.log("INFO", f"t{tid}-{i}", modulo="Test")

                threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                lines = logger.archivo_actual.read_text(encoding="utf-8").strip().splitlines()
                self.assertEqual(len(lines), 40)
                parsed = [json.loads(line) for line in lines]
                self.assertTrue(all("timestamp" in item and item["modulo"] == "Test" for item in parsed))
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            JsonLogger._instancia = None


class TestMainAndUtils(unittest.TestCase):
    def test_extraer_url_de_argumentos(self):
        import main

        self.assertEqual(main.extraer_url_de_argumentos(["app.py", "https://example.com"]), "https://example.com")
        self.assertEqual(main.extraer_url_de_argumentos(["app.py", "--url=http://localhost:8000"]), "http://localhost:8000")
        self.assertEqual(main.extraer_url_de_argumentos(["app.py", "--url", "https://test.dev"]), "https://test.dev")
        self.assertIsNone(main.extraer_url_de_argumentos(["app.py"]))

    def test_event_bus_and_diagnostics_and_qss(self):
        from controlador.utils.event_bus import MultitoolEventBus
        from vistas.utils.startup_diagnostics import StartupDiagnostics
        from vistas.estilos import generar_qss_global

        bus = MultitoolEventBus()
        recibido = []
        bus.subscribe("ping", lambda p: recibido.append(p["v"]))
        bus.publish("ping", {"v": 42})
        self.assertEqual(recibido, [42])

        ok, warnings = StartupDiagnostics.run_checks()
        self.assertTrue(ok)
        self.assertIsInstance(warnings, list)

        qss = generar_qss_global({"acento": "#123456"})
        self.assertIn("#123456", qss)

    def test_base_app_gui_mixins(self):
        from vistas.gui import BaseAppGUI

        for method_name in (
            "_restaurar_geometria_ventana",
            "_guardar_geometria_ventana",
            "toggle_zen_mode",
            "_setup_ram_monitor",
            "_liberar_memoria_manual",
            "navegar_atras",
            "navegar_adelante",
            "abrir_en_modulo",
        ):
            self.assertTrue(hasattr(BaseAppGUI, method_name), f"Falta {method_name} en BaseAppGUI")


if __name__ == "__main__":
    unittest.main()
