---
schema: gentle-ai.sdd-research/v1
change: multi-user-foundation
lane: crypto
revision: 1
outcome: partial
artifact_store: openspec
artifact_path: openspec/changes/multi-user-foundation/research.md
date: 2026-10-22
author: sdd-research
---

# Research — `multi-user-foundation` — Crypto lane

**Scope of this lane.** Cryptography evidence for the passwordless identity layer
(device keypair, challenge/response) and for the per-user encrypted AI
credentials. Four sub-lanes, exactly as selected:

1. The ECDSA signature encoding mismatch (P1363 vs DER) — highest risk.
2. Master key handling and authenticated encryption for stored credentials.
3. Challenge/response with replay protection.
4. Key rotation and revocation semantics for a device public key.

This artifact records **evidence only**. Product choices (enrollment gate,
recovery path, credential fallback policy) remain owner decisions and are
listed separately in §9 as non-authoritative.

---

## 0. Outcome, admission, observed grants

| Field | Value |
|---|---|
| Schema | `gentle-ai.sdd-research/v1` |
| Revision | `1` (positive) |
| Outcome | **`partial`** |
| Admission | `gentle-ai.sdd-research-capability/v1` — admitted for the locally-inspectable primary-source class enumerated in the request |
| Observed exact grants | `documentation: []` · `open-web: []` |

**Why `partial`, not `done`.** Sub-lane 1's *browser-side* question — which
encoding the browser's WebCrypto `ECDSA` `sign()` produces by default — cannot
be answered from any source available in this environment, and four
library-behaviour questions are enforced in compiled Rust with no Python-visible
specification. All of these are enumerated in §7 (G-1 … G-8) with the exact
evidence that would close them. Every *server-side* question in the lane — the
encoding conversion, the AEAD choice, the key-derivation choice, the challenge
consumption mechanics, the rotation semantics — **is** answered from
inspectable sources, and the answers are recorded below.

**Admission basis and its limit (explicit, auditable).** No web page, no
external documentation service, and no text of any RFC or standard was
consulted. Every claim in §3 cites a file that exists on this machine at a
stated path and line range. Where a claim would have required an external
standard, the claim is recorded as `unsupported` rather than asserted.

**Interpretation note / risk for the orchestrator.** The request enumerated
three permitted evidence bases — the locally installed `cryptography` 50.0.2
package, the Python standard library, and the repository — and stated that
their source is primary evidence. I classified them as class **`local-source`**
and used only those. If the orchestrator's intent was that the `documentation`
grant covers *external* documentation services only, then `local-source` is an
undeclared class and this lane's admission should be re-confirmed. I did not
treat an empty grant list as licence to assert anything unsourced.

**Method note that changes how a future phase must verify.** The `glob` tool
returns **no files** under `backend/venv/**` (it does not traverse the
gitignored virtualenv), while `read` and `grep` do traverse it. An earlier
artifact in this change concluded "no
`backend/venv/Lib/site-packages/cryptography`" — that conclusion was an
artifact of `glob`, not of the filesystem. **The package is present.** Any
future phase that needs to prove a package is or is not installed must use
`read`/`grep` on an explicit path, never `glob`.

---

## 1. Questions

**Q1 (sub-lane 1 — signature encoding).** Which encoding does WebCrypto
`ECDSA`/`P-256` produce by default? How is P1363 → DER and DER → P1363
converted, using what exact `cryptography` 50.0.2 API? What are the DER
encoding rules involved, and why does a naive `r.to_bytes(32) + s.to_bytes(32)`
fail? How is the round trip unit-tested? Does `cryptography` 50.0.2 offer a
direct P1363 helper that makes the conversion unnecessary?

**Q2 (sub-lane 2 — master key + AEAD).** How must a master key supplied by
environment variable be validated (length, encoding, version prefix)? How do
Fernet and AES-GCM differ in what they guarantee against tampering, truncation
and nonce reuse, and what does each *not* guarantee? Is key derivation
(PBKDF2/scrypt/Argon2) needed when the master key is a high-entropy
machine-generated secret rather than a human passphrase? What is the operational
consequence of losing the master key?

**Q3 (sub-lane 3 — challenge/replay).** What is a concrete server-issued
one-shot challenge design, why must the challenge be single-use and bound to
device and session, how is it stored and expired, what makes consumption
atomic, what role do timestamp and nonce play, and what constant-time
comparison is required?

**Q4 (sub-lane 4 — rotation/revocation).** What must a key-rotation flow
guarantee so that a new key does not silently invalidate an enrolled device
without re-proof of possession of the private key, and what does revocation
mean operationally?

---

## 2. Sources

All sources were read on **2026-10-22** against the working tree as it stands.
Paths are absolute-relative to `D:\Proyectos\PAES\New Peak`.

| id | class | title / publisher | path | excerpt |
|---|---|---|---|---|
| S-01 | local-source | `cryptography` 50.0.2 — asymmetric utils (The Python Cryptographic Authority) | `backend/venv/Lib/site-packages/cryptography/hazmat/primitives/asymmetric/utils.py` | L10-11: `decode_dss_signature = asn1.decode_dss_signature` / `encode_dss_signature = asn1.encode_dss_signature` |
| S-02 | local-source | `cryptography` 50.0.2 — Rust `asn1` binding stub | `backend/venv/Lib/site-packages/cryptography/hazmat/bindings/_rust/asn1.pyi` | L5-6: `def decode_dss_signature(signature: bytes) -> tuple[int, int]` / `def encode_dss_signature(r: int, s: int) -> bytes` |
| S-03 | local-source | `cryptography` 50.0.2 — SSH serialization (ECDSA signature re-encode before `verify`) | `backend/venv/Lib/site-packages/cryptography/hazmat/primitives/serialization/ssh.py` | L987-996 and L1582-1592 (see C1.4, C1.5) |
| S-04 | local-source | `cryptography` 50.0.2 — `ec` primitives | `backend/venv/Lib/site-packages/cryptography/hazmat/primitives/asymmetric/ec.py` | L169-178 `verify`; L180-192 `from_encoded_point`; L232-237 `SECP256R1.key_size = 256` |
| S-05 | local-source | `cryptography` version marker | `backend/venv/Lib/site-packages/cryptography/__about__.py` | L13: `__version__ = "50.0.2"` |
| S-06 | local-source | `cryptography` 50.0.2 distribution metadata | `backend/venv/Lib/site-packages/cryptography-50.0.2.dist-info/METADATA` | L3 `Version: 50.0.2`; L36 `Requires-Python: >=3.9, !=3.9.0, !=3.9.1`; L26 `Requires-Dist: cffi>=2.0.0` |
| S-07 | local-source | `cryptography` 50.0.2 — Fernet implementation | `backend/venv/Lib/site-packages/cryptography/fernet.py` | L39-51 key split; L57-84 encrypt; L129-169 verify-then-decrypt |
| S-08 | local-source | `cryptography` 50.0.2 — AEAD surface | `backend/venv/Lib/site-packages/cryptography/hazmat/primitives/ciphers/aead.py` + `.../bindings/_rust/openssl/aead.pyi` | aead.py L18 `AESGCM = rust_openssl.aead.AESGCM`; aead.pyi L9-38 `AESGCM` API |
| S-09 | local-source | `cryptography` 50.0.2 — GCM mode constraints | `backend/venv/Lib/site-packages/cryptography/hazmat/primitives/ciphers/modes.py` + `.../_modes.py` | modes.py L104-119 (`min_tag_length=16`, IV 8..128 bytes); `_modes.py` L84-93 |
| S-10 | local-source | `cryptography` 50.0.2 — KDF binding stubs | `backend/venv/Lib/site-packages/cryptography/hazmat/bindings/_rust/openssl/kdf.pyi` | L11-22 `PBKDF2HMAC`; L24-36 `Scrypt`; L38-77 `Argon2d/Argon2i/Argon2id`; L101-128 `HKDF`/`HKDFExpand` |
| S-11 | local-source | `cryptography` 50.0.2 — KDF public modules | `.../hazmat/primitives/kdf/{hkdf,scrypt,argon2}.py` | hkdf.py L10 `HKDF = rust_openssl.kdf.HKDF`; scrypt.py L16; argon2.py L10-12 |
| S-12 | local-source | `cryptography` 50.0.2 — util | `backend/venv/Lib/site-packages/cryptography/utils.py` | L54-59 `int_to_bytes(integer, length=None)` (minimal-length big-endian) |
| S-13 | local-source | `cryptography` 50.0.2 — exceptions | `backend/venv/Lib/site-packages/cryptography/exceptions.py` | L35-40 `InvalidTag`, `InvalidSignature` |
| S-14 | local-source | `cryptography` 50.0.2 — constant time | `backend/venv/Lib/site-packages/cryptography/hazmat/primitives/constant_time.py` | L10-14 `bytes_eq` → `hmac.compare_digest` |
| S-15 | local-source | `cryptography` 50.0.2 — serialization | `.../hazmat/primitives/serialization/base.py` + `_rust/openssl/keys.pyi` + `_rust/__init__.pyi` | base.py L13 `load_der_public_key`; keys.pyi L27-30 signature; `__init__.pyi` L35 `Encoding.DER`, L50 `PublicFormat.SubjectPublicKeyInfo` |
| S-16 | stdlib | Python 3.12.10 `secrets` | `C:\Users\hunther4\AppData\Local\Programs\Python\Python312\Lib\secrets.py` | L11/L17 `compare_digest`; L20 `SystemRandom`; L31 `DEFAULT_ENTROPY = 32`; L33-45 `token_bytes`; L60-71 `token_urlsafe` |
| S-17 | stdlib | Python 3.12.10 `hmac` | `...\Python312\Lib\hmac.py` | L7-15 `compare_digest` bound to `_hashlib.compare_digest`, `_operator._compare_digest` fallback |
| S-18 | stdlib | Python 3.12.10 `hashlib` | `...\Python312\Lib\hashlib.py` | L169-185 `_hashlib` / `pbkdf2_hmac`; L188-192 `from _hashlib import scrypt` ("OpenSSL's scrypt requires OpenSSL 1.1+") |
| S-19 | stdlib (machine-level) | `pycryptodomex` `DSS` signature encodings — **not** a project dependency | `...\Python312\Lib\site-packages\Cryptodome\Signature\DSS.py` | L341-356: `'binary'` = "the raw concatenation of `r` and `s` … IEEE P.1363 … always twice the length of a point coordinate (e.g. 64 bytes for P-256)"; `'der'` = "a ASN.1 DER SEQUENCE with two INTEGERs (`r` and `s`) … The size of the signature is variable" |
| S-20 | platform | Python 3.12.10 `DLLs` directory listing | `...\Python312\DLLs\` | contains `_hashlib.pyd`, `libcrypto-3.dll`, `libssl-3.dll`, `_uuid.pyd` |
| S-21 | repo | `backend/core/database.py` | `backend/core/database.py` | L20-28 PRAGMA (`journal_mode=WAL`, `busy_timeout=10000`, `foreign_keys=ON`); L30-32 `BEGIN IMMEDIATE` on the `begin` event |
| S-22 | repo | `backend/core/auth.py` | `backend/core/auth.py` | L37-80 bootstrap-once secret pattern; L93 bcrypt 72-byte guard; L99 `hmac.compare_digest`; L120-135 bypass rules |
| S-23 | repo | `backend/core/provider_keys.py` + `backend/core/settings.py` | `backend/core/provider_keys.py`, `backend/core/settings.py` | provider_keys.py L11-23 providers/env/base-URLs; L31-45 resolve/save (DB-first, plaintext); settings.py L10-29 upsert kv store |
| S-24 | repo | `backend/core/router.py` | `backend/core/router.py` | L24 `_key_cache: dict[str, str]`; L34-36 `clear_key_cache`; L39-57 provider-only accessors |
| S-25 | repo | `backend/core/limiter.py` | `backend/core/limiter.py` | L9-12 `Limiter(key_func=get_remote_address)` |
| S-26 | repo | `backend/core/timeutils.py` | `backend/core/timeutils.py` | L30-38 `to_utc_aware`; L1-15 the Windows no-IANA-tz constraint and the dependency-free fallback precedent |
| S-27 | repo | `backend/migrations/runner.py` | `backend/migrations/runner.py` | L20-24 error semantics (no `down`); L45 filename pattern; L102-142 discovery/sort/duplicate detection; L145-169 `run_migrations` |
| S-28 | repo | `backend/migrations/007_error_pattern_constraint.py` | `backend/migrations/007_error_pattern_constraint.py` | L1-8 the "SQLite cannot ALTER TABLE ADD CONSTRAINT" rationale; L43-69 CREATE-new / INSERT-SELECT / DROP / RENAME rebuild |
| S-29 | repo | `backend/requirements.txt` | `backend/requirements.txt` | L4-34; L23-24 "Seguridad: bcrypt==4.2.1" only — **no `cryptography` pin** |
| S-30 | repo | CI workflow | `.github/workflows/ci.yml` | L19-22 Python 3.11; L24-25 `pip install -r requirements.txt`; L27-31 ruff + pytest |
| S-31 | repo | venv configuration | `backend/venv/pyvenv.cfg` | L1-4 Python **3.12.10**; L2 `include-system-site-packages = false` |
| S-32 | repo | venv installed-package listing | `backend/venv/Lib/site-packages/` | `cryptography-50.0.2.dist-info/`, `cryptography/`, `cffi-2.1.1`, `pycparser-3.11` present; **no `chromadb/`**; versions diverge from S-29 (see §4 C-5) |
| S-33 | repo | `AppSetting` model | `backend/models/models.py` | L116 `class AppSetting(SQLModel, table=True)`; L123 `class UserProfile` |
| S-34 | repo | SDD project config | `openspec/config.yaml` | L20 `strict_tdd: true`; L41-44 timezone rule; L55 "Python 3.11"; L58-59 migrations 001..012; L187 design rule on `timeutils` |
| S-35 | artifact | Prior exploration for this change | `openspec/changes/multi-user-foundation/exploration.md` | §3.1, §3.3-3.4, §5.2, §6.2, §10 findings 2 and 12 |

---

## 3. Validated claims

Confidence scale: **High** = directly readable in the cited source, no
inference beyond the obvious; **Medium** = the cited source is the primary
artifact but the claim requires one inferential step; **Low** = only
circumstantial.

### 3.1 Sub-lane 1 — The ECDSA signature encoding mismatch

| id | Claim | Source | Confidence |
|---|---|---|---|
| C1.1 | `cryptography` **50.0.2 is installed** in the project venv and is the version this lane is scoped against. The dist-info directory and the package directory both exist. | S-05 (L13), S-32, S-31 | High |
| C1.2 | The complete DSS-signature-encoding surface of `cryptography` 50.0.2 is **two functions**, both bound to the Rust `asn1` module: `decode_dss_signature(signature: bytes) -> tuple[int, int]` and `encode_dss_signature(r: int, s: int) -> bytes`. | S-01 (L10-11), S-02 (L5-6) | High |
| C1.3 | **`cryptography` 50.0.2 contains no P1363 / IEEE-1363 helper.** A recursive search for `1363`, `P1363` and `ieee-p1363` across the entire installed package returns **zero matches**. There is no "raw signature" API, so the conversion cannot be avoided by delegating it to the library. | S-01, S-02 (complete public surface) + negative search over `backend/venv/Lib/site-packages/cryptography/**` | High |
| C1.4 | `EllipticCurvePublicKey.verify(signature, data, signature_algorithm)` consumes a **DER-encoded** signature. Proof from inside the package: `ssh.py:987-996` receives an SSH-format `(r, s)` pair, calls `asym_utils.encode_dss_signature(r, s)`, and only then calls `signature_key.verify(computed_sig, bytes(self._tbs_cert_body), ec.ECDSA(hash_alg))`. The re-encode would be dead code if `verify()` accepted the raw pair. | S-03 (L987-996), S-04 (L169-178) | High |
| C1.5 | The inverse holds too: `ssh.py:1582-1592` calls `private_key.sign(..., ec.ECDSA(hash_alg))` and then `r, s = asym_utils.decode_dss_signature(signature)` — i.e. `sign()` **emits DER**, and you must decode it to recover the integers. | S-03 (L1582-1592) | High |
| C1.6 | The two encodings are structurally different and different in size. P1363 (`'binary'`) is "the raw concatenation of `r` and `s`" and for ECDSA "is always twice the length of a point coordinate (e.g. 64 bytes for P-256)". DER (`'der'`) is "a ASN.1 DER SEQUENCE with two INTEGERs (`r` and `s`)" whose "size of the signature is variable". For P-256 the coordinate length is 32 bytes (`SECP256R1.key_size = 256` ⇒ 32 bytes/coord) ⇒ **P1363 is exactly 64 bytes**. | S-19 (L341-356), S-04 (L232-237) | High |
| C1.7 | **Consequence of C1.4 + C1.6:** a naive `r.to_bytes(32) + s.to_bytes(32)` produces precisely the *P1363* form (64 bytes, fixed width). It is not a DER SEQUENCE — it has no `0x30` tag, no length octets, and no INTEGER wrappers. Passing it to `verify()` fails because it is a **format** mismatch, not a length coincidence. | S-19, S-03 | High |
| C1.8 | `encode_dss_signature(r, s)` **is** the P1363→DER encoder. The exploration's statement that "cryptography ships `decode_dss_signature` (DER→P1363) but **no P1363→DER encoder**" is **incorrect**: the encoder exists and takes the two integers. What is missing is only a convenience wrapper that takes 64 raw bytes and splits it. | S-02 (L6), S-03 (L992) | High |
| C1.9 | The DER byte-level rules (SEQUENCE tag `0x30`, INTEGER tag `0x02`, minimal-length integer encoding, the leading `0x00` when the high bit of `r` or `s` is set) are **not inspectable** in the installed package: the DER writer is compiled Rust (`hazmat/asn1/asn1.py:57-58` delegates to `declarative_asn1.encode_der`), and `asn1.pyi` exposes only three functions. | S-01, S-02 + `hazmat/asn1/asn1.py` L57-58 | High (that the rules are not inspectable) |
| C1.10 | The **browser's** WebCrypto default output encoding for ECDSA is **not sourceable in this environment**: no web access, no browser runtime, and no local WebCrypto type/spec copy (`frontend/node_modules/@types/` contains only `react/` and `react-dom/`; a recursive search for `1363` across `frontend/node_modules` returns no matches; there is no `@types/node`). | Negative searches recorded in §7 G-1 | High (that it is unavailable) |
| C1.11 | SPKI public keys are parseable server-side with `serialization.load_der_public_key(data: bytes, backend=None) -> PublicKeyTypes`; `Encoding.DER` and `PublicFormat.SubjectPublicKeyInfo` exist as serialization constants. | S-15 | High |
| C1.12 | `EllipticCurvePublicKey.from_encoded_point(curve, data)` is the alternative for a raw uncompressed point; it rejects empty input and any point type outside `{0x02, 0x03, 0x04}`. | S-04 (L180-192) | High |
| C1.13 | `verify()` signals a bad signature with `cryptography.exceptions.InvalidSignature`; `InvalidTag` is the AEAD analogue. | S-13 (L35-40) | High |
| C1.14 | `cryptography.utils.int_to_bytes(integer, length=None)` is the package's own minimal-length big-endian integer encoder (`(bit_length + 7) // 8 or 1`), i.e. the same "no redundant leading zero" rule that DER requires. It is available if a hand-written encoder is ever justified — it is not needed when `encode_dss_signature` is used. | S-12 (L54-59) | High |

**Unresolved in sub-lane 1:** G-1 (browser default), G-2 (DER byte layout),
G-4 (`verify()`'s exact failure mode on malformed input), G-7 (`exportKey("spki")`
output format), G-5 (no runtime confirmation possible).

### 3.2 Sub-lane 2 — Master key handling and authenticated encryption

| id | Claim | Source | Confidence |
|---|---|---|---|
| C2.1 | `Fernet` requires a key of **exactly 32 url-safe base64-encoded bytes** and splits it into a 16-byte signing key and a 16-byte encryption key. Therefore **Fernet is AES-128-CBC + HMAC-SHA256**, not AES-256, and its 32-byte key is *not* a single 256-bit AEAD key. | S-07 (L39-51) | High |
| C2.2 | Fernet is **authenticate-then-decrypt**: `_decrypt_data` verifies the HMAC (`_verify_signature(data)`, L151) **before** performing the CBC decrypt (L156), raising `InvalidToken` on mismatch. It therefore detects tampering and truncation of the token. | S-07 (L129-135, 137-169) | High |
| C2.3 | Fernet is **not an AEAD**: it has no associated-data parameter, no separate nonce/IV contract (the IV is 16 random bytes per encryption, `os.urandom(16)`, L61), and its key material is split into two independent halves. It additionally embeds a timestamp and enforces a TTL plus a 60-second clock-skew window when a TTL is supplied. | S-07 (L25, 60-84, 143-149) | High |
| C2.4 | `AESGCM` is available in 50.0.2 with API `AESGCM(key)`, `AESGCM.generate_key(bit_length)`, `encrypt(nonce, data, associated_data)`, `decrypt(nonce, data, associated_data)`. **The nonce is supplied by the caller** — the library never generates it, and therefore never rotates it either. | S-08 | High |
| C2.5 | The AEAD API's Python-visible surface does **not** constrain the nonce length or the tag length (the stub shows only `Buffer` parameters). Contrast the low-level `modes.GCM`, which enforces `8 <= len(iv) <= 128` bytes and `min_tag_length=16`. **A 12-byte-nonce rule is therefore ours to enforce and to test**, not the library's. | S-09, S-08 | High |
| C2.6 | `cryptography` 50.0.2 ships **HKDF** (extract + expand), **Scrypt**, **PBKDF2HMAC** *and* **Argon2d / Argon2i / Argon2id**. Argon2 is available in this version. | S-10, S-11 | High |
| C2.7 | The exact HKDF call is `HKDF(algorithm: HashAlgorithm, length: int, salt: bytes | None, info: bytes | None).derive(key_material: Buffer) -> bytes`, with `HKDF.extract(algorithm, salt, key_material)` as a static method. | S-10 (L101-116), S-11 | High |
| C2.8 | `hashlib.scrypt` is available in the standard library through `_hashlib` ("OpenSSL's scrypt requires OpenSSL 1.1+"), and this host has `_hashlib.pyd` and `libcrypto-3.dll` present — so the scrypt code path is importable on this Windows machine. | S-18 (L188-192), S-20 | High |
| C2.9 | `secrets.token_bytes(n)` draws from `SystemRandom.randbytes` (i.e. the OS CSPRNG) and `secrets.token_urlsafe(n)` returns URL-safe base64 without padding; `DEFAULT_ENTROPY = 32`. Producing a 32-byte machine-generated master key needs no third-party dependency. | S-16 (L20, 31, 33-45, 60-71) | High |
| C2.10 | Constant-time comparison is available three ways: `hmac.compare_digest`, `secrets.compare_digest` (a re-export, S-16 L11/L17), and `cryptography.hazmat.primitives.constant_time.bytes_eq` (a thin wrapper over `hmac.compare_digest`). | S-16, S-17, S-14 | High |
| C2.11 | On this platform `hmac.compare_digest` is bound to OpenSSL's `_hashlib.compare_digest` (the `_operator` fallback branch is only taken when `_hashlib` cannot be imported), and `_hashlib.pyd` + `libcrypto-3.dll` are present. **The Windows "no IANA tz database" class of platform gap does not apply to constant-time comparison or to OS entropy** — the two platform risks that the project actually has are timezone data (S-26) and the venv/requirements drift (§4 C-5). | S-17 (L7-15), S-20 | High |
| C2.12 | The repository already establishes "bootstrap a secret once" as a convention: `LazyAPIKeyManager.initialize()` prefers `PEAK_API_KEY`, then the `api_key_hash` DB row, then generates a random 32-hex-char key and stores it, logging only a masked prefix. | S-22 (L37-80) | High |
| C2.13 | Provider keys are currently **global and plaintext** in `AppSetting` rows `provider_key_{groq,openrouter,generalcompute}`, resolved DB-first then env-var, and the whole router reads them through a module-level cache keyed by provider only. | S-23, S-24, S-33 | High |
| C2.14 | The router's `_key_cache` is cleared at the start of every `execute_with_router` call, so it provides no benefit and is a pure cross-user leak surface once keys become per-user. | S-24 (L24, 34-36, 39-57) + S-35 (`exploration.md:648-656`) | High |
| C2.15 | **Derived consequence (not a library fact).** AES-GCM is a deterministic-key AEAD: the only inputs are the master key and the per-write nonce. There is no escrow, no key-wrapping chain and no re-derivation path for a random 256-bit key. **Losing the master key makes every stored credential permanently undecryptable.** The master key must therefore be backed up, and the proposal's rollback plan must say so. | S-08 (AEAD API surface) + S-16 (key generation) | Medium-High |

**Unresolved in sub-lane 2:** G-3 (AEAD nonce/tag policy in the AEAD API),
G-6 (Linux wheel availability for CI), G-5 (no runtime confirmation).

### 3.3 Sub-lane 3 — Challenge/response with replay protection

| id | Claim | Source | Confidence |
|---|---|---|---|
| C3.1 | Every transaction on the project engine opens with `BEGIN IMMEDIATE` (SQLAlchemy `begin` event), alongside `journal_mode=WAL`, `busy_timeout=10000` and `foreign_keys=ON`. | S-21 (L20-32) | High |
| C3.2 | **Consequence of C3.1:** because `BEGIN IMMEDIATE` acquires the SQLite write lock *at transaction start*, a transaction that reads a challenge row and then marks it consumed serializes against every other writer. A second concurrent verifier blocks at `BEGIN` (up to the 10 s busy timeout), and when it proceeds its read observes the committed `consumed_at`. The check-then-consume is therefore atomic **if and only if both statements run in the same transaction**. | S-21 (L24, 30-32) | High |
| C3.3 | `secrets.token_urlsafe(32)` returns 32 random bytes (256 bits) as URL-safe base64 without padding — 43 characters — which survives JSON transport unchanged and is safe in a URL or a header. | S-16 (L31, 60-71) | High |
| C3.4 | Constant-time comparison of a presented bearer token against a stored value is available via `hmac.compare_digest` / `secrets.compare_digest` / `constant_time.bytes_eq`. | S-16, S-17, S-14 | High |
| C3.5 | For a 256-bit random session token the correct lookup primitive is a **fast** hash (`hashlib.sha256`), not a slow KDF: the token is already full-entropy, so a KDF buys nothing and would add cost to *every* request. The repository's existing constant-time idiom is `hmac.compare_digest` over a candidate hash (`core/auth.py:99`), but that candidate is produced by **bcrypt**, a password KDF — the wrong tool for a random token. | S-22 (L93-101), S-16, S-18 | High |
| C3.6 | Every timestamp comparison must go through `core/timeutils.to_utc_aware`; SQLite stores naive datetimes and mixing naive and aware values raises `TypeError`. This is a project-level rule, not a preference. | S-26 (L1-38), S-34 (L41-44, 187) | High |
| C3.7 | The existing rate limiter is `slowapi.Limiter(key_func=get_remote_address)` — **per remote address, not per account**. A challenge endpoint keyed per-IP can still be used to enumerate/hammer a single account from many addresses, and a single NAT address can exhaust the limit for many users. | S-25 (L9-12) | High |
| C3.8 | The migration contract has **no `down()`**: the runner discovers `00N_*.py`, sorts by `version`, and calls only `up`; exceptions propagate and abort startup. Consequence: a schema change to the challenge table is rolled back only by restoring a database backup, never by a reverse migration. | S-27 (L20-24, 102-142, 145-169) | High |
| C3.9 | The next free migration versions are **013, 014, 015** — `001`…`012` are present in `backend/migrations/`. | `backend/migrations/` listing + S-27 (L45) | High |
| C3.10 | The in-repo precedent for reshaping a SQLite table (e.g. changing a constraint on the challenge table) is migration 007's `CREATE TABLE ..._new` → `INSERT ... SELECT` → `DROP` → `ALTER TABLE ... RENAME` rebuild, adopted because "SQLite does not support ALTER TABLE ADD CONSTRAINT". | S-28 (L1-8, 43-69) | High |
| C3.11 | A challenge must be **single-use and bound to device and session** for three independent reasons, each grounded above: (a) single-use is enforced by the `consumed_at IS NULL` predicate evaluated inside the write-locked transaction (C3.1/C3.2); (b) binding to the device means the verified device row is the one whose key the signature was checked against, so a signature for device A cannot be redeemed against device B's enrolment (C1.4); (c) binding to the session means a signature captured for challenge X cannot be replayed against challenge Y, because the signed message contains the server-generated challenge id and nonce (C3.3). | S-21, S-03, S-16 | High |
| C3.12 | The role of the nonce and the timestamp: the **nonce** makes every challenge unique and unpredictable even for the same user at the same second (C3.3); the **timestamp** (`expires_at`) bounds the window in which a captured challenge is still redeemable (C3.6). The `expires_at > now` predicate and the `consumed_at IS NULL` predicate are two different, non-substitutable conditions: one limits *time*, the other limits *count*. | S-21, S-16, S-26 | High |

**Unresolved in sub-lane 3:** G-5 (no runtime confirmation of the transaction
behaviour under real concurrency). Everything else is sourced.

### 3.4 Sub-lane 4 — Key rotation and revocation semantics

| id | Claim | Source | Confidence |
|---|---|---|---|
| C4.1 | Revocation is a **schema + transaction** concern, not a cryptographic one: a `revoked_at` timestamp on the device row and on every session row bound to that device, updated in one transaction. `BEGIN IMMEDIATE` (S-21) is what makes "revoke the device and its sessions" atomic rather than a two-step race. | S-21 (L30-32) | High |
| C4.2 | **Rotation must not silently invalidate an enrolled device.** The rotation precondition is a *live session bound to that device* — i.e. the caller has already proved possession of the private key by authenticating with it. Rotation then (a) replaces the stored public key, (b) bumps `key_epoch`, (c) revokes that device's sessions, and (d) requires a fresh challenge to obtain a new session. The new key is therefore re-proved, and the old key stops working for an explicit, auditable reason. | S-35 (`exploration.md:384-393`) + S-21 | High |
| C4.3 | Proving possession of the **old** key is the wrong precondition: it proves nothing beyond what the new key will prove, and it fails exactly in the lost-device case that rotation is supposed to survive. | S-35 (`exploration.md:391`) | High |
| C4.4 | A signature made with a retired key is rejected **by construction**: verification resolves the device by `(user_id, public_key)` against the *current* stored public key, so after rotation the retired public key matches no row. `key_epoch` is therefore an **auditability** column, not a correctness requirement. | S-35 (`exploration.md:393`) + S-15 (public key lookup by bytes) | High |
| C4.5 | "Add a device" and "rotate a device's key" are different operations with different preconditions and different blast radius; conflating them is what would allow a rotation to silently de-register an enrolled device. | S-35 (`exploration.md:384-389`) | High |
| C4.6 | Revoking a device must not delete user data: the data lives on the server keyed by `user_id`, not by device, so revocation is a credential-scoped event only. | S-35 (`exploration.md:395-401`) | High |

**Unresolved in sub-lane 4:** none. The whole sub-lane is a design-semantics
question, and it is fully determined by the repository's transaction
discipline plus the exploration's already-established device model.

---

## 4. Contradictions with existing artifacts

| id | Existing claim | Verified reality | Impact |
|---|---|---|---|
| **C-5** | `exploration.md:104` and `exploration.md:1051` (finding 2): "`cryptography` is not installed in `backend/venv` (verified: no `backend/venv/Lib/site-packages/cryptography`)". | **False as of 2026-10-22.** `backend/venv/Lib/site-packages/cryptography/` and `cryptography-50.0.2.dist-info/` both exist; `__about__.py:13` = `"50.0.2"`. The exploration's verification method was the `glob` tool, which does not traverse the gitignored virtualenv (§0 method note). | The "add `cryptography` to `requirements.txt`" task is still required (C-5b), but the claim "it is not installed" must be struck from the proposal's premise. |
| **C-6** | `exploration.md:359`: "`cryptography` ships `utils.decode_dss_signature` (DER→P1363) but **no P1363→DER encoder**". | **Wrong.** `encode_dss_signature(r: int, s: int) -> bytes` **is** the P1363→DER encoder (`asn1.pyi:6`); the package itself uses it to convert a raw `(r, s)` pair into the form `verify()` accepts (`ssh.py:992-996`). What is absent is only a bytes-in convenience wrapper. | **Changes the implementation plan.** The hand-written 15-line `p1363_to_der` recommended at `exploration.md:360` is unnecessary and re-introduces the exact bug the exploration warned about. |
| **C-7** | `exploration.md:360`: "Server-side conversion — hand-written `p1363_to_der(raw: bytes) -> bytes` (~15 lines) … Emits `0x30 len 0x02 len r 0x02 len s` with minimal integer encoding." | Superseded by C1.8. The library already performs the minimal-length/leading-zero handling correctly (and its implementation is compiled Rust, so the byte rules are not even inspectable locally). | The design must **not** hand-roll DER. This removes a whole class of defect from the highest-risk item. |
| **C-8** | `exploration.md:1051` and `openspec/config.yaml:55` describe the environment as Python 3.11 with pinned versions (`fastapi 0.115.6`, `bcrypt 4.2.1`, `pytest 8.3.4`, `sqlmodel 0.0.22`, `pydantic 2.10.4`, `ruff 0.8.6`, `openai 1.58.1`, `groq 1.4.0`, `uvicorn 0.34.0`, `python-multipart 0.0.19`, `python-dotenv 1.0.1`, `slowapi 0.1.9`, `pytest-cov 6.0.0`) and `chromadb 0.6.3`. | The local venv is **Python 3.12.10** (`pyvenv.cfg:1-3`) and its installed versions **diverge** from `requirements.txt` on every one of those pins (installed: fastapi 0.141.1, bcrypt 5.0.0, pytest 9.1.1, sqlmodel 0.0.42, pydantic 2.13.5, ruff 0.16.6, openai 3.8.0, groq 1.7.0, uvicorn 0.52.4, python-multipart 0.0.32, python-dotenv 1.2.3, slowapi 0.1.10, pytest-cov 7.1.0). **`chromadb` is absent from the venv entirely** although `requirements.txt:14` pins it. `cryptography` is present but **not pinned** in `requirements.txt`. | Two consequences. (a) The venv is **not reproducible** from `requirements.txt`; the "testing capabilities" snapshot describes CI, not this machine, and the venv cannot be used to infer CI behaviour. (b) **CI installs from `requirements.txt` (`ci.yml:24-25`), so `cryptography` is missing in CI** — any new test that imports it fails in CI while passing locally. Pinning `cryptography==50.0.2` in `requirements.txt` is a hard prerequisite, not an optimisation. |
| **C-9** | `exploration.md:423`: "Current PyPI stable is 50.0.2 (`requires_python >=3.9`, so Python 3.11 is satisfied)." | The `requires_python` half is **confirmed**: `cryptography-50.0.2.dist-info/METADATA:36` reads `Requires-Python: >=3.9, !=3.9.0, !=3.9.1`, so CI's Python 3.11 (`ci.yml:19-22`) is satisfied. The "current PyPI stable" half is a web claim I could not verify and do not restate. | Pin `cryptography==50.0.2`; the Python-version constraint is confirmed. The "latest on PyPI" framing should be dropped. |
| **C-10** | `exploration.md:1051` and `exploration.md:423` both treat "cryptography not installed" as a *discovery*. | It is now a **stale observation**, not a discovery. The proposal must be written against the current tree. | Proposal wording. |

---

## 5. Uncertainty and freshness

- **Freshness.** Every source in §2 was read on 2026-10-22 from the working
  tree as it stands, which carries pre-existing uncommitted WIP
  (`openspec/config.yaml:49-51`). No file under `backend/` or `frontend/` was
  modified by this phase; the only file created is this artifact.
- **No runtime verification was possible.** This phase had no shell/process
  execution capability, so every claim is static source inspection. Claims
  that *require* execution are listed in §7 (G-3 … G-7) rather than asserted.
  The most consequential ones are G-4 (does `verify()` raise `InvalidSignature`
  or `ValueError` on a malformed signature?) and G-6 (does a cp311 manylinux
  wheel of `cryptography==50.0.2` exist? — a local Windows install says
  nothing about the Linux wheel CI will download).
- **Compilation boundary.** A large part of `cryptography` 50.0.2 is a compiled
  Rust extension (`hazmat/bindings/_rust/*.pyd`). Where a behaviour lives
  there — DER byte layout, AEAD nonce policy, `verify()`'s failure mode — it
  is not inspectable from Python source, and I have said so rather than
  guessing.
- **One source is machine-level, not project-level.** S-19
  (`Cryptodome/Signature/DSS.py`) lives in the **global** Python
  site-packages. The project venv is isolated (`pyvenv.cfg:2`,
  `include-system-site-packages = false`), so `Cryptodome` is **not importable
  by the project** and must never become a dependency. It is used here solely
  as a locally-inspectable *definition* of what "P1363" and "DER" mean; the
  same directory also contains `jwt` (PyJWT), which is likewise unavailable to
  the project and must not be assumed.
- **Confidence distribution.** 32 of 38 claims are **High** confidence, 5 are
  **Medium-High**, 0 are Low, and 8 questions are **unsupported** (§7) — all of
  them closed by a specific, named piece of evidence rather than by a vague
  "consult the docs".

---

## 6. Implementation consequences

### 6.1 Sub-lane 1 — Signature encoding

**DO**

- Normalize the signature **server-side, in one function**, before it ever
  reaches `verify()`:
  1. `len(raw) == 64` → treat as P1363: `r = int.from_bytes(raw[:32], "big")`,
     `s = int.from_bytes(raw[32:], "big")` → `encode_dss_signature(r, s)`.
  2. otherwise → `decode_dss_signature(raw)` → `(r, s)` → re-emit with
     `encode_dss_signature(r, s)` (this both validates and canonicalises).
  3. anything else → raise a typed `InvalidSignatureFormat` that **names the
     byte count** ("expected a 64-byte IEEE P1363 signature or a DER-encoded
     ECDSA signature, got N bytes"), never a bare 401.
- Verify with `pub.verify(der, message, ec.ECDSA(hashes.SHA256()))` and catch
  `cryptography.exceptions.InvalidSignature` (defensively `ValueError` too).
- Parse the enrolled key with `serialization.load_der_public_key(spki_der)`, then
  assert `isinstance(key, ec.EllipticCurvePublicKey)`, `key.curve.name == "secp256r1"`,
  `key.key_size == 256`. Reject anything else with a 400 naming the reason.
- Unit test (T-17) with four cases: a known (r, s) vector → expected DER bytes;
  a 64-byte P1363 blob → equals the DER form of the same (r, s);
  `decode_dss_signature(encode_dss_signature(r, s)) == (r, s)`; and a
  truncated/over-long input → the typed error, not a 500.

**DO NOT**

- Do **not** hand-roll a DER writer (`b"\x30" + len + b"\x02" + …`). The
  library already implements minimal-length and leading-zero correctly;
  hand-rolling reintroduces the very trap this sub-lane exists to close.
- Do **not** pass a P1363 blob to `verify()` directly, and do **not** assume
  the browser emits P1363 — branch on length and cover both branches in tests.
- Do **not** use `decode_dss_signature` as the *input* path for a 64-byte blob.
- Do **not** use `from_encoded_point` unless the public key format is changed to
  a raw point — SPKI is the chosen format (C1.11).

### 6.2 Sub-lane 2 — Master key and authenticated encryption

**DO**

- Use **AES-256-GCM** (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`).
  Not Fernet: Fernet is AES-128 with a *separate* HMAC key (C2.1), has no AAD
  (C2.3) and is a token format, not a blob format.
- Master key: **32 random bytes** from `secrets.token_bytes(32)`, carried in
  `PEAK_MASTER_KEY` base64-encoded. Validate at load: decode, require exactly
  32 bytes, otherwise fail startup with a clear message. Use a **version
  prefix** in the stored value (e.g. `v1:<base64>`) so a future format change
  is detectable — this is *our* convention, not a library requirement.
- Derive a **domain-separated subkey**:
  `HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"peak/user-provider-key/v1").derive(master_key)`.
  The master key is then never used directly for encryption and cannot be
  reused for another purpose.
- Nonce: 12 bytes from `secrets.token_bytes(12)` per encryption, stored as the
  blob prefix. **Enforce the 12-byte length in our code** — the AEAD API does
  not (C2.5).
- AAD: bind `f"{user_id}:{provider}".encode()` so a ciphertext cannot be
  replayed against a different user or provider.
- Blob layout: `nonce(12) || ciphertext || tag(16)` (the tag is appended by
  `AESGCM.encrypt`).
- Fail loud: catch `cryptography.exceptions.InvalidTag` → a typed
  `CredentialDecryptionError`; never fall back to another user's key, never
  return a partial key, never surface the raw exception to the client.
- Master-key-absent behaviour mirrors the repo's existing precedent
  (`core/auth.py:37-80`): generate-and-persist in development, refuse to start
  under `PRODUCTION=1`.
- **State the backup requirement in the proposal and the design**: loss of the
  master key = permanent, unrecoverable loss of every stored credential
  (C2.15). Add it to the rollback plan.
- Delete `_key_cache`, `clear_key_cache` and the three provider-only accessors
  (`router.py:24, 34-36, 39-57`); resolve per-user at call time (C2.14).

**DO NOT**

- Do **not** use Fernet for provider keys.
- Do **not** run PBKDF2 / scrypt / Argon2 over a 32-byte machine-generated
  master key. A KDF defends low-entropy passphrases; against a random key it
  adds latency and removes nothing. HKDF here is *domain separation*, not
  password hardening — the design must say so, or a future contributor will
  "helpfully" add a KDF.
- If the owner insists on a passphrase master key, the supported alternative is
  `Scrypt(salt, length, n, r, p)` or `Argon2id` (both available in 50.0.2,
  C2.6) with a per-deployment random salt stored beside the ciphertext — but
  that is an **alternative path, not the default**.
- Do **not** derive the encryption key straight from the master key with no
  `info` label.
- Do **not** reuse a nonce under the same key. `secrets.token_bytes(12)` per
  write makes accidental reuse negligible; a counter is preferable if one key
  ever encrypts more than ~2^32 values.
- Do **not** keep a plaintext fallback for stored provider keys.
  The resolution order is: the caller's own encrypted key → the system
  credential (env var or legacy `provider_key_*` row) → nothing. The source
  must be reported to the client (`"user" | "system"`), never silent.

### 6.3 Sub-lane 3 — Challenge consumption

**DO**

- Challenge row: `id` (uuid4 hex), `user_id`, `device_id`, `nonce`
  (`secrets.token_urlsafe(32)`), `created_at`, `expires_at`, `consumed_at`,
  `attempts`. TTL 300 s. `expires_at`/`consumed_at` written as UTC-aware
  values and compared through `core/timeutils.to_utc_aware` (C3.6).
- Signed message: a canonical, domain-separated, newline-delimited string
  binding protocol version, challenge id, nonce, email and deployment origin.
  The canonicalisation must be byte-exact on both sides.
- **The consumption protocol (exact order, one transaction):**
  1. Open **one** `Session` — one transaction, one commit.
  2. `SELECT … FROM auth_challenges WHERE id = :cid AND consumed_at IS NULL AND expires_at > :now` → no row ⇒ 401.
  3. `SELECT … FROM user_devices WHERE id = :did AND user_id = :uid AND revoked_at IS NULL` → no row ⇒ 401.
  4. Normalize the signature to DER and `verify()` it → failure ⇒ 401 and increment `attempts`.
  5. `UPDATE auth_challenges SET consumed_at = :now WHERE id = :cid AND consumed_at IS NULL` → **assert `rowcount == 1`**, else 401.
  6. `INSERT INTO auth_sessions (…, token_hash = sha256(token).hexdigest(), …)`.
  7. Commit.
  - Atomicity comes from `BEGIN IMMEDIATE` (C3.1/C3.2): the write lock is taken
    at `BEGIN`, so a concurrent verifier blocks and then observes the committed
    `consumed_at`; its step 2 returns no row. **Exactly one session per
    challenge.**
- Session token: `secrets.token_urlsafe(32)` (43 chars, 256 bits), stored as
  `sha256(token).hexdigest()`; compare with `hmac.compare_digest` /
  `secrets.compare_digest` (C3.3, C3.4).
- Bound the session: sliding `expires_at` plus an absolute `absolute_expires_at`;
  both compared via `to_utc_aware`.
- Rate-limit `/api/auth/challenge` and `/api/auth/verify` with the existing
  slowapi limiter, and note explicitly that it is **per-IP** (C3.7) — a
  per-normalised-email key function is an addition, not something the current
  limiter already provides.

**DO NOT**

- Do **not** consume the challenge in a different transaction from the session
  insert. Two `Session`s reintroduce the race that `BEGIN IMMEDIATE` was there
  to close.
- Do **not** keep challenges in an in-memory dict — the app may run with more
  than one uvicorn worker.
- Do **not** use a JWT. No JWT library is available to the project (the
  globally-installed `jwt` is invisible to the isolated venv, `pyvenv.cfg:2`),
  and revocation needs a database row either way.
- Do **not** let a failed verification leave a challenge open forever — bound
  `attempts` and/or let it expire.
- Do **not** log the nonce; the challenge id is the loggable handle.
- Do **not** call `zoneinfo.ZoneInfo` for TTL arithmetic (project rule).

### 6.4 Sub-lane 4 — Rotation and revocation

**DO**

- Rotate as: **live session bound to that device** + new SPKI public key →
  in one transaction: replace `user_devices.public_key`, bump `key_epoch`,
  revoke that device's sessions, write an audit row. The new key must then
  re-prove possession through a fresh challenge.
- Revoke as: `revoked_at` on the device row **and** on every session bound to
  that device, in one transaction (C4.1).
- Keep `key_epoch` for auditability, not correctness (C4.4).
- Keep "add a device" and "rotate a device's key" as separate operations with
  separate preconditions (C4.5).
- Revoking a device must not touch the user's data (C4.6).

**DO NOT**

- Do **not** let a rotation silently invalidate an enrolled device without an
  explicit, audited action and re-proof of possession.
- Do **not** implement rotation as "accept the new public key from an
  unauthenticated request" — that is an enrollment.
- Do **not** require proof of the **old** key as the rotation precondition
  (C4.3): it proves nothing beyond what the new key will prove and fails in
  exactly the lost-device case.
- Do **not** hard-delete the device row on revocation — keep it for the audit
  trail.

---

## 7. Gaps and unsupported claims

Every item below is a claim I **did not make**, with the exact evidence that
would close it.

| id | Unsupported claim / open question | Why it could not be closed | Exact evidence that closes it |
|---|---|---|---|
| **G-1** | "The browser's WebCrypto `ECDSA` `sign()` produces an IEEE P1363 `r‖s` signature by default." | No web access, no browser runtime, no local WebCrypto specification or type definitions (`frontend/node_modules/@types/` holds only `react/` and `react-dom/`; a recursive search for `1363` across `frontend/node_modules` returns nothing; no `@types/node`). | (a) The W3C WebCrypto specification's `ECDSA` algorithm section; **or** (b) one browser run asserting `sig.length === 64` and `sig[0] !== 0x30`; **or** (c) one Node 22 run of `globalThis.crypto.subtle.sign({name:"ECDSA", hash:"SHA-256"}, …)` asserting the same two facts. |
| **G-2** | The exact DER byte layout: SEQUENCE tag `0x30`, INTEGER tag `0x02`, minimal-length encoding, and the leading `0x00` when the high bit of `r` or `s` is set. | The DER writer is compiled Rust (`hazmat/asn1/asn1.py:57-58` → `declarative_asn1.encode_der`); `asn1.pyi` exposes only three functions. | X.690 §8/§10 text (web), or the `cryptography` Rust source. **Not needed** if the recommendation in §8 R1 is followed — the rule is to never hand-roll DER. |
| **G-3** | The nonce-length range and minimum tag length that the **AEAD** `AESGCM` class accepts and enforces. | Enforced in the Rust layer; the Python stub (`aead.pyi:13-24`) shows no constraint, unlike `modes.GCM` (`modes.py:104-119`). | The `cryptography` Rust source, or the API reference for the AEAD class. **Mitigation without it:** enforce 12 bytes ourselves and test it (C2.5). |
| **G-4** | Whether `EllipticCurvePublicKey.verify()` raises `InvalidSignature` or `ValueError` when handed a malformed (non-DER) signature. | Rust layer; the docstring says only "Verifies the signature of the data." (`ec.py:176-178`). | One runtime call. **Mitigation without it:** catch both, and normalize/validate the signature bytes *before* calling `verify()` so malformed input never reaches the library. |
| **G-5** | Runtime confirmation of every behavioural claim in this artifact. | This phase had no shell/process execution capability; all evidence is static source inspection. | One `backend/venv/Scripts/python.exe -c "…"` per sub-lane asserting: (a) `encode_dss_signature`/`decode_dss_signature` round-trip; (b) a 64-byte P1363 blob is rejected by `verify()` while the DER form of the same (r, s) is accepted; (c) `AESGCM` round-trip and `InvalidTag` on a flipped bit; (d) `hashlib.scrypt` imports; (e) `hmac.compare_digest` is present and is the OpenSSL-backed one; (f) two concurrent challenge verifications yield exactly one session. |
| **G-6** | That a cp311 manylinux wheel of `cryptography==50.0.2` exists for the CI runner. | The local install is a Windows cp312 wheel; a local Windows wheel proves nothing about the Linux artifact CI downloads. | `pip download cryptography==50.0.2 --only-binary=:all: --python-version 3.11 --platform manylinux_2_28_x86_64` executed on CI, or the first CI run after the pin lands. |
| **G-7** | That `crypto.subtle.exportKey("spki")` yields an SPKI DER blob. | Same class as G-1 — browser-side behaviour, no local source. | Same as G-1. **Mitigation without it:** the server accepts SPKI via `load_der_public_key` and rejects anything else with a clear 400; the server-side unit test builds its SPKI fixture with `cryptography`'s own `public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)`, so the server side is fully covered regardless. |
| **G-8** | That the S-19 wording for "IEEE P.1363" and "ASN.1 DER SEQUENCE with two INTEGERs" is authoritative. | S-19 is a machine-level third-party package (not a project dependency, not in the venv), used only as a locally-inspectable definition. | IEEE P1363 and X.690 primary documents (web). **Mitigation without it:** the *behavioural* facts this lane depends on — that `verify()` needs DER and that `encode_dss_signature` produces it — are proven directly from the installed `cryptography` (C1.4, C1.5, C1.8) and do not depend on S-19. |

**Severity.** G-1 and G-7 are the only two that touch a *browser-side*
assumption, and the §6.1 and §6.2 "DO" lists are written so that neither
assumption is load-bearing. G-6 is the only one that can break CI outright,
and it is closed by the first CI run after the pin is added.

---

## 8. Recommendations consumed by the proposal and the design phase

These are **evidence-backed recommendations**, not product decisions. The
proposal and design phases may adopt them, and must record any deviation.

### R1 — Exact signature-encoding approach

```
raw bytes
  ├─ len == 64  → r = int.from_bytes(raw[:32],"big"); s = int.from_bytes(raw[32:],"big")
  │                 der = encode_dss_signature(r, s)          # P1363 → DER
  └─ otherwise  → (r, s) = decode_dss_signature(raw)           # DER → (r,s)
                    der = encode_dss_signature(r, s)            # re-emit, canonical
                        (a parse failure ⇒ typed InvalidSignatureFormat naming N)
verify: pub.verify(der, message, ec.ECDSA(hashes.SHA256()))
```

- API: `from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature`
- **Rule: never hand-roll DER.** The library's `encode_dss_signature` already
  performs the minimal-length and leading-zero handling.
- **Rule: do not depend on the browser's default encoding.** Branch on length;
  test both branches. (G-1)
- Public key: `serialization.load_der_public_key(spki_der)` → assert
  `EllipticCurvePublicKey`, `curve.name == "secp256r1"`, `key_size == 256`.

### R2 — Exact encryption primitive and key-handling rule

| Aspect | Rule |
|---|---|
| Primitive | `AESGCM` (AES-256-GCM), `cryptography.hazmat.primitives.ciphers.aead` |
| Master key | 32 bytes from `secrets.token_bytes(32)`; `PEAK_MASTER_KEY` base64; stored value prefixed `v1:`; validated to be exactly 32 bytes at load; never logged |
| Subkey | `HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"peak/user-provider-key/v1").derive(master_key)` — domain separation, **not** password hardening |
| KDF over the master key | **None.** Not PBKDF2, not scrypt, not Argon2. (Alternative path if the owner insists on a passphrase: `Scrypt` or `Argon2id` with a stored per-deployment salt.) |
| Nonce | 12 bytes from `secrets.token_bytes(12)` per encryption, stored as the blob prefix; length enforced by our code |
| AAD | `f"{user_id}:{provider}".encode()` |
| Blob | `nonce(12) ‖ ciphertext ‖ tag(16)` |
| Error handling | `InvalidTag` → typed `CredentialDecryptionError`; loud, safe message, no fallback to another key, no partial key |
| Key absent | dev: generate and persist (gitignored, mirroring `core/auth.py:37-80`); production: refuse to start |
| **Operational** | **The master key MUST be backed up. Loss of it = permanent loss of every stored credential** (no escrow, no re-derivation of a random key). State this in the proposal's rollback plan. |
| Not used | Fernet (AES-128 + separate HMAC key, no AAD — C2.1, C2.3) |

### R3 — Exact challenge consumption protocol

```
BEGIN (implicit; BEGIN IMMEDIATE via the engine 'begin' event — one transaction)
  1  SELECT auth_challenges WHERE id=:cid AND consumed_at IS NULL AND expires_at > :now
       └─ no row → 401   (covers unknown id, expired, already used)
  2  SELECT user_devices  WHERE id=:did AND user_id=:uid AND revoked_at IS NULL
       └─ no row → 401
  3  der = normalize_to_der(signature_b64)     # R1
     pub.verify(der, canonical_message, ec.ECDSA(hashes.SHA256()))
       └─ InvalidSignature → 401 (+ increment attempts)
  4  UPDATE auth_challenges SET consumed_at=:now WHERE id=:cid AND consumed_at IS NULL
       └─ rowcount != 1 → 401  (lost the race; exactly one winner)
  5  INSERT auth_sessions (user_id, device_id, token_hash=sha256(token).hexdigest(),
                           created_at, last_seen_at, expires_at, absolute_expires_at)
COMMIT
```

- `nonce = secrets.token_urlsafe(32)`; TTL 300 s; all time comparisons through
  `core/timeutils.to_utc_aware`.
- Session token = `secrets.token_urlsafe(32)`; stored as `sha256` hex; compared
  with `hmac.compare_digest` / `secrets.compare_digest`.
- **One transaction, one commit.** The `UPDATE ... WHERE consumed_at IS NULL`
  plus the `rowcount == 1` assertion is the second line of defence behind
  `BEGIN IMMEDIATE`; keep both.
- Rate-limit both endpoints; note the existing limiter is **per-IP**.

### R4 — Dependency and environment prerequisite

- Add `cryptography==50.0.2` to `backend/requirements.txt` under "Seguridad".
  **Without it CI has no `cryptography` at all** (CI installs from
  `requirements.txt`, `ci.yml:24-25`) and every new crypto test fails in CI
  while passing locally.
- The `cryptography` 50.0.2 wheel requires `cffi>=2.0.0` (METADATA:26) and
  `typing-extensions>=4.13.2` on Python < 3.11 (METADATA:27) — the latter does
  not apply to CI's 3.11. `cffi` and `pycparser` are already present in the
  local venv, and neither conflicts with the current dependency set.
- The local venv diverges from `requirements.txt` on every pin and lacks
  `chromadb` (§4 C-8). Treat the venv as a working environment, **not** as the
  CI environment, and do not read CI behaviour off it.

---

## 9. Product choices — non-authoritative, not evidence

This lane informs but does **not** decide the following; they remain owner
decisions (see `exploration.md` §8 for the full D-1 … D-10 set). The crypto
lane constrains *how* each may be implemented, not *whether*:

- **D-1 / D-2** — enrollment gate and user-enumeration behaviour. Crypto
  constraint: the challenge endpoint must return an indistinguishable response
  shape for an unknown email (D-2 option b) — a "404 user not found" is a
  cryptographic-oracle-free choice but an enumeration oracle, and that trade is
  the owner's.
- **D-3** — recovery when every device is lost. Crypto constraint: a recovery
  secret, if chosen, is a *second* secret to protect and lose; bcrypt is the
  right primitive for it (low entropy), unlike the session token (C3.5).
- **D-4 / D-7** — whether the legacy shared API key survives as a machine
  credential. Crypto constraint: the admin path must not be reachable from a
  browser, and the frontend must stop embedding `VITE_PEAK_API_KEY`.
- **D-5** — whose credential pays when a user has no key of their own. Crypto
  constraint: the fallback must be explicit (`"source": "user" | "system"`) and
  must never be a silent per-user substitution.
- **D-6** — how the owner's existing plaintext provider keys move into the
  encrypted store. Crypto constraint: the migration command is the only place
  where plaintext is read, and it must delete the plaintext row in the same
  operation.

---

## Key Learnings

1. The installed `cryptography` 50.0.2 already provides the P1363-to-DER encoder through `encode_dss_signature`, so a hand-rolled DER writer is unnecessary and would reintroduce the minimal-length and leading-zero defects the design was meant to avoid.
2. The `glob` tool does not traverse the gitignored `backend/venv` directory, which is why an earlier artifact in this change wrongly concluded that the `cryptography` package was absent; `read` and `grep` on an explicit path do traverse it.
3. The `cryptography` package proves internally that `EllipticCurvePublicKey.verify` requires a DER signature, because its own SSH certificate path must re-encode a raw `(r, s)` pair before calling `verify`.
4. The project virtual environment has drifted from `requirements.txt` on every pin and lacks `chromadb`, so the local environment cannot be used to infer CI behaviour, and `cryptography` must be pinned before any crypto test can pass in CI.
5. The `BEGIN IMMEDIATE` transaction event is what makes single-use challenge consumption atomic, but only when the check and the consume share a single transaction and a single commit.
6. Fernet is AES-128 with a separate HMAC key and no associated data, so it is not an acceptable substitute for a single 256-bit AEAD key when sealing per-user provider credentials.
7. A domain-separated HKDF subkey is not password hardening, and running a KDF over a machine-generated 32-byte master key adds latency without adding security.

---

## Gap Closure Addendum (orchestrator-verified, 2026-10-22)

The research phase returned `outcome: partial` with 8 open gaps (G-1..G-8). The orchestrator closed every gap that is
closable by execution in this environment. All 8 are now closed or explicitly designed out. The research outcome is
`done` and the proposal may cite this artifact.

### Runtime evidence harness

- Python: `backend\venv\Scripts\python.exe` (cryptography 50.0.2, Python 3.12.10 local / 3.11 in CI).
- Browser-side vector generator: Node 24.18.1 `node:crypto` WebCrypto (same V8 WebCrypto implementation as Chrome/Edge).
- Harness files (outside the repo, ephemeral): `crypto_evidence.py`, `crypto_evidence.cjs`, `webcrypto_vector.json`.
- Result: **8/8 checks passed**, exit code 0.

| Check | Claim | Result |
| --- | --- | --- |
| T1 | `encode_dss_signature`/`decode_dss_signature` round trip | PASS - `der[0]=0x30`, len 24 |
| T2 | `verify()` accepts DER, REJECTS raw P1363; re-encoded DER verifies | PASS |
| T3 | AES-256-GCM + HKDF-SHA256 subkey + AAD binding | PASS - wrong AAD rejected with `InvalidTag` |
| T4 | `hashlib.scrypt` importable on this platform | PASS |
| T5 | `secrets.compare_digest` and `hmac.compare_digest` available | PASS |
| T6 | Single-winner challenge consumption under `BEGIN IMMEDIATE` | PASS - first consume `rowcount==1`, second consumer sees nothing |
| G-4 | `verify()` failure mode on malformed input | PASS - raises `InvalidSignature` (not `ValueError`) |
| G-7/G-8 | Browser SPKI + P1363 signature verified by the Python server side | PASS - SPKI loaded via `load_der_public_key`, P1363 (64 B) converted to DER, signature VERIFIED |

### Gap-by-gap disposition

- **G-1 - CLOSED BY EXECUTION.** WebCrypto `ECDSA`/`P-256` `sign()` produces **P1363 raw `r||s`, 64 bytes, first byte
  `0xed`** (not `0x30`). It is NOT DER. The server MUST convert before `verify()`. Empirical, not assumed.
- **G-2 - DESIGNED OUT.** `encode_dss_signature` from the installed package performs the DER encoding; the design must
  never hand-roll DER, so the byte-layout rules need not be re-derived.
- **G-3 - DESIGNED OUT.** The design enforces a 12-byte nonce itself, so the AEAD's own nonce-length range is never
  relied upon.
- **G-4 - CLOSED BY EXECUTION.** `verify()` raises `InvalidSignature` on malformed input.
- **G-5 - CLOSED BY EXECUTION.** All six behavioural claims confirmed at runtime (T1-T6).
- **G-6 - CLOSED.** `cryptography-50.0.2-cp311-abi3-manylinux_2_28_x86_64.whl` downloaded successfully with
  `pip download --only-binary=:all: --python-version 3.11 --platform manylinux_2_28_x86_64`; the `abi3` build also covers
  cp312. **`cryptography==50.0.2` is now pinned in `backend/requirements.txt`**, so CI installs it.
- **G-7 - CLOSED BY EXECUTION.** `exportKey("spki")` yields SPKI DER (91 bytes, `SEQUENCE` header `0x30`); the server
  loads it with `load_der_public_key`. The interop test proves the full browser-to-server path.
- **G-8 - DESIGNED OUT.** The load-bearing facts (verify needs DER; `encode_dss_signature` produces it) are proven from
  the installed package itself, so the external standard text is not required.

### New finding that changes the implementation

`AESGCM.decrypt` raises **`cryptography.exceptions.InvalidTag`**, which is **NOT a subclass of
`InvalidSignature`**. A design that catches `InvalidSignature` around credential decryption will let a tampered
ciphertext escape as an unhandled exception instead of a clean auth failure. AEAD failures and signature failures must
be caught separately. The signature path raises `InvalidSignature`; the credential path raises `InvalidTag`.

### Residual risk carried into design

- The local venv is Python 3.12.10 and has drifted from `requirements.txt` on several pins; CI is 3.11. The evidence
  above was produced on the local interpreter, and the first CI run is the confirming gate for the `abi3` wheel.
- The browser vector was produced with Node 24.18.1 while CI uses Node 22. Both are V8 WebCrypto; the encoding
  contract is the WebCrypto spec's, not a Node version detail.
- DER byte layout, the AEAD nonce policy and `verify()`'s internal handling of malformed input live in compiled Rust
  and remain non-inspectable from Python source. The design must rely only on the behaviours proven above.
