# Heurística de curación

Objetivo: el `GROUNDING.md` más pequeño que le da a Claude suficiente contexto para no
sugerir algo que ya rechazaste, no reinventar un patrón que ya existe, y no tocar código
protegido por cumplimiento. Cada archivo incluido debe poder justificarse en una frase; si
no puedes justificarlo, no lo incluyas.

## Orden de prioridad para incluir

1. **Interfaces y contratos antes que implementaciones.** Un archivo de tipos, un schema
   OpenAPI, una definición de interfaz TypeScript, un `.proto` — dicen más sobre "cómo se usa
   esto" que la implementación completa detrás. Ejemplo: incluye `types/Vendor.ts` con las
   firmas públicas; no incluyas los 400 archivos que las implementan.

2. **Un ejemplo representativo por patrón, no todas las instancias.** Si hay 12 endpoints REST
   que siguen la misma forma (validación → servicio → respuesta), incluye el mejor ejemplo de
   ese patrón, no los 12. Justificación: "ejemplo representativo del patrón
   controller→service→repository usado en todos los endpoints REST".

3. **Módulos relevantes al cumplimiento, completos.** A diferencia de la regla anterior, si un
   módulo maneja datos regulados (PII, datos financieros, autenticación, cifrado), inclúyelo
   completo, no resumido. Un fragmento fuera de contexto es peor que no incluirlo: puede hacer
   que Claude sugiera modificar una validación de cumplimiento sin ver por qué existe.

4. **Registros de decisiones de arquitectura (ADR), si existen.** Carpetas típicas:
   `docs/adr/`, `decisions/`, `architecture/`. Documentan el "por qué" que el código no dice.

5. **Configuración de compilación y dependencias.** `package.json`, `tsconfig.json`,
   `requirements.txt`, `Cargo.toml`, `pyproject.toml`. Le dicen a Claude qué librerías están
   realmente disponibles antes de que sugiera instalar una nueva o usar una API que el
   proyecto no soporta.

## Excluir siempre

- Tests, salvo que el test sea la única definición legible de un contrato (p. ej. un test de
  snapshot que documenta la forma exacta de una respuesta API y no hay schema en otro lado).
- Código generado (clientes de API generados, migraciones de ORM auto-generadas, bundles).
- `vendor/`, `node_modules/`, y equivalentes de otras plataformas (`.venv/`, `target/`).
- Migraciones de base de datos (el historial de cambios de schema no es contexto de
  arquitectura; si el schema actual importa, represéntalo con el modelo/entidad, no con el
  historial de migraciones).
- Ficheros de datos (fixtures, CSVs de prueba, dumps de base de datos).

## Estado actual vs. estado deseado

Cuando el código muestra un patrón que el equipo activamente quiere dejar de usar (p. ej.
"todavía usamos callbacks en `legacy/`, pero todo código nuevo usa async/await"), documenta
ambos explícitamente en las secciones separadas del template. Sin este marcador, Claude trata
el código legado como la convención vigente y lo replica en sugerencias nuevas.

## Ejemplo de justificación de inclusión

```
apps/api/src/types/Vendor.ts       | contrato público del dominio Vendor, usado por 40+ archivos
apps/api/src/routes/vendors.ts     | ejemplo representativo del patrón controller→service→repository
apps/api/src/services/encryption.ts| módulo de cumplimiento (cifra PII), incluido completo por Ley 1581
docs/adr/003-multi-tenancy.md      | decisión de arquitectura activa, explica el filtro por organizationId
package.json                        | dependencias reales disponibles, evita sugerir librerías no instaladas
```

## Fuentes

- **Orden de prioridad y reglas de exclusión de esta página**: criterio editorial propio,
  desarrollado para esta skill. No proviene de un estándar publicado ni de un organismo de
  normalización. Calidad: heurística razonada, no validada contra un corpus externo — trátala
  como punto de partida y ajústala al repositorio real que estés curando.
- **Patrones de detección de secretos** (`scripts/ground.py`, lista `SECRET_PATTERNS`):
  replican firmas de reconocimiento de uso público en herramientas conocidas de escaneo de
  secretos como [TruffleHog](https://github.com/trufflesecurity/trufflehog) y
  [Gitleaks](https://github.com/gitleaks/gitleaks) (AWS Access Key, cabecera de clave privada,
  JWT, tokens de Slack, cadenas de conexión con credenciales embebidas). Calidad: cobertura
  parcial y no mantenida en sincronía con esos proyectos — es una red de seguridad secundaria
  sobre archivos ya seleccionados por lista blanca, no un reemplazo de un escáner de secretos
  dedicado en CI/CD.
- **Repo Prompt** (mencionado en `README.md` como acelerador opcional): fuente primaria,
  [repoprompt.com](https://repoprompt.com), enlazada directamente.
