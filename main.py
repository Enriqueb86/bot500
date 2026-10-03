import time
from strategies.base_strategy import BaseStrategy


def main():
  print("Iniciando Bot de Trading con Gemini AI...")
  strategy = BaseStrategy()

  # Bucle principal de ejecución (Ejemplo: evalúa el mercado cada 60 segundos en modo prueba)
  try:
    while True:
      strategy.run_cycle()
      print("Esperando próximo ciclo en 60 segundos...")
      time.sleep(60)
  except KeyboardInterrupt:
    print("\nBot detenido manualmente por el usuario.")


if __name__ == "__main__":
  main()