# Traspaso del proyecto para Gemini

## Objetivo del documento

Este documento describe el estado actual del bot, los cambios realizados, cómo
funciona y qué trabajo falta. Antes de modificar el proyecto, revisa el código
actual y conserva esta arquitectura. No habilites órdenes reales ni muestres el
contenido de `.env`.

## Estado actual

El proyecto es un bot long-only para criptomonedas que funciona exclusivamente en
paper trading. Actualmente:

- Consulta datos OHLCV y ticker desde Binance mediante CCXT.
- Opera los símbolos configurados, inicialmente `BTC/USDT` y `ETH/USDT`.
- Utiliza velas de una hora.
- Solo genera señales con velas cerradas.
- Evita procesar dos veces la misma vela.
- Mantiene posiciones separadas por símbolo.
- Simula capital, exposición, comisiones, slippage y P&L.
- Aplica stop-loss, take-profit y un límite global de drawdown.
- Persiste el estado para poder reiniciarse sin perder posiciones.
- Puede utilizar Gemini como filtro opcional de señales técnicas.
- Tiene un backtest técnico que no llama a Gemini.
- No contiene lógica para enviar órdenes reales al exchange.

El bot fue ejecutado correctamente con:

```text
Iniciando bot en PAPER TRADING.
Filtro Gemini: ACTIVO
[INFO] Datos conectados a Binance Testnet.
```

Los mensajes `Vela ... ya procesada; sin duplicar senal` son normales. Indican que
la vela ya fue evaluada y que el bot está evitando repetir una operación. El proceso
continúa revisando el mercado cada 420 segundos, principalmente para controlar
posiciones y detectar stops intraperiodo.

## Arquitectura actual

```text
main.py
├── config/settings.py
├── strategies/base_strategy.py
│   ├── strategies/technical_strategy.py
│   ├── core/data_engine.py
│   ├── core/indicators.py
│   ├── core/ai_analyst.py
│   ├── core/risk_engine.py
│   ├── core/execution.py
│   └── core/logger.py
├── core/dashboard.py
└── backtest.py
```

## Cambios realizados

### 1. Configuración centralizada

`config/settings.py` ahora carga y valida los parámetros desde `.env`:

- Símbolos y timeframe.
- Intervalo del ciclo.
- Capital inicial.
- Riesgo por operación.
- Máxima exposición total.
- Máximo drawdown.
- Multiplicadores ATR.
- Comisión y slippage.
- Mínimo notional.
- Activación y modelo de Gemini.

Valores iniciales importantes:

```text
Capital inicial:             100 USDT
Riesgo por operación:        1%
Exposición máxima total:     40%
Drawdown máximo:             15%
Stop-loss:                   2 ATR
Take-profit:                 2R, equivalente a 4 ATR
Comisión por lado:           0,1%
Slippage por lado:           0,05%
Timeframe:                   1h
Intervalo de consulta:       420 segundos
```

`PAPER_TRADING=false` hace que el programa se niegue a iniciar. Esto es deliberado:
todavía no debe existir una vía hacia trading real.

### 2. Estrategia técnica determinista

La estrategia está en `strategies/technical_strategy.py` y se reutiliza en paper
trading y backtest.

Entrada long si se cumplen simultáneamente:

```text
close > SMA 200
EMA 20 > SMA 50
MACD histogram > 0
RSI 14 entre 50 y 68
No existe una posición abierta en ese símbolo
```

Salida por cualquiera de estas condiciones:

```text
Stop-loss
Take-profit
Cruce bajista de EMA 20 por debajo de SMA 50
RSI 14 por debajo de 45
Circuit breaker de drawdown
```

Si stop y take-profit aparecen dentro de la misma vela y no puede determinarse el
orden, se asume que se ejecutó primero el stop. Esto mantiene un backtest
conservador.

### 3. Indicadores

`core/indicators.py` calcula sin `pandas-ta`:

- SMA 50.
- SMA 200.
- EMA 20.
- RSI 14 con suavizado tipo Wilder.
- MACD 12/26/9.
- ATR 14 con suavizado tipo Wilder.
- Media de volumen de 20 períodos.

Se eliminó la dependencia activa de `pandas-ta` para evitar problemas con Numba y
Python 3.14.

### 4. Integración con Gemini

`core/ai_analyst.py` fue migrado de `google.generativeai` al SDK `google-genai`.

Modelo verificado con la clave existente:

```text
gemini-3.8-flash
```

Gemini ya no produce libremente una orden de compra o venta. La señal principal es
técnica y Gemini funciona como filtro de entrada. Puede responder:

```text
APROBAR
RECHAZAR
REDUCIR_RIESGO
```

La respuesta JSON incluye:

```json
{
  "decision": "REDUCIR_RIESGO",
  "confidence": 75,
  "risk_multiplier": 0.5,
  "reasons": ["motivo"]
}
```

La integración utiliza:

- JSON Schema.
- Temperatura baja.
- Timeout.
- Reintentos limitados.
- Umbral mínimo de confianza.
- Validación de decisión y multiplicador.
- Rechazo seguro ante errores o JSON inválido.

Gemini solo se consulta cuando ya existe una señal técnica de compra. No se llama en
cada ciclo y no se utiliza para bloquear salidas de riesgo.

Para activarlo en `.env`:

```dotenv
AI_ENABLED=true
GEMINI_MODEL=gemini-3.8-flash
```

No inventar noticias. Actualmente el prompt informa `news_available=false`.

### 5. Motor de paper trading

`core/execution.py` reemplazó el booleano global `active_position` por posiciones
persistentes separadas por símbolo.

Cada posición conserva:

- Símbolo.
- Timestamp de entrada.
- Vela que originó la señal.
- Precio de entrada con slippage.
- Cantidad.
- Stop-loss.
- Take-profit.
- Comisión de entrada.
- Motivo y confianza.

Al abrir una posición:

- Se limita el tamaño por riesgo.
- Se limita por exposición total.
- Se limita por efectivo disponible.
- Se verifica el mínimo notional.
- Se descuenta notional y comisión del efectivo.

Al cerrar una posición:

```text
PnL bruto = (precio de salida - precio de entrada) × cantidad
PnL neto = PnL bruto - comisión de entrada - comisión de salida
```

El estado se guarda atómicamente en:

```text
state/paper_state.json
```

Incluye efectivo, peak equity, drawdown, posiciones, últimos precios y últimas velas
procesadas.

### 6. Velas cerradas y deduplicación

`strategies/base_strategy.py` utiliza la penúltima vela devuelta por el exchange para
generar señales, ya que la última normalmente sigue abierta.

El timestamp procesado queda persistido por símbolo. El bot puede seguir ejecutándose
cada 420 segundos sin abrir varias operaciones por la misma vela.

También se evita aplicar a una nueva posición el rango high/low ocurrido antes de su
entrada.

### 7. Registros y dashboard

Se reemplazó el registro ambiguo de acciones por tres archivos:

```text
logs/signals.csv
logs/trades.csv
logs/equity.csv
```

`signals.csv` contiene indicadores, señal técnica, decisión de Gemini y decisión
final. `trades.csv` registra aperturas, cierres, costes y P&L. `equity.csv` registra
efectivo, equity, exposición y drawdown.

El dashboard se ejecuta con:

```bash
python3 main.py --dashboard
```

También funciona `python3 core/dashboard.py`, aunque se recomienda usar el comando
anterior.

### 8. Backtest

`backtest.py` reutiliza los indicadores, las señales técnicas, el RiskEngine y el
ExecutionEngine.

Características:

- No llama a Gemini.
- Descarga datos públicos de producción, pero nunca envía órdenes.
- Excluye la vela posiblemente abierta.
- Calcula la señal con una vela cerrada.
- Ejecuta la entrada en la apertura de la vela siguiente.
- Incluye comisión y slippage.
- Evalúa stop y take-profit dentro de la vela de entrada.
- Usa resolución conservadora cuando stop y target coinciden.
- Compara contra buy-and-hold.

Comandos:

```bash
python3 backtest.py --symbol "BTC/USDT" --candles 2000
python3 backtest.py --symbol "ETH/USDT" --candles 2000
```

También acepta un CSV con columnas:

```text
timestamp,open,high,low,close,volume
```

### 9. Seguridad del repositorio

- `.env` fue retirado del índice de Git, pero el archivo local se conservó.
- `.env` está incluido en `.gitignore`.
- Se agregó `.env.example` sin secretos.
- Los archivos `__pycache__`, `*.pyc`, estado y logs generados están ignorados.
- Si el repositorio se compartió cuando `.env` estaba versionado, debe rotarse la
  clave de Gemini.

### 10. Dependencias y documentación

`requirements.txt` ahora contiene solamente dependencias utilizadas:

```text
ccxt
google-genai
numpy
pandas
python-dotenv
```

`README.md` contiene instalación, ejecución, dashboard, backtest, archivos generados
y advertencias de seguridad.

## Pruebas realizadas

Se agregaron pruebas sin llamadas reales a Binance ni Gemini para:

- Position sizing.
- Validación de ATR.
- Apertura y cierre de posiciones.
- P&L neto con comisiones.
- Persistencia después de reiniciar.
- Señal técnica de entrada.
- Señal técnica de salida.
- Gemini desactivado.
- Respuesta estructurada de Gemini mediante mock.
- Protección contra usar el high/low previo a la entrada.

Resultado actual:

```text
9 tests ejecutados
9 tests aprobados
```

Comando:

```bash
python3 -m unittest discover -s tests -v
```

También se verificó una llamada real a `gemini-3.8-flash`. La respuesta fue válida y
el filtro devolvió `REDUCIR_RIESGO` con confianza y multiplicador parseados.

## Primer resultado de backtest

Muestra de BTC/USDT:

```text
Período:               2026-09-03 a 2026-10-06 UTC
Velas utilizables:     800
Operaciones cerradas:  18
Ganadoras:              6
Perdedoras:            12
Win rate:              33,333%
Retorno neto:          -3,239%
Drawdown máximo:        3,544%
Profit factor:          0,444
Expectancy:            -0,1799 USDT por operación
Buy-and-hold:          +11,502%
Equity final:          96,7609 USDT
```

Este resultado confirma que el motor puede medir pérdidas correctamente. No demuestra
rentabilidad; por el contrario, la estrategia inicial necesita investigación y más
datos. No optimizar parámetros únicamente sobre esta muestra.

## Cómo ejecutar el proyecto

Prueba de un ciclo:

```bash
python3 main.py --once
```

Ejecución continua:

```bash
python3 main.py
```

El proceso continuo se detiene con `Ctrl+C`.

Dashboard en otra terminal:

```bash
python3 main.py --dashboard
```

Backtests, también desde otra terminal o con el bot detenido:

```bash
python3 backtest.py --symbol "BTC/USDT" --candles 2000
python3 backtest.py --symbol "ETH/USDT" --candles 2000
```

## Restricciones que deben mantenerse

1. No habilitar órdenes reales.
2. No añadir claves del exchange hasta terminar validación y revisión de seguridad.
3. No permitir retiros bajo ninguna circunstancia.
4. No convertir a Gemini en la única fuente de señales.
5. No usar la última vela abierta para generar señales.
6. No eliminar comisiones o slippage del backtest.
7. No borrar ni reiniciar el estado automáticamente.
8. No mostrar, registrar ni versionar secretos.
9. No afirmar rentabilidad con muestras pequeñas.
10. No modificar una regla de paper trading sin modificar la misma regla en backtest.

## Trabajo pendiente antes de producción

Prioridad alta:

- Obtener varios años de datos por símbolo.
- Ejecutar pruebas en mercados alcistas, bajistas y laterales.
- Agregar validación walk-forward y períodos fuera de muestra.
- Agregar límite de pérdida diaria.
- Agregar reporte de Sharpe, Sortino y duración de operaciones.
- Comparar formalmente `technical_only` contra `technical_plus_gemini`.
- Registrar latencia y versión exacta del prompt de Gemini.
- Ejecutar paper trading durante varias semanas.
- Probar recuperación después de cierres abruptos del proceso.

Prioridad media:

- Exportar curva de equity y gráficos.
- Añadir evaluación multi-activo conjunta al backtest.
- Añadir filtros de volumen y volatilidad sólo si mejoran fuera de muestra.
- Añadir alertas, sin convertirlas en órdenes.
- Añadir tests de fallos de red y respuestas parciales del exchange.

Solo después de superar estas etapas debe diseñarse un módulo de ejecución Testnet.
La ejecución real debe permanecer fuera del alcance hasta contar con evidencia
fuera de muestra, paper trading estable, límites de pérdidas probados y una revisión
de seguridad independiente.

## Instrucciones para futuras modificaciones de Gemini

Antes de editar:

1. Lee `README.md` y este documento completos.
2. Revisa `git status` y conserva cambios del usuario.
3. Ejecuta los tests actuales.
4. Explica qué hipótesis de estrategia estás intentando mejorar.
5. Implementa cambios pequeños y reutilizables entre paper y backtest.
6. Añade o actualiza tests.
7. Ejecuta backtest dentro y fuera de muestra.
8. Reporta resultados positivos y negativos sin ocultar costes.
9. No cambies `.env` ni expongas su contenido.
10. No habilites producción.
