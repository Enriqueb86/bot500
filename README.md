# Crypto Bot — paper trading

Bot long-only para observar una estrategia tecnica en velas de una hora. Las
senales son deterministas y Gemini puede habilitarse como filtro opcional. La
ejecucion real esta intencionalmente bloqueada.

## Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Conserva tu `GEMINI_API_KEY` existente si ya tienes un `.env`. Por defecto
`AI_ENABLED=false`: esto permite medir primero la estrategia tecnica sin que un
modelo cambiante altere el experimento.

Cuando quieras medir la variante con el filtro de IA, cambia en `.env`:

```dotenv
AI_ENABLED=true
GEMINI_MODEL=gemini-3.8-flash
```

Gemini solo se consulta cuando ya existe una senal tecnica de compra. Un error,
respuesta invalida o confianza insuficiente rechaza la entrada de forma segura.

## Uso

Un ciclo, recomendado para verificar la configuracion:

```bash
python main.py --once
```

Ejecucion continua:

```bash
python main.py
```

Estado, posiciones y rendimiento:

```bash
python main.py --dashboard
```

Backtest tecnico (sin Gemini):

```bash
python backtest.py --symbol BTC/USDT --candles 2000
```

Tambien se puede usar un CSV con columnas `timestamp,open,high,low,close,volume`:

```bash
python backtest.py --symbol BTC/USDT --csv datos.csv
```

Tests locales, sin llamadas a Binance ni Gemini:

```bash
python -m unittest discover -s tests -v
```

## Archivos generados

- `state/paper_state.json`: saldo, posiciones y ultima vela procesada.
- `logs/signals.csv`: todas las decisiones tecnicas y de Gemini.
- `logs/trades.csv`: aperturas y cierres con P&L y costes.
- `logs/equity.csv`: curva de capital, exposicion y drawdown.

Estos archivos no se versionan. Para comenzar un experimento nuevo, detén el bot,
respalda los logs que quieras conservar y elimina manualmente el estado y los CSV.

## Seguridad

- `PAPER_TRADING=false` hace que el programa se niegue a arrancar.
- El bot no configura claves del exchange ni contiene codigo para enviar ordenes.
- Gemini nunca autoriza retiros ni interactua con la cuenta del exchange.
- No uses dinero real hasta completar backtests fuera de muestra y varias semanas
  de paper trading con costes realistas.
