# ⚽ Sistema de alerta de Jogos

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot-pyTelegramBotAPI-2CA5E0.svg)](https://core.telegram.org/bots)
[![Deployed on Render](https://img.shields.io/badge/Render-Hosted-46E3B7.svg)](https://render.com)

Assistente automatizado de transmissões esportivas. O sistema agrega jogos de futebol a partir de APIs externas, permite que os torcedores selecionem seus times favoritos por meio de uma interface Web autenticada via Telegram e dispara diariamente a agenda dos jogos com canais de transmissão diretamente no chat privado.

---

## 📌 Funcionalidades

- **Autenticação com Telegram Widget**: Login na interface Web sem senhas manuais, capturando o `chat_id` diretamente pela API oficial do Telegram.
- **Gerenciamento de Times Favoritos**: Painel Web responsivo para torcedores selecionarem seus clubes do coração.
- **Bot Interativo (Webhook)**: Recebimento de mensagens em tempo real via HTTP Webhooks hospedados na nuvem.
- **Pipeline de Dados & Seeder Automático**: Carga de ligas e clubes via API-Sports e FutPythonTrader, salvando países, campeonatos e equipes no PostgreSQL.
- **Agendamento com APScheduler**:
  - `03:00 AM`: Sincronização diária das partidas (*fixtures*) do dia.
  - `Matinal`: Disparo automático e customizado das agendas de transmissão para cada usuário cadastrado.

---

## 🏗️ Arquitetura do Sistema

```text
┌────────────────────────┐      ┌─────────────────────────┐
│     Usuário / Web      │      │     Telegram App        │
│  (select_favorites)    │      │  (Notificações /start)  │
└───────────▲────────────┘      └───────────▲─────────────┘
            │                               │
            │ HTTP                          │ Webhook (POST)
            ▼                               ▼
┌─────────────────────────────────────────────────────────┐
│                 FastAPI Application (Render)            │
│  ├── /telegram-webhook  (Dispatcher de Mensagens)       │
│  ├── /favoritos/{id}    (Seleção de Times)              │
│  ├── APScheduler        (Tarefas agendadas)             │
└───────────────────────────▲─────────────────────────────┘
                            │
              psycopg2 / SQL Queries
                            ▼
┌─────────────────────────────────────────────────────────┐
│             PostgreSQL Database (Render)                │
│  (users, teams, leagues, countries, user_favorites)     │
└─────────────────────────────────────────────────────────┘
