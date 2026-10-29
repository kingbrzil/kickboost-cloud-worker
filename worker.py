"""
KickBoost Cloud Worker 24/7 - Multi-Account Syndicate & Auto-Vitrine
Runs in GitHub Actions / Cloud.
Farms on main account + 5 ghost accounts in parallel.
Transfers all farmed coins to main account and buys Vitrine Slot 1 automatically.
"""
import os
import sys
import time
import json
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dlmctogvkgbabribpnvm.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
MAIN_REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN", "5nnv7alciejw")
MAIN_USER_ID = "bfcebab7-b5ba-4747-96fd-b2b48a7a5819"

# Load ghost accounts
GHOSTS = [
    {"nome": "Operario 1", "refresh_token": "414e8259-rt", "id": "414e8259-edab-4278-a4f3-85794730ab2f"},
    {"nome": "Operario 2", "refresh_token": "1bc0a11a-rt", "id": "1bc0a11a-fc68-421c-a6b9-8368dfb6989c"},
    {"nome": "Operario 3", "refresh_token": "730ac196-rt", "id": "730ac196-1bca-407b-bf74-17c4e3e4f1af"},
    {"nome": "Operario 4", "refresh_token": "71ec679a-rt", "id": "71ec679a-f431-495e-a1e5-55d8dca81907"},
    {"nome": "Operario 5", "refresh_token": "35403fd7-rt", "id": "35403fd7-dbfb-4edf-87ee-99d7fb3e3339"}
]

# Read exact refresh tokens from sindicato_contas.json if present
try:
    if os.path.exists("sindicato_contas.json"):
        with open("sindicato_contas.json", "r", encoding="utf-8") as f:
            GHOSTS = json.load(f)
except Exception:
    pass

def get_token(refresh_tok):
    try:
        r = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"refresh_token": refresh_tok},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception as e:
        print(f"[Auth Error {refresh_tok[:8]}] {e}")
    return None

def process_main_account():
    token = get_token(MAIN_REFRESH_TOKEN)
    if not token:
        return

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        hb = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/registrar_heartbeat", headers=headers, json={"p_versao": "1.0.0"}, timeout=10)
        hb_data = hb.json() if hb.status_code == 200 else {}
    except Exception:
        hb_data = {}

    try:
        hh = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/registrar_heartbeat_hyperia", headers=headers, json={}, timeout=10)
        hh_data = hh.json() if hh.status_code == 200 else {}
    except Exception:
        hh_data = {}

    pontos = hb_data.get("pontos_total", 0)
    na_vitrine = hb_data.get("na_vitrine", False)
    acumulado_seg = hh_data.get("acumulado_seg", 0)
    horas = round(acumulado_seg / 3600, 2)
    liberado = hh_data.get("liberado", False)

    print(f"[{time.strftime('%H:%M:%S UTC')}] [CONTA PRINCIPAL] Moedas: {pontos} | Vitrine: {na_vitrine} | Horas 24h: {horas}h/24h")

    # Se moedas >= 120 e nao esta na vitrine, compra vitrine (Estrategia 2: Slot 1)
    if pontos >= 120 and not na_vitrine:
        try:
            cb = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/comprar_tempo_vitrine", headers=headers, json={"p_horas": 1}, timeout=10)
            print(f"[★ COMPRA VITRINE] Status: {cb.status_code} Resposta: {cb.text}")
        except Exception as e:
            print(f"[Erro Compra Vitrine] {e}")

    # Se bateu as 24h e liberou o modo free
    if liberado and not na_vitrine:
        try:
            ev = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/entrar_vitrine", headers=headers, json={"p_modo": "automatico"}, timeout=10)
            print(f"[★ VITRINE FREE] Status: {ev.status_code} Resposta: {ev.text}")
        except Exception as e:
            print(f"[Erro Vitrine Free] {e}")

def process_ghost_account(ghost):
    rt = ghost.get("refresh_token")
    nome = ghost.get("nome", "Fantasma")
    token = get_token(rt)
    if not token:
        return

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Heartbeat
    try:
        hb = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/registrar_heartbeat", headers=headers, json={"p_versao": "1.0.0"}, timeout=10)
        hb_data = hb.json() if hb.status_code == 200 else {}
    except Exception:
        hb_data = {}

    pontos = hb_data.get("pontos_total", 0)
    print(f"  -> [{nome}] Farm OK | Moedas: {pontos}")

    # Se tiver pelo menos 10 moedas (minimo de transferencia), drena tudo pra conta principal!
    if pontos >= 10:
        try:
            tr = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/transferir_moedas",
                headers=headers,
                json={"p_destinatario_id": MAIN_USER_ID, "p_quantidade": pontos},
                timeout=10
            )
            print(f"  [$$$ DRENO] {nome} transferiu {pontos} moedas -> Conta Principal! Resultado: {tr.status_code} {tr.text}")
        except Exception as e:
            print(f"  [Erro Transferencia {nome}] {e}")

if __name__ == "__main__":
    start_time = time.time()
    duration_seconds = int(os.environ.get("RUN_DURATION_SEC", "270"))
    print(f"=== [KickBoost Sindicato 24/7 Ativo] ===")
    print(f"Contas no Sindicato: 1 Principal + {len(GHOSTS)} Fantasmas")

    while time.time() - start_time < duration_seconds:
        process_main_account()
        for g in GHOSTS:
            process_ghost_account(g)
        time.sleep(45)

    print("=== [Ciclo do Sindicato concluido com sucesso.] ===")
