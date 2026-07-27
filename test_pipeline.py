# test_pipeline.py
import sys
from app.services.football_api import schedule_fixtures
from app.services.scraper import msg_por_fixture
from app.telegram_bot import disparar_agenda_matinal_usuarios
from app.database.queries import obter_todos_usuarios_com_favoritos

def testar_pipeline_completo():
    print("==================================================")
    print("🧪 INICIANDO TESTE DO PIPELINE COMPLETO")
    print("==================================================\n")

    # ----------------------------------------------------
    # TESTE 1: Carga da API (Simulando as 03:00)
    # ----------------------------------------------------
    print("1️⃣ [TESTE 03:00] Testando busca na API-Sports e popular fixtures...")
    try:
        schedule_fixtures()
        print("   👉 Verifique seu banco no DBeaver/pgAdmin: a tabela 'fixtures' deve ter registros do dia!\n")
    except Exception as e:
        print(f"   ❌ Erro no Teste 1: {e}\n")
        return

    # ----------------------------------------------------
    # TESTE 2: Scraper + Atualização do Banco (Simulando as 07:45)
    # ----------------------------------------------------
    print("2️⃣ [TESTE 07:45] Executando scraper e geração do mapa de mensagens...")
    mensagens_por_time = msg_por_fixture()
    print(f"   👉 Chaves geradas no dicionário/JSON: {len(mensagens_por_time)}")
    
    # Exibe uma amostra do texto formatado
    if mensagens_por_time:
        primeira_chave = list(mensagens_por_time.keys())[0]
        print("\n   --- Exemplo de Mensagem Gerada ---")
        print(mensagens_por_time[primeira_chave])
        print("   -----------------------------------\n")
    else:
        print("   ⚠️ Atenção: Nenhuma mensagem foi gerada. Verifique se o scraper encontrou jogos ou se a tabela fixtures tem partidas hoje.\n")

    # ----------------------------------------------------
    # TESTE 3: Verificação de Usuários com Favoritos
    # ----------------------------------------------------
    print("3️⃣ [TESTE BANCO] Buscando usuários e favoritos agrupados...")
    usuarios = obter_todos_usuarios_com_favoritos()
    print(f"   👉 Total de usuários encontrados com favoritos: {len(usuarios)}")
    for u in usuarios:
        print(f"      - Chat ID: {u[1]} | Favoritos (IDs): {u[2]}")
    print()

    # ----------------------------------------------------
    # TESTE 4: Disparo Final via Telegram (Simulando as 08:00)
    # ----------------------------------------------------
    confirmacao = input("4️⃣ [TESTE 08:00] Deseja disparar as mensagens REAIS para o Telegram agora? (s/n): ")
    if confirmacao.lower() == 's':
        print("   🚀 Disparando mensagens...")
        disparar_agenda_matinal_usuarios(mensagens_por_time)
        print("   ✅ Teste concluído! Cheque o aplicativo do Telegram no seu celular.\n")
    else:
        print("   ⏭️ Disparo via Telegram pulado pelo usuário.\n")

    print("==================================================")
    print("🎉 TESTE FINALIZADO!")
    print("==================================================")

if __name__ == "__main__":
    testar_pipeline_completo()