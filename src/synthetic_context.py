"""Local synthetic harness capabilities only; no Brief/UI/provider integration.

The interpreter and fixture/runner code are trusted. HMAC and object registration
reject caller data, not arbitrary code execution or introspection in this process.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile
import time

import pandas as pd

from src.scenario_comparison import ARTIFACT_TABLES, ComparisonInput, validate_comparison_input

_FIXTURE = Path(__file__).resolve().parents[1] / 'examples/planning/synthetic_demo'
_APPROVED = {
    'config.json': '6611a61d72433729241c584438d641d2ef4290716fcdc5177b4baf244e521904',
    'demand.csv': 'fb2f44256bc4ea28e22ed9900818ec7f44e35683da8c694bd1228d2540cfcc68',
    'external_receipts.csv': 'f5ad33a2dc7fef667c4a33ba6812b9fe7519723629a3aad2f7ea634bec1c106c',
    'initial_inventory.csv': '11baf5c688fb1287624fa7cecaaccf489f39bd7bfe32c17191d5187d1d19fc1c',
    'plants.csv': '457033301960c8441008d608ba7d057a03e485f47f92d0ebb430bd95237e6f12',
    'product_plant_mapping.csv': 'a485d4fc94ca1d0e4aad9a5d91fe4858fe4f35d8560872c39141d7d15c604d53',
    'products.csv': '612c3b8a87efec1d21981acb401d685fa949dc62fac482f487b3049639e09393',
    'weekly_capacity.csv': 'ee782c07e0f1062d7d7e83c46d33b1e68cfcdfd75f129572974a1e4102e82569',
    'workload_factors.csv': '1d801e1491eb3ccae4623c4ba9790abade79a10b149eee174271fdbdbe177dbb',
}

# Separate P5 admission. The manifest itself is pinned in trusted code; a
# caller-supplied manifest or path is never an authority to add fixture bytes.
_P5_LOW_RISK_ID = 'p5_low_risk_v1'
_P5_LOW_RISK_FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/p5_low_risk_v1'
_P5_LOW_RISK_MANIFEST_SHA256 = '88e3de4a24521c07b4c8cc1bf661fdf72c3310d6ca74719ec066cf45c52cca86'


class ContextRejected(ValueError):
    """Authorization or immutable evidence binding could not be established."""


@dataclass(frozen=True, slots=True)
class SyntheticContext:
    issuer_id: str
    run_id: str
    scenario: str
    manifest_sha256: str
    artifact_hashes: tuple[tuple[str, str], ...]
    expires_at: float
    nonce: str
    signature: str


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    """Verification result only: no path, table access, or reusable load authority."""
    run_id: str
    scenario: str
    manifest_sha256: str
    artifact_hashes: tuple[tuple[str, str], ...]


def _read_at(directory_fd: int, name: str) -> bytes:
    if not isinstance(name, str) or Path(name).name != name or name in ('.', '..'):
        raise ContextRejected('Invalid direct-file name')
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ContextRejected('Regular file required')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            value = stream.read(8 * 1024 * 1024 + 1)
        if len(value) > 8 * 1024 * 1024:
            raise ContextRejected('Harness file exceeds bound')
        return value
    finally:
        os.close(fd)


def _directory(path: Path) -> int:
    """Walk every component without following directory symlinks."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.absolute().parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_p5_low_risk_at(fd: int) -> tuple[dict[str, str], dict[str, bytes]]:
    """Verify a directory descriptor against the code-pinned P5 manifest."""
    raw = _read_at(fd, 'MANIFEST.json')
    if hashlib.sha256(raw).hexdigest() != _P5_LOW_RISK_MANIFEST_SHA256:
        raise ContextRejected('P5 fixture manifest changed')
    manifest = json.loads(raw)
    approved = manifest['files_sha256']
    if (set(manifest) != {'fixture_version', 'data_mode', 'files_sha256'}
            or manifest['fixture_version'] != 'p5-low-risk-v1'
            or manifest['data_mode'] != 'SYNTHETIC_DEMO'
            or type(approved) is not dict
            or set(approved) != set(_APPROVED)
            or any(type(value) is not str or len(value) != 64
                   or any(ch not in '0123456789abcdef' for ch in value)
                   for value in approved.values())):
        raise ContextRejected('P5 fixture manifest invalid')
    payloads = {name: _read_at(fd, name) for name in _APPROVED}
    if any(hashlib.sha256(payloads[name]).hexdigest() != approved[name] for name in _APPROVED):
        raise ContextRejected('P5 fixture bytes changed')
    return approved, payloads


def _read_p5_low_risk_fixture() -> tuple[dict[str, str], dict[str, bytes]]:
    """Read only the registered directory, with a code-pinned manifest and bytes."""
    try:
        fd = _directory(_P5_LOW_RISK_FIXTURE)
        try:
            return _read_p5_low_risk_at(fd)
        finally:
            os.close(fd)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ContextRejected('P5 fixture admission rejected') from exc


class SyntheticHarness:
    """Create one disposable Run from pinned fixture bytes. No path import API.

    Keep the instance in trusted local code. Use as a context manager. Construction
    executes the existing deterministic runner only in a fresh temporary folder.
    """
    def __init__(self, *, fixture_id: str = 'v1_1') -> None:
        if type(fixture_id) is not str or fixture_id not in {'v1_1', _P5_LOW_RISK_ID}:
            raise ContextRejected('Unknown synthetic fixture identity')
        self._fixture_id = fixture_id
        self._temp = tempfile.TemporaryDirectory(prefix='sct-synthetic-context-')
        self._closed = False
        self._issued: dict[str, SyntheticContext] = {}
        self._secret = secrets.token_bytes(32)
        self._issuer = secrets.token_hex(16)
        try:
            if fixture_id == 'v1_1':
                fixture_fd = _directory(_FIXTURE)
                try:
                    payloads = {name: _read_at(fixture_fd, name) for name in _APPROVED}
                finally:
                    os.close(fixture_fd)
                if any(hashlib.sha256(payloads[n]).hexdigest() != h for n, h in _APPROVED.items()):
                    raise ContextRejected('Synthetic fixture provenance mismatch')
                self._approved = _APPROVED
            else:
                self._approved, payloads = _read_p5_low_risk_fixture()
            self._config = json.loads(payloads['config.json'])
            names = {v['path'] for v in self._config['files'].values()}
            if (self._config['data_mode'] != 'SYNTHETIC_DEMO'
                    or names != set(self._approved) - {'config.json'}
                    or (fixture_id == _P5_LOW_RISK_ID
                        and self._config.get('assumption_version') != 'p5-low-risk-synthetic-v1')):
                raise ContextRejected('Unapproved fixture configuration')
            root = Path(self._temp.name)
            inputs = root / 'inputs'
            inputs.mkdir()
            for name, value in payloads.items():
                (inputs / name).write_bytes(value)
            from src.run_planning import run_csv_planning
            outputs = run_csv_planning(self._config, inputs_dir=inputs, output_root=root / 'runs')
            # The runner's return is constrained to this freshly owned workspace.
            path = outputs['run_manifest'].parent
            if path.parent != root / 'runs' or path.is_symlink():
                raise ContextRejected('Unexpected harness output location')
            self._run_path = path
            self._source_hashes = {str((inputs / n).resolve()): self._approved[n] for n in names}
            self._binding, self._scenarios = self._inspect()
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> SyntheticHarness:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def close(self) -> None:
        self._closed = True
        self._issued.clear()
        self._secret = b''
        self._temp.cleanup()

    def _inspect(self, capture: dict[str, bytes] | None = None) -> tuple[tuple[str, str, tuple[tuple[str, str], ...]], tuple[str, ...]]:
        """Read only own Run; verify data without following recorded source paths."""
        try:
            if self._fixture_id == _P5_LOW_RISK_ID:
                approved, _ = _read_p5_low_risk_fixture()
                if approved != self._approved:
                    raise ContextRejected('P5 fixture identity changed')
            fd = _directory(self._run_path)
            try:
                raw = _read_at(fd, 'run_manifest.json')
                if capture is not None:
                    capture['run_manifest'] = raw
                m = json.loads(raw)
                if (m.get('Run_ID') != self._run_path.name
                        or m.get('Data_Mode') != 'SYNTHETIC_DEMO'
                        or m.get('Configuration') != self._config
                        or m.get('Source_Hashes') != self._source_hashes
                        or set(m.get('Artifacts', {})) != set(ARTIFACT_TABLES)):
                    raise ContextRejected('Unapproved Run provenance')
                tables, hashes = {}, []
                for name, table in ARTIFACT_TABLES.items():
                    entry = m['Artifacts'][name]
                    if entry['Path'] != name + '.csv':
                        raise ContextRejected('Unapproved artifact path')
                    data = _read_at(fd, entry['Path'])
                    if capture is not None:
                        capture[name] = data
                    digest = hashlib.sha256(data).hexdigest()
                    if digest != entry['SHA256']:
                        raise ContextRejected('Artifact digest mismatch')
                    header = pd.read_csv(BytesIO(data), nrows=0)
                    ids = [c for c in header if c in ['Run_ID', 'Schema_Version', 'Scenario',
                           'Plant_ID', 'Product Card Id', 'Product Name', 'Receipt_ID', 'Order Item Id',
                           'Source_Record_ID'] or c.endswith('_Version')]
                    frame = pd.read_csv(BytesIO(data), converters={c: str for c in ids})
                    if 'Order_Date' in frame:
                        frame['Order_Date'] = pd.to_datetime(frame.Order_Date, errors='raise')
                    if type(entry['Rows']) is not int or len(frame) != entry['Rows']:
                        raise ContextRejected('Artifact row-count mismatch')
                    if frame.empty and name != 'external_receipts':
                        raise ContextRejected('Required artifact is empty')
                    tables[table] = frame
                    hashes.append((name, digest))
                scenarios = tuple(s['Scenario'] for s in self._config['scenarios'])
                for scenario in scenarios:
                    validate_comparison_input(ComparisonInput(m, tables, scenario))
                # Check lifecycle even if a corrupt configuration has no scenarios.
                if not scenarios or any(m.get(k) != v for k, v in [
                    ('Execution_Status', 'SUCCEEDED'), ('Validation_Status', 'PASSED'),
                    ('Publication_Status', 'PUBLISHED'), ('Schema_Version', 'sequential_v1')]):
                    raise ContextRejected('Run is not valid and published')
                return (m['Run_ID'], hashlib.sha256(raw).hexdigest(), tuple(sorted(hashes))), scenarios
            finally:
                os.close(fd)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ContextRejected('Harness publication evidence rejected') from exc

    def _signature(self, c: SyntheticContext) -> str:
        payload = json.dumps([c.issuer_id, c.run_id, c.scenario, c.manifest_sha256,
                              c.artifact_hashes, c.expires_at, c.nonce], allow_nan=False).encode()
        if self._fixture_id == _P5_LOW_RISK_ID:
            payload += b'|' + _P5_LOW_RISK_ID.encode() + b'|' + _P5_LOW_RISK_MANIFEST_SHA256.encode()
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()

    def issue(self, scenario: str) -> SyntheticContext:
        if self._closed or scenario not in self._scenarios:
            raise ContextRejected('Harness closed or scenario not approved')
        binding, scenarios = self._inspect()
        if binding != self._binding or scenarios != self._scenarios:
            raise ContextRejected('Evidence changed since harness publication')
        run, digest, artifacts = binding
        c = SyntheticContext(self._issuer, run, scenario, digest, artifacts,
                             time.monotonic() + 300, secrets.token_hex(24), '')
        object.__setattr__(c, 'signature', self._signature(c))
        self._issued[c.nonce] = c
        return c

    def verify(self, context: SyntheticContext) -> VerifiedIdentity:
        # These checks run before any evidence/file access.
        if self._closed or type(context) is not SyntheticContext:
            raise ContextRejected('Context was not issued by this live harness')
        try:
            registered = self._issued.get(context.nonce) is context
        except (TypeError, AttributeError):
            registered = False
        if not registered:
            raise ContextRejected('Context was not issued by this live harness')
        try:
            authentic = (context.issuer_id == self._issuer
                          and hmac.compare_digest(context.signature, self._signature(context))
                          and time.monotonic() < context.expires_at)
        except (ValueError, TypeError):
            authentic = False
        if not authentic:
            raise ContextRejected('Context authentication or expiry failed')
        binding, scenarios = self._inspect()
        if (binding != self._binding or context.scenario not in scenarios
                or binding != (context.run_id, context.manifest_sha256, context.artifact_hashes)):
            raise ContextRejected('Context evidence binding failed')
        return VerifiedIdentity(context.run_id, context.scenario,
                                context.manifest_sha256, context.artifact_hashes)

    def snapshot(self, context: SyntheticContext) -> tuple[tuple[str, bytes], ...]:
        """Authorized, revalidated immutable bytes; never exposes a load path.

        The captured bytes are exactly those inspected, preventing a later
        consumer from reopening paths after verification. No planning execution.
        """
        self.verify(context)  # Authentication/expiry checked before any read.
        captured: dict[str, bytes] = {}
        binding, scenarios = self._inspect(capture=captured)
        if (binding != (context.run_id, context.manifest_sha256, context.artifact_hashes)
                or context.scenario not in scenarios):
            raise ContextRejected('Snapshot evidence changed')
        return tuple(sorted(captured.items()))
