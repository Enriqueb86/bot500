import json
from google import genai
from google.genai import types
from config.settings import GEMINI_API_KEY


class GeminiAnalyst:

  def __init__(self):
    # Inicializa el cliente oficial de Gemini con tu API Key
    self.client = genai.Client(api_key=GEMINI_API_KEY)

  def analyze_market(self, market_data: dict, news_summary: str = "Sin noticias macro recientes.") -> dict:
    """Envía los datos técnicos y el contexto de noticias a Gemini 

    para obtener una decisión analítica estricta en formato JSON.
    """
    prompt = f"""
        Eres un analista cuantitativo experto en trading de criptomonedas. 
        Analiza los siguientes indicadores técnicos actuales y el contexto de mercado.
        
        Debes responder ESTRICTAMENTE en formato JSON válido (sin bloques de código markdown adicionales si es posible, o asegurando que sea parseable) 
        con las siguientes claves exactas:
        - "decision": (string con valores permitidos: "COMPRAR", "VENDER", "MANTENER")
        - "confianza": (número entero del 0 al 100 indicando tu nivel de seguridad)
        - "razon": (string breve explicando el motivo técnico y de contexto)

        Indicadores Técnicos Actuales:
        {json.dumps(market_data, indent=2)}

        Noticias / Contexto Macro:
        {news_summary}
        """

    try:
      # Actualizamos al modelo recomendado por la API
      response = self.client.models.generate_content(
          model="gemini-3.8-flash",
          contents=prompt,
          config=types.GenerateContentConfig(
              response_mime_type="application/json",
              temperature=0.1,
          ),
      )
      
      # Parsear el texto devuelto como diccionario de Python
      result = json.loads(response.text)
      return result

    except Exception as e:
      print(f"[Error] En analista de IA Gemini: {e}")
      return {
          "decision": "MANTENER",
          "confianza": 0,
          "razon": f"Fallo al procesar respuesta de IA: {str(e)}"
      } 