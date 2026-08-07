---
name: codebase-grounding
description: Construye y mantiene un artefacto de contexto curado (GROUNDING.md) por repositorio para que las revisiones de código de Claude conozcan la arquitectura, los patrones internos y las restricciones de cumplimiento reales del proyecto, en vez de responder de forma genérica. Se activa con frases como "prepara el contexto de este repo", "revisa mi código con contexto", "Claude no entiende nuestra arquitectura", "grounding", "contexto específico del proyecto", o antes de cualquier revisión de código, auditoría, refactor o decisión de arquitectura sobre un repositorio real. No la uses para revisiones puntuales de un solo archivo aislado ni para scripts desechables sin arquitectura que preservar.
---

# codebase-grounding

Esta skill construye y mantiene `GROUNDING.md`: un artefacto de contexto curado que vive
dentro del repositorio que describe. Su función es reducir sugerencias incorrectas en
revisiones de código, no producir evidencia de cumplimiento regulatorio — la trazabilidad
para auditoría la da git, no esta skill.

Opera en 4 fases: SCOPE → ASSEMBLE → APPLY → PERSIST. Ejecuta las fases en orden. No saltes
fases ni agregues pasos adicionales.

## Regla de aislamiento (no negociable)

`GROUNDING.md` es memoria estrictamente por proyecto. Vive en la raíz del repositorio al que
describe. **Nunca** leas un `GROUNDING.md` de otra ruta, ni transfieras patrones, decisiones
o aprendizajes de un proyecto a otro. Hacerlo filtraría contexto confidencial entre clientes.
Antes de leer o escribir un `GROUNDING.md`, confirma que su ruta está dentro de la raíz del
repositorio en el que estás trabajando ahora mismo. Si el usuario pide reutilizar contexto de
otro proyecto, recházalo y explica por qué.

## FASE 1 — SCOPE

Haz como máximo 2 preguntas, en un solo turno:

1. ¿Qué repositorio y qué tarea vas a hacer? (revisión, auditoría, refactor, decisión de
   arquitectura)
2. ¿Es un dominio regulado? (fintech / salud / ninguno) — esto determina si se completa la
   sección "Restricciones de cumplimiento" del template.

No preguntes nada más en esta fase. Con las respuestas, infiere la profundidad del contexto
(número aproximado de archivos a incluir) según el tamaño y la complejidad del repositorio, y
confírmala en una sola línea, por ejemplo:

> "Contexto ligero (~10 archivos). Di 'profundo' para un barrido completo."

Si el usuario responde "profundo" (o equivalente), amplía la selección de archivos en la
fase siguiente; si no responde, procede con la profundidad inferida.

## FASE 2 — ASSEMBLE

Antes de seleccionar archivos, **lee `reference/curation.md` completo**. Contiene la
heurística de curación con ejemplos concretos — es la parte de mayor valor de esta skill y
no debe improvisarse.

Pasos:

1. Selecciona archivos por **lista blanca explícita**. Nunca "escanees todo el repo y
   excluyas lo sensible" — la inclusión es siempre una decisión positiva y justificada,
   archivo por archivo. El escaneo de secretos (paso 3) es una red de seguridad secundaria
   sobre archivos ya elegidos, no el mecanismo de selección.
2. Para cada archivo candidato, escribe en una frase por qué lo incluyes, siguiendo el orden
   de prioridad de `reference/curation.md` (interfaces/contratos, un ejemplo por patrón,
   módulos de cumplimiento completos, ADRs, configuración de build/dependencias). Si no puedes
   justificar la inclusión en una frase, no lo incluyas.
3. Ejecuta el escaneo de secretos sobre los archivos seleccionados:
   ```
   python3 scripts/ground.py build --root <raíz-repo> --output <raíz-repo>/GROUNDING.md \
     --file <archivo1> --file <archivo2> ... \
     --reason "<justificación1>" --reason "<justificación2>" ...
   ```
   Si el escaneo detecta un posible secreto, el comando se detiene con código de salida 2 e
   imprime archivo y línea (nunca el valor). **Detente ahí.** No continúes la construcción del
   contexto hasta que el usuario confirme que el archivo señalado es seguro o lo excluya.
4. Al completar sin hallazgos, `ground.py build` genera `GROUNDING.md` a partir de
   `reference/template.md`, calcula el hash SHA-256 del conjunto de archivos incluidos (en
   orden estable) y lo almacena en el propio archivo.
5. Completa a mano las secciones narrativas de `GROUNDING.md` que el script deja como
   plantilla (`Alcance`, `Estado actual`, `Estado deseado`, `Invariantes`, y
   `Restricciones de cumplimiento` si aplica según la Fase 1). **Distingue explícitamente**
   el estado actual del código (incluidos los patrones que no te gustan) del estado deseado
   (hacia dónde va, qué preferir en código nuevo). Sin este marcador, las sugerencias
   futuras replican patrones legado como si fueran la norma.

## FASE 3 — APPLY

1. Antes de usar `GROUNDING.md` en una sesión de revisión, verifica que sigue vigente:
   ```
   python3 scripts/ground.py verify --root <raíz-repo> --output <raíz-repo>/GROUNDING.md
   ```
   Código de salida 0: el contexto sigue vigente, continúa. Código de salida distinto de
   cero: los archivos incluidos cambiaron desde que se construyó el contexto. **No preguntes
   "¿sigue siendo válido esto?"** — eso se acepta sin leer. En vez de eso, informa
   directamente qué archivos del manifiesto cambiaron o desaparecieron y reconstruye el
   contexto (Fase 2) antes de continuar con la tarea.
2. Carga el contenido de `GROUNDING.md` verificado como contexto de la sesión.
3. Ejecuta la tarea del usuario (revisión, auditoría, refactor, diseño) con ese contexto.
4. Presenta cualquier cambio de código como un diff explícito. No apliques cambios sin
   aprobación explícita del usuario sobre ese diff en particular. No agregues ceremonias
   adicionales de control de cambios más allá de esta aprobación por diff.

## FASE 4 — PERSIST

Al final de la sesión (o cuando el usuario rechace una sugerencia con un motivo claro):

1. Registra el aprendizaje directamente en `GROUNDING.md`, en la sección
   "Patrones rechazados", con el formato: sugerencia rechazada + motivo.
2. Usa el subcomando `update`, que además refresca el hash almacenado:
   ```
   python3 scripts/ground.py update --root <raíz-repo> --output <raíz-repo>/GROUNDING.md \
     --note "<sugerencia rechazada> — <motivo>"
   ```
3. Esta captura es implícita, a partir de rechazos reales durante la sesión — no hagas una
   encuesta de fin de sesión ni pidas una puntuación numérica.
4. Nunca escribas este aprendizaje en ningún lugar fuera de `GROUNDING.md` dentro de la raíz
   de este repositorio. No existe memoria global para esta skill.
