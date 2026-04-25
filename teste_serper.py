import requests
import json

def buscar_transmissao_viva(time_casa, time_fora):
    url = "https://google.serper.dev/search"
    
    # Query potente para o Google entender que queremos o canal de TV
    query = f"lista de canais de transmissão {time_casa} x {time_fora} hoje"
    
    payload = json.dumps({
        "q": query,
        "gl": "br",  
        "hl": "pt-br",  
        "autocorrect": True
    })
    
    headers = {
        'X-API-KEY': 'dfceee3f5cfa933668492cf0fc80dd63a98e17be',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        results = response.json()
        
        if "answerBox" in results:
            return results["answerBox"].get("answer") or results["answerBox"].get("snippet")
        
        if "organic" in results and len(results["organic"]) > 0:
            return results["organic"][0]["snippet"]
            
        return "Informação de transmissão não encontrada."
        
    except Exception as e:
        print(f"Erro no Serper: {e}")
        return "Erro ao buscar transmissão."
    

def extrair_canais(texto_bruto):
    canais_conhecidos = [
        "Globo", "Record", "SBT", "Band", "SporTV", "Premiere", 
        "ESPN", "CazéTV", "Max", "TNT", "Disney+", "Paramount+", "Star+"
    ]
    
    achados = []
    for canal in canais_conhecidos:
        if canal.lower() in texto_bruto.lower():
            achados.append(canal)
    
    if achados:
        return "📺 " + ", ".join(achados)
    return "📺 Verifique o guia local"


resultado = buscar_transmissao_viva("Fluminense", "Chapecoense")
print(f"📺 Transmissão encontrada: {resultado}")