from app.football_api import buscar_jogos_do_dia

def testar_api():
    print("📡 Chamando API...")
    jogos = buscar_jogos_do_dia()
    if not jogos:
        print("❌ Nenhum jogo retornado (ou erro na chave).")
    else:
        for jogo in jogos:
            print(f"✅ {jogo['horario']} - {jogo['casa']} x {jogo['fora']}")

if __name__ == "__main__":
    testar_api()