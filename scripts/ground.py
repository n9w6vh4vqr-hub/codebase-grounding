#!/usr/bin/env python3
"""ground.py - CLI for building, verifying, and updating a project's GROUNDING.md context artifact.
Copyright (C) 2026 Milton F. Amado <diaatdia@hotmail.com>

This program is free software: you can redistribute it and/or modify it under the terms of
the GNU General Public License as published by the Free Software Foundation, either version
3 of the License, or (at your option) any later version. This program is distributed in the
hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details. You should have received a copy of the GNU General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.

Usage:
    ground.py build  --root <repo-root> --output <GROUNDING.md path> --file <path> [--file <path> ...] [--reason <text> ...]
    ground.py verify --root <repo-root> --output <GROUNDING.md path>
    ground.py update --root <repo-root> --output <GROUNDING.md path> --note <text>
"""

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HASH_LINE_RE = re.compile(
    r"^Generado: (?P<fecha>.+?) · Hash: (?P<hash>[0-9a-f]{12}) · Archivos: (?P<n>\d+)$",
    re.MULTILINE,
)
MANIFEST_HEADER = "## Manifiesto de archivos"
REJECTED_HEADER = "## Patrones rechazados"

# Firmas de reconocimiento de uso público en herramientas de escaneo de secretos como
# TruffleHog (https://github.com/trufflesecurity/trufflehog) y
# Gitleaks (https://github.com/gitleaks/gitleaks). Cobertura parcial, no sincronizada con
# esos proyectos: red de seguridad secundaria sobre archivos ya elegidos por lista blanca,
# no un reemplazo de un escáner de secretos dedicado en CI/CD. Ver reference/curation.md
# sección "Fuentes" para el detalle de calidad/alcance.
SECRET_PATTERNS = [
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS Secret Key", re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}")),
    ("Private Key Header", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("JWT Token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Generic API Key", re.compile(r"(?i)(api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\s*[=:]\s*['\"][A-Za-z0-9_\-/+=]{16,}['\"]")),
    ("Connection String", re.compile(r"(?i)(postgres|postgresql|mysql|mongodb|redis)://[^:\s]+:[^@\s]+@")),
    ("Slack Token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
]


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def resolve_root(root_arg: str) -> Path:
    root = Path(root_arg).resolve()
    if not root.is_dir():
        die(f"root no es un directorio: {root}")
    return root


def resolve_output(output_arg: str, root: Path) -> Path:
    output = Path(output_arg).resolve()
    try:
        output.relative_to(root)
    except ValueError:
        die(f"GROUNDING.md debe estar dentro de la raíz del repo indicada ({root}), recibido: {output}")
    return output


def resolve_included_files(root: Path, file_args: list, reasons: list) -> tuple:
    if not file_args:
        die("build requiere al menos un --file (selección por lista blanca)")
    if reasons and len(reasons) != len(file_args):
        die("si se pasan --reason, debe haber uno por cada --file, en el mismo orden")
    resolved = []
    for i, f in enumerate(file_args):
        p = Path(f)
        p = p if p.is_absolute() else (root / p)
        p = p.resolve()
        try:
            p.relative_to(root)
        except ValueError:
            die(f"archivo fuera de la raíz del repo: {p}")
        if not p.is_file():
            die(f"archivo no encontrado: {p}")
        reason = reasons[i] if reasons else "(justificación pendiente)"
        resolved.append((p, reason))
    # Stable order: sorted by path relative to root, keeping each file's own reason attached.
    resolved.sort(key=lambda pair: str(pair[0].relative_to(root)))
    return resolved


def scan_secrets(files: list) -> list:
    findings = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append((f, lineno, label))
    return findings


def compute_hash(root: Path, files: list) -> str:
    digest = hashlib.sha256()
    for f in files:
        digest.update(str(f.relative_to(root)).encode("utf-8"))
        digest.update(b"\x00")
        digest.update(f.read_bytes())
        digest.update(b"\x00")
    return digest.hexdigest()


def load_template() -> str:
    template_path = Path(__file__).resolve().parent.parent / "reference" / "template.md"
    if not template_path.is_file():
        die(f"plantilla no encontrada: {template_path}")
    return template_path.read_text(encoding="utf-8")


def cmd_build(args) -> None:
    root = resolve_root(args.root)
    output = resolve_output(args.output, root)
    resolved = resolve_included_files(root, args.file, args.reason or [])
    files = [p for p, _ in resolved]

    findings = scan_secrets(files)
    if findings:
        print("escaneo de secretos: se detectaron posibles credenciales. Build detenido.", file=sys.stderr)
        for f, lineno, label in findings:
            print(f"  {f.relative_to(root)}:{lineno} — {label}", file=sys.stderr)
        sys.exit(2)

    file_hash = compute_hash(root, files)
    short_hash = file_hash[:12]

    manifest_lines = [f"{p.relative_to(root)} | {reason}" for p, reason in resolved]

    template = load_template()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = template.replace(
        "# Grounding: <proyecto>\nGenerado: <fecha> · Hash: <sha256-corto> · Archivos: <n>",
        f"# Grounding: {root.name}\nGenerado: {generated} · Hash: {short_hash} · Archivos: {len(files)}",
    )
    content = content.replace(
        "<ruta | motivo de inclusión en una línea>",
        "\n".join(manifest_lines) if manifest_lines else "(sin archivos)",
    )
    # Store the full hash as an HTML comment so verify can recover it without parsing the short form ambiguously.
    content += f"\n<!-- grounding-hash-full: {file_hash} -->\n"
    content += f"<!-- grounding-manifest: {' | '.join(str(f.relative_to(root)) for f in files)} -->\n"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"GROUNDING.md generado: {output}")
    print(f"archivos incluidos: {len(files)}")
    print(f"hash: {short_hash}")


def parse_existing(output: Path) -> dict:
    if not output.is_file():
        die(f"GROUNDING.md no encontrado: {output}")
    text = output.read_text(encoding="utf-8")
    full_hash_match = re.search(r"<!-- grounding-hash-full: ([0-9a-f]{64}) -->", text)
    manifest_match = re.search(r"<!-- grounding-manifest: (.*?) -->", text)
    if not full_hash_match or not manifest_match:
        die("GROUNDING.md no contiene metadatos de hash/manifiesto reconocibles; regenera con 'build'")
    stored_hash = full_hash_match.group(1)
    manifest = [m.strip() for m in manifest_match.group(1).split("|") if m.strip()]
    return {"text": text, "hash": stored_hash, "manifest": manifest}


def cmd_verify(args) -> None:
    root = resolve_root(args.root)
    output = resolve_output(args.output, root)
    state = parse_existing(output)

    missing = [rel for rel in state["manifest"] if not (root / rel).is_file()]
    if missing:
        print("archivos del manifiesto ya no existen:")
        for rel in missing:
            print(f"  {rel}")
        sys.exit(1)

    files = [(root / rel).resolve() for rel in state["manifest"]]
    files.sort(key=lambda p: str(p.relative_to(root)))
    current_hash = compute_hash(root, files)

    if current_hash == state["hash"]:
        print("OK: el contexto sigue vigente (hash coincide).")
        sys.exit(0)

    print("desactualizado: el hash no coincide. Archivos posiblemente modificados:")
    # We can't know exactly which changed without per-file hashes, so recompute per-file.
    for f in files:
        rel = f.relative_to(root)
        print(f"  {rel}")
    sys.exit(1)


def cmd_update(args) -> None:
    root = resolve_root(args.root)
    output = resolve_output(args.output, root)
    state = parse_existing(output)

    manifest_paths = [(root / rel).resolve() for rel in state["manifest"]]
    missing = [p for p in manifest_paths if not p.is_file()]
    if missing:
        die("no se puede actualizar: hay archivos del manifiesto que ya no existen. Ejecuta 'build' de nuevo.")

    manifest_paths.sort(key=lambda p: str(p.relative_to(root)))
    new_hash = compute_hash(root, manifest_paths)
    short_hash = new_hash[:12]

    text = state["text"]
    text = re.sub(
        r"<!-- grounding-hash-full: [0-9a-f]{64} -->",
        f"<!-- grounding-hash-full: {new_hash} -->",
        text,
    )
    text = HASH_LINE_RE_MULTILINE_SUB(text, short_hash, len(manifest_paths))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"- {timestamp}: {args.note}"
    if REJECTED_HEADER in text:
        marker = REJECTED_HEADER
        idx = text.index(marker) + len(marker)
        # Insert after the header line.
        next_newline = text.index("\n", idx)
        text = text[: next_newline + 1] + entry + "\n" + text[next_newline + 1 :]
    else:
        die("plantilla inesperada: no se encontró la sección 'Patrones rechazados'")

    output.write_text(text, encoding="utf-8")
    print(f"GROUNDING.md actualizado: {output}")
    print(f"hash: {short_hash}")
    print(f"nota registrada: {args.note}")


def HASH_LINE_RE_MULTILINE_SUB(text: str, short_hash: str, n_files: int) -> str:
    def repl(m):
        return f"Generado: {m.group('fecha')} · Hash: {short_hash} · Archivos: {n_files}"

    new_text, count = HASH_LINE_RE.subn(repl, text)
    if count == 0:
        die("no se encontró la línea de metadatos 'Generado: ... · Hash: ... · Archivos: ...'")
    return new_text


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ground.py",
        description="Construye, verifica y actualiza el contexto GROUNDING.md de un repositorio.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Genera GROUNDING.md a partir de una lista blanca de archivos")
    p_build.add_argument("--root", required=True, help="Raíz del repositorio")
    p_build.add_argument("--output", required=True, help="Ruta de salida para GROUNDING.md (debe estar bajo --root)")
    p_build.add_argument("--file", action="append", required=True, help="Archivo a incluir (repetible)")
    p_build.add_argument("--reason", action="append", help="Justificación de inclusión, uno por --file en el mismo orden")
    p_build.set_defaults(func=cmd_build)

    p_verify = sub.add_parser("verify", help="Verifica si el hash del contexto sigue vigente")
    p_verify.add_argument("--root", required=True, help="Raíz del repositorio")
    p_verify.add_argument("--output", required=True, help="Ruta de GROUNDING.md existente")
    p_verify.set_defaults(func=cmd_verify)

    p_update = sub.add_parser("update", help="Refresca el hash y registra un aprendizaje")
    p_update.add_argument("--root", required=True, help="Raíz del repositorio")
    p_update.add_argument("--output", required=True, help="Ruta de GROUNDING.md existente")
    p_update.add_argument("--note", required=True, help="Aprendizaje a registrar (p. ej. sugerencia rechazada + motivo)")
    p_update.set_defaults(func=cmd_update)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
