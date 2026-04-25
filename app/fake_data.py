from datetime import date


def buscar_jogos_fake():

    hoje = date.today().isoformat()
    return [
        {
            "home": "Fluminense",
            "away": "Palmeiras",
            "date": hoje,
            "time": "21:30"
        },
        {
            "home": "Vasco",
            "away": "Botafogo",
            "date": hoje,
            "time": "18:00"
        }
    ]