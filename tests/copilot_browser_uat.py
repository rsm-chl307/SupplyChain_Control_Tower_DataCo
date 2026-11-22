"""Opt-in local Chromium UAT. Synthetic fixture only; aborts off-origin requests.

Run with an existing Playwright/Chromium environment. This script provisions only
its own temporary ledger and starts only the local development app. It is not
part of unittest discovery or the synthetic_only_suite integrated group.
"""
from __future__ import annotations

import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = os.environ.get('COPILOT_P4_ENTRYPOINT', 'scenario_planning_app.py')
if APP_NAME not in {'scenario_planning_app.py', '_p4_staged_preview.py'}:
    raise AssertionError('Only a local P4 Dashboard entrypoint is allowed')
APP_PATH = ROOT / 'dashboard' / APP_NAME
if APP_PATH.is_symlink():
    raise AssertionError('P4 Dashboard entrypoint cannot be a symlink')
APP_PYTHON = os.environ.get('COPILOT_UAT_APP_PYTHON', '/usr/local/bin/python3')
PORT = 8765
URL = f'http://127.0.0.1:{PORT}'
PASSWORD = secrets.token_urlsafe(24)
CHROMIUM = ROOT / 'tmp/wp2_browser_uat_phase_a/browsers/chromium_headless_shell-1255/chrome-headless-shell-linux64/chrome-headless-shell'


def wait_for_local_server(server: subprocess.Popen) -> None:
    for _ in range(120):
        if server.poll() is not None:
            raise RuntimeError(f'Local Streamlit server exited: {server.returncode}')
        try:
            with urlopen(URL + '/_stcore/health', timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError('Local Streamlit health check timed out')


def idle(page) -> None:
    page.wait_for_function("() => document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'", timeout=60000)
    expect(page.get_by_test_id('stException')).to_have_count(0)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='copilot-browser-uat-') as temporary:
        ledger = str(Path(temporary) / 'ledger.sqlite3')
        provision = (
            'import sys; from src.ai_copilot.approval import OwnerVerifier; '
            'from src.ai_copilot.ledger import ExecutionLedger; '
            'v=OwnerVerifier.derive(sys.argv[2],b"0123456789abcdef"); '
            'ExecutionLedger.provision(sys.argv[1],v); '
            'print(v.salt_hex); print(v.digest_hex)'
        )
        prepared = subprocess.run([APP_PYTHON, '-B', '-c', provision, ledger, PASSWORD],
                                  cwd=ROOT, check=True, capture_output=True, text=True,
                                  env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        salt, digest = prepared.stdout.strip().splitlines()
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
               'COPILOT_LOCAL_OWNER_MODE': '1', 'COPILOT_LEDGER_PATH': ledger,
               'COPILOT_OWNER_SALT_HEX': salt, 'COPILOT_OWNER_SCRYPT_HEX': digest,
               'COPILOT_OFFLINE_TEST_SNAPSHOT': 'offline-browser-fixture'}
        command = [APP_PYTHON, '-B', '-m', 'streamlit', 'run',
                   str(APP_PATH), f'--server.port={PORT}',
                   '--server.address=127.0.0.1', '--server.headless=true',
                   '--browser.gatherUsageStats=false']
        server = subprocess.Popen(command, cwd=ROOT, env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            wait_for_local_server(server)
            with sync_playwright() as playwright:
                expect.set_options(timeout=60000)
                launch = {'headless': True, 'args': ['--disable-dev-shm-usage']}
                if CHROMIUM.is_file():
                    launch['executable_path'] = str(CHROMIUM)
                browser = playwright.chromium.launch(**launch)
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                external: list[str] = []

                def protect(route):
                    if route.request.url.startswith(URL):
                        route.continue_()
                    else:
                        external.append(route.request.url)
                        route.abort()

                page.route('**/*', protect)
                page.on('websocket', lambda socket: external.append(socket.url)
                        if not socket.url.startswith(URL.replace('http:', 'ws:')) else None)
                page.goto(URL)
                idle(page)
                expect(page.get_by_text('Planning', exact=True).first).to_be_visible()
                page.get_by_text('Decision Copilot', exact=True).click()
                idle(page)
                expect(page.get_by_text('Outbound request digest')).to_have_count(0)
                page.get_by_role('button', name='Create trusted synthetic Context').click()
                idle(page)
                page.get_by_role('button', name='Prepare Brief').click()
                idle(page)
                expect(page.get_by_text('Exact validated Brief')).to_be_visible()
                expect(page.get_by_text('Brief SHA-256:', exact=False)).to_be_visible()
                expect(page.get_by_text('Outbound request digest')).to_be_visible()
                digest_before = [value.strip() for value in page.locator('code').all_text_contents()
                                 if len(value.strip()) == 64][0]
                expect(page.get_by_text('Durable ledger status: NOT_STARTED')).to_be_visible()
                page.get_by_label('Owner password').fill('shared-demo-password')
                page.get_by_role('button', name='Approve exact request').click()
                idle(page)
                expect(page.get_by_text('Approval status: REJECTED')).to_be_visible()
                page.get_by_label('Owner password').fill(PASSWORD)
                page.get_by_role('button', name='Approve exact request').click()
                idle(page)
                expect(page.get_by_text('Approval status: VALID')).to_have_count(1)
                page.get_by_role('button', name='Preview Fake Provider response').click()
                idle(page)
                expect(page.get_by_text('Validated advisory preview — qualitative only')).to_be_visible()
                expect(page.get_by_text('Advisory severity / 建議性嚴重程度: Medium')).to_be_visible()
                expect(page.get_by_text('Capacity_Utilization', exact=False).first).to_be_visible()
                page.get_by_label('Synthetic scenario').click()
                page.get_by_role('option', name='Demand_Surge').click()
                idle(page)
                page.get_by_role('button', name='Create trusted synthetic Context').click()
                idle(page)
                page.get_by_role('button', name='Prepare Brief').click()
                idle(page)
                expect(page.get_by_text('Outbound request digest')).to_be_visible()
                digest_after = [value.strip() for value in page.locator('code').all_text_contents()
                                if len(value.strip()) == 64][0]
                assert digest_after != digest_before
                expect(page.get_by_text('Approval status: NOT APPROVED')).to_be_visible()
                assert page.get_by_role('button', name='Request analysis').count() == 0
                page.set_viewport_size({'width': 390, 'height': 844})
                expect(page.get_by_text('Exact validated Brief')).to_be_visible()
                page.get_by_role('button', name='Close and remove synthetic Context').click()
                idle(page)
                expect(page.get_by_text('Exact validated Brief')).to_have_count(0)
                page.set_viewport_size({'width': 1440, 'height': 1000})
                page.reload()
                idle(page)
                page.get_by_text('Decision Copilot', exact=True).click()
                idle(page)
                expect(page.get_by_text('Outbound request digest')).to_have_count(0)
                browser.close()
                assert not external, f'Blocked off-origin browser requests: {external}'
                print('CHROMIUM_SYNTHETIC_UAT PASS external_requests=0')
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
