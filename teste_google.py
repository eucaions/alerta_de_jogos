import requests

# Suas chaves
API_KEY = "AIzaSyCF0pUgFxe5V8sUq1GotbgkvFE67HyWchQ"
CX = "b30be1f8ff3cc4940"

def testar_google(time_a, time_b):
    print(f"🔍 Buscando transmissão: {time_a} x {time_b}...")
    
    query = f"onde assistir {time_a} x {time_b} hoje transmissão"
    url = f"https://www.googleapis.com/customsearch/v1"
    
    params = {
        "key": API_KEY,
        "cx": CX,
        "q": query,
        "gl": "br",  # Geolocalização Brasil
        "hl": "pt-br" # Idioma Português
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "items" in data:
            # Pegamos o snippet do primeiro resultado
            primeiro_resultado = data["items"][0]["snippet"]
            print("\n📝 Resultado do Google:")
            print("-" * 30)
            print(primeiro_resultado)
            print("-" * 30)
            
            # Teste de extração simples
            canais = ["Globo", "SporTV", "Premiere", "ESPN", "CazéTV", "Max", "TNT", "Disney+"]
            encontrados = [c for c in canais if c.lower() in primeiro_resultado.lower()]
            print(f"📺 Canais detectados: {', '.join(encontrados) if encontrados else 'Nenhum identificado no texto'}")
        else:
            print("❌ Erro: O Google não retornou resultados. Verifique se o seu CX está configurado para 'Pesquisar na Web Inteira'.")
            print(f"Resposta da API: {data}")

    except Exception as e:
        print(f"💥 Erro na requisição: {e}")

if __name__ == "__main__":
    # Teste com um jogo que você sabe que vai acontecer ou aconteceu recentemente
    testar_google("Fluminense", "Chapecoense")