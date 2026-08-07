# codebase-grounding

codebase-grounding — construye y mantiene contexto curado de repositorios para Claude.
Copyright (C) 2026 Milton F. Amado

This program is free software: you can redistribute it and/or modify it under the terms of
the GNU General Public License as published by the Free Software Foundation, either version
3 of the License, or (at your option) any later version. This program is distributed in the
hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details. You should have received a copy of the GNU General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.

Contacto: Milton F. Amado — diaatdia@hotmail.com

Skill para Claude Code que construye y mantiene `GROUNDING.md`: un artefacto de contexto
curado que vive dentro de cada repositorio, para que Claude conozca la arquitectura, los
patrones internos y las restricciones de cumplimiento reales de ese proyecto antes de
revisar código — en vez de responder de forma genérica.

## ¿Qué hace?

- **Selección por lista blanca:** curas explícitamente qué archivos entran al contexto,
  cada uno con una justificación de una frase. Nunca escanea todo el repo y excluye lo
  sensible.
- **Estado actual vs. estado deseado:** distingue cómo está construido el código hoy
  (incluidos los patrones que no te gustan) de hacia dónde debería ir el código nuevo.
- **Detección de obsolescencia por hash:** cada `GROUNDING.md` guarda el hash del conjunto
  de archivos incluidos. Al reutilizarlo, se recalcula y se avisa si el repo cambió — sin
  preguntas del tipo "¿sigue vigente?" que se aceptan sin leer.
- **Escaneo de secretos como red secundaria:** antes de escribir el contexto, revisa los
  archivos ya seleccionados en busca de credenciales y detiene el proceso si encuentra algo.
- **Aislamiento estricto por proyecto:** `GROUNDING.md` vive en la raíz del repositorio que
  describe. La skill nunca lee ni transfiere contexto de un proyecto a otro.

## Nota de alcance

Esta skill reduce sugerencias incorrectas en revisiones de código al darle a Claude contexto
específico del proyecto. **No** produce evidencia de cumplimiento regulatorio ni
trazabilidad defendible ante un regulador (p. ej. la SFC). La trazabilidad de qué cambió y
por qué la da el historial de git, no esta skill. Trátala como una herramienta de precisión
y ahorro de tiempo, no como un control de cumplimiento.

## Instalación

Es una skill de Claude Code / Claude, no un paquete de npm ni de pip. Se instala copiando
la carpeta a tu directorio de skills:

```bash
git clone https://github.com/[tu-usuario]/codebase-grounding.git
cp -r codebase-grounding ~/.claude/skills/codebase-grounding
```

El único requisito para el CLI incluido es Python 3.9+ (solo biblioteca estándar, sin
dependencias que instalar).

## Uso rápido

Dentro de una sesión de Claude Code o Claude, en el repositorio que te interesa:

> "Prepara el contexto de este repo antes de revisar el módulo de pagos."

La skill hace como máximo 2 preguntas (repositorio/tarea, y si el dominio es regulado),
infiere la profundidad del contexto y confirma en una línea antes de construir
`GROUNDING.md`. Las sesiones siguientes verifican automáticamente si el contexto sigue
vigente (por hash de contenido) antes de reutilizarlo.

También puedes invocar el CLI directamente:

```bash
# Construye GROUNDING.md a partir de una lista blanca de archivos
python3 scripts/ground.py build \
  --root /ruta/al/repo \
  --output /ruta/al/repo/GROUNDING.md \
  --file src/types/Vendor.ts --reason "contrato público del dominio Vendor" \
  --file src/routes/vendors.ts --reason "ejemplo representativo del patrón REST"

# Verifica si el contexto sigue vigente (hash de contenido, no fecha)
python3 scripts/ground.py verify --root /ruta/al/repo --output /ruta/al/repo/GROUNDING.md

# Registra un aprendizaje (sugerencia rechazada + motivo) y refresca el hash
python3 scripts/ground.py update \
  --root /ruta/al/repo --output /ruta/al/repo/GROUNDING.md \
  --note "sugerencia: usar Redis para cache de sesión — motivo: stack ya define Postgres-only por contrato de infra"
```

`verify` sale con código 0 si el hash coincide, 1 si el conjunto de archivos cambió (e
imprime cuáles), y falla explícitamente si `GROUNDING.md` está fuera de la raíz del repo
indicada. El escáner de secretos reconoce claves de AWS, cabeceras de clave privada, tokens
JWT, tokens de Slack, cadenas de conexión con credenciales embebidas y el patrón genérico
`api_key=...`. Nunca imprime el valor detectado, solo archivo y línea.

## Repo Prompt (opcional)

Si usas macOS, la app [Repo Prompt](https://repoprompt.com) puede acelerar la selección
manual de archivos con una vista de árbol del repositorio. Es un acelerador puramente
opcional — la skill no depende de ella, no requiere configuración MCP, y funciona igual de
bien en cualquier plataforma sin ella.

## Fuentes

Ver `reference/curation.md` sección "Fuentes" para el origen y nivel de confianza de la
heurística de curación y de los patrones de detección de secretos usados en
`scripts/ground.py`.

## Licencia

Este proyecto está disponible bajo dos modelos de licencia:

### 1. GPL v3 (uso abierto)

**Gratis para:** desarrolladores independientes, startups, proyectos open source, uso
educativo.

**Términos:**
- Puedes usar, modificar y distribuir libremente
- Mejoras deben compartirse con la comunidad si distribuyes una versión modificada
- Debes dar crédito

**Cuándo aplica:** si compartes cualquier versión modificada públicamente, debe ser bajo
GPL v3.

[Ver licencia completa](./LICENSE)

### 2. Uso comercial

**Para:** empresas o consultores que quieren usar la skill como parte de un servicio de
pago a clientes, o que necesitan mantener modificaciones privadas sin las obligaciones de
copyleft de la GPL v3.

**Pricing:** definido caso a caso, según el alcance del uso comercial. Contacta antes de
usarla con fines comerciales para acordar los términos.

**Contacto:** Milton F. Amado — diaatdia@hotmail.com

## Contribuciones

Las mejoras son bienvenidas. Abre un issue o envía un PR. Al contribuir, aceptas que tus
cambios se licencien bajo GPL v3.

## Decisiones de implementación

Estas son las decisiones tomadas ante ambigüedades del encargo original, siguiendo la regla
de "elige la opción más simple y anótala aquí":

- **Formato de `--reason` en `build`**: se pasa como lista paralela a `--file`, en el mismo
  orden y misma cantidad. Es más explícito en la CLI que inferir la justificación desde el
  contenido del archivo, y deja la justificación real en manos de quien invoca la skill
  (Claude, siguiendo `reference/curation.md`), no del script.
- **Almacenamiento del hash completo**: el header visible de `GROUNDING.md` muestra solo los
  primeros 12 caracteres del SHA-256 (legible), pero el hash completo de 64 caracteres se
  guarda en un comentario HTML al final del archivo (`<!-- grounding-hash-full: ... -->`)
  junto con el manifiesto de rutas relativas (`<!-- grounding-manifest: ... -->`). Esto evita
  colisiones del hash corto y le da a `verify`/`update` una fuente de verdad exacta sin
  tener que re-parsear la tabla de manifiesto en prosa libre.
- **Detección de "qué cambió" en `verify`**: dado que solo se almacena el hash del conjunto
  concatenado (no un hash por archivo), `verify` no puede señalar con precisión cuál archivo
  individual cambió cuando el hash no coincide — solo que el conjunto ya no coincide. En ese
  caso lista todos los archivos del manifiesto para que el usuario los revise. Un hash por
  archivo habría resuelto esto pero agrega complejidad no pedida por el encargo; se documenta
  aquí como limitación conocida en vez de silenciarla.
- **Codificación de texto al escanear secretos**: `scan_secrets` decodifica cada archivo como
  UTF-8 y omite silenciosamente archivos binarios o con encoding distinto (no son candidatos
  razonables para contener secretos de texto plano de todas formas, y fallar ahí rompería
  builds legítimos con, por ejemplo, un PNG incluido por error en la lista blanca — aunque en
  la práctica la curación de la Fase 2 no debería seleccionar binarios).
- **Nombre de la skill**: `codebase-grounding`, no `repo-prompt-grounding` (nombre obsoleto
  de una versión anterior que dependía de la app Repo Prompt).
- **Licencia dual GPL v3 / comercial**: el pricing comercial no está fijado — se define caso
  a caso según el alcance del uso. Se deja el contacto como pendiente hasta que el titular
  defina un canal de contacto real.
