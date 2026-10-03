import os
import sys
import pandas as pd
from datetime import datetime

# Añadir el directorio raíz al path para importar módulos correctamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import TradeLogger

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear_screen()
    print("=" * 65)
    print(" 🚀 CRYPTO BOT - DASHBOARD DE RENDIMIENTO")
    print("=" * 65)
    print(f"🕒 Fecha de consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Análisis del archivo CSV de trades dentro de la carpeta logs/
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(root_dir, 'logs', 'trades_history.csv')
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            print(f"📂 Historial de trades cargado desde: logs/trades_history.csv")
            print(f"📊 Total de operaciones registradas: {len(df)}")
            
            if not df.empty:
                print("\n--- Últimas Operaciones ---")
                print(df.tail(5).to_string(index=False))
        except Exception as e:
            print(f"⚠️ Error al leer el archivo CSV: {e}")
    else:
        print("⚠️ No se encontró el archivo `trades_history.csv` en la carpeta `logs/`.")

    print("\n" + "-" * 65)
    print("📈 Métricas Calculadas (TradeLogger):")
    
    # 2. Reporte desde el TradeLogger
    try:
        logger = TradeLogger()
        report = logger.generate_performance_report()
        
        if isinstance(report, dict):
            for key, value in report.items():
                formatted_key = key.replace('_', ' ').capitalize()
                print(f"  • {formatted_key}: {value}")
        else:
            print(f"  {report}")
            
    except Exception as e:
        print(f"  ⚠️ No se pudieron obtener las métricas del logger: {e}")
        
    print("=" * 65)

if __name__ == "__main__":
    main()