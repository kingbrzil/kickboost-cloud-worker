"""
KickBoost Cloud Worker 24/7 - Multi-Account Syndicate & Auto-Vitrine (30 Operarios)
Runs in GitHub Actions / Cloud.
Farms on main account + 30 ghost accounts in parallel.
Transfers all farmed coins to main account and buys Vitrine Slot 1 automatically.
"""
import os
import sys
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dlmctogvkgbabribpnvm.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
MAIN_REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN", "5nnv7alciejw")
MAIN_USER_ID = "bfcebab7-b5ba-4747-96fd-b2b48a7a5819"

# Load 30 ghost accounts
GHOSTS = []
try:
    if os.path.exists("sindicato_contas.json"):
        with open("sindicato_contas.json", "r", encoding="utf-8") as f:
            GHOSTS = json.load(f)
except Exception as e:
    print(f"[Aviso] Nao foi possivel carregar sindicato_contas.json: {e}")

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
    print(f"Contas no Sindicato: 1 Principal + {len(GHOSTS)} Operarios Fantasmas")

    while time.time() - start_time < duration_seconds:
        process_main_account()
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(process_ghost_account, GHOSTS)
        time.sleep(45)

    print("=== [Ciclo do Sindicato concluido com sucesso.] ===")
