"""Offline regressions for unavailable direct Inep HTTPS transports."""
import importlib.util
import ssl
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError

script = Path(__file__).resolve().parents[1] / 'scripts' / 'download_inep_enem.py'
spec = importlib.util.spec_from_file_location('inep_transport', script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TransportTests(unittest.TestCase):
    def test_python_timeout_uses_verified_fallback(self):
        opener = SimpleNamespace(open=lambda *a, **k: (_ for _ in ()).throw(URLError(TimeoutError('timed out'))))
        with patch.object(mod, 'build_opener', return_value=opener), patch.object(
                mod, '_curl_verified', return_value=b'%PDF recovered') as fallback:
            result = mod._download_once('https://download.inep.gov.br/a.pdf',
                                       ssl.create_default_context(), ca_bundle='trusted.pem')
        self.assertEqual(result, b'%PDF recovered')
        fallback.assert_called_once_with('https://download.inep.gov.br/a.pdf', ca_bundle='trusted.pem')

    def test_curl_retries_direct_ipv4_without_weakening_tls(self):
        commands = []
        def run(cmd, **kwargs):
            commands.append(cmd)
            if len(commands) == 1:
                return SimpleNamespace(returncode=28, stderr='timed out')
            Path(cmd[cmd.index('--output') + 1]).write_bytes(b'%PDF recovered')
            return SimpleNamespace(returncode=0, stderr='')
        with patch.object(mod.subprocess, 'run', side_effect=run):
            self.assertEqual(mod._curl_verified('https://download.inep.gov.br/a.pdf', ca_bundle='trusted.pem'), b'%PDF recovered')
        self.assertNotIn('--noproxy', commands[0])
        self.assertIn('--noproxy', commands[1])
        for cmd in commands:
            self.assertIn('--ipv4', cmd)
            self.assertIn('--cacert', cmd)
            self.assertFalse({'-k', '--insecure', '-L', '--location'}.intersection(cmd))

    def test_curl_exhaustion_remains_failure(self):
        with patch.object(mod.subprocess, 'run', return_value=SimpleNamespace(returncode=28, stderr='timed out')):
            with self.assertRaisesRegex(URLError, 'transports failed'):
                mod._curl_verified('https://download.inep.gov.br/a.pdf')

    def test_pdf_timeout_stops_batch_and_records_blocker(self):
        calls = []
        def request(url, **kwargs):
            calls.append(url)
            if url.endswith('.pdf'):
                raise RuntimeError('Falha após 3 tentativas: timed out')
            return b'index'
        discovered = {(1, 'azul'): {'code': 1, 'prova': 'https://download.inep.gov.br/a.pdf', 'gabarito': None}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(mod, 'discover', return_value=discovered), patch.object(mod, 'request', side_effect=request):
            root = Path(tmp)
            report = mod.acquire(root/'pdfs', root/'manifest.json', years=[2017, 2018], delay=0)
            self.assertEqual(report['results'][-1]['status'], 'source_transport_blocked')
            self.assertEqual(len(calls), 2)
            self.assertFalse((root/'manifest.json').exists())
            self.assertTrue((root/'pdfs'/'download-report.json').exists())


if __name__ == '__main__':
    unittest.main()
