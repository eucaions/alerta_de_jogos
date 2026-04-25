from datetime import date

def formatar_lista_jogos(jogos: list) -> str:
    # 1. Pegamos a data de hoje para formatar o título e filtrar
    hoje_obj = date.today()
    # Se a sua API já retorna apenas jogos de hoje, o filtro abaixo é opcional, 
    # mas vamos mantê-lo por segurança se você passar a lista bruta.
    
    if not jogos:
        return "⚽ Nenhum jogo de destaque encontrado para hoje."

    mensagem = (
        f"⚽ *Jogos de hoje — {hoje_obj.strftime('%d/%m/%Y')}*\n\n"
    )

    for jogo in jogos:
        # Usamos .get() para evitar que o bot trave se faltar alguma informação
        liga = jogo.get("liga", "Outros")
        casa = jogo.get("casa", "Time A")
        fora = jogo.get("fora", "Time B")
        horario = jogo.get("horario", "--:--")
        transmissao = jogo.get("transmissao", "Consultar guias")

        # Montando o bloco de cada jogo
        linha = (
            f"🏆 *{liga}*\n"
            f"🏟 {casa} x {fora}\n"
            f"🕒 Horário: {horario}\n"
            f"📺 {transmissao}\n"
            f"----------------------------\n"
        )

        mensagem += linha

    mensagem += "\nBom jogo! 🎫"

    return mensagem