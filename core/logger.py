import csv
import os
from datetime import datetime


class TradeLogger:

  def __init__(self, filename="logs/trades_history.csv"):
    self.filename = filename
    os.makedirs(os.path.dirname(self.filename), exist_ok=True)
    
    if not os.path.exists(self.filename):
      with open(self.filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "action", "price", "size", "pnl", "balance_after", "reason"
        ])

  def log_trade(self, action: str, price: float, size: float, pnl: float, balance: float, reason: str):
    with open(self.filename, mode='a', newline='') as f:
      writer = csv.writer(f)
      writer.writerow([
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          action,
          price,
          size,
          round(pnl, 2),
          round(balance, 2),
          reason
      ])

  def generate_performance_report(self) -> dict:
    if not os.path.exists(self.filename):
      return {"status": "No hay historial de operaciones aún."}

    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    total_profit = 0.0
    total_loss = 0.0

    with open(self.filename, mode='r') as f:
      reader = csv.DictReader(f)
      for row in reader:
        if row["action"] in ["VENTA", "CIERRE"]:
          total_trades += 1
          pnl = float(row["pnl"])
          if pnl > 0:
            winning_trades += 1
            total_profit += pnl
          else:
            losing_trades += 1
            total_loss += abs(pnl)

    if total_trades == 0:
      return {"mensaje": "Faltan operaciones cerradas para calcular métricas."}

    win_rate = (winning_trades / total_trades) * 100
    profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

    return {
        "Total Operaciones": total_trades,
        "Operaciones Ganadoras": winning_trades,
        "Operaciones Perdedoras": losing_trades,
        "Win Rate (%)": round(win_rate, 2),
        "Profit Factor": round(profit_factor, 2),
        "Beneficio Neto ($)": round(total_profit - total_loss, 2)
    }