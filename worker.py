"""
KickBoost Cloud Worker 24/7
Runs continuously in GitHub Actions / Cloud Runner.
Zero PC required - 100% automated farm and vitrine entrance.
"""
import os
import sys
import time
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dlmctogvkgbabribpnvm.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN", "5nnv7alciejw")

if not SUPABASE_ANON_KEY:
    try:
        import json
        with open("kickboost_client_build/resources/app/config.json", "r") as f:
            cfg = json.load(f)
            SUPABASE_ANON_KEY = cfg["supabaseAnonKey"]
    except Exception:
        pass

def get_token():
    try:
        r = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"refresh_token": REFRESH_TOKEN},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception as e:
        print(f"[Auth Error] {e}")
    return None

def run_cycle():
    token = get_token()
    if not token:
        print("[Alerta] Nao foi possivel obter token de sessao.")
        return

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Heartbeat basico
    try:
        hb = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/registrar_heartbeat", headers=headers, json={"p_versao": "1.0.0"}, timeout=10)
        hb_data = hb.json() if hb.status_code == 200 else {}
    except Exception:
        hb_data = {}

    # 2. Heartbeat HyperIA
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

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}] Farm OK | Moedas: {pontos} | Vitrine: {na_vitrine} | Horas 24h: {horas}h/24h")

    # 3. Se ja tiver liberado o modo free (apos 24h) e nao estiver na vitrine, tenta entrar
    if liberado and not na_vitrine:
        try:
            ev = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/entrar_vitrine", headers=headers, json={"p_modo": "automatico"}, timeout=10)
            print(f"[*] Tentativa de entrada free na vitrine: {ev.status_code} {ev.text}")
        except Exception as e:
            print(f"[Erro Vitrine Free] {e}")

    # 4. Se tiver moedas suficientes (>= 120) e nao estiver na vitrine, compra 1 hora
    if pontos >= 120 and not na_vitrine:
        try:
            cb = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/comprar_tempo_vitrine", headers=headers, json={"p_horas": 1}, timeout=10)
            print(f"[*] Compra de vitrine com moedas: {cb.status_code} {cb.text}")
        except Exception as e:
            print(f"[Erro Compra Vitrine] {e}")

if __name__ == "__main__":
    # Roda em loop por aproximadamente 4.5 minutos para cobrir o intervalo do schedule do GitHub
    start_time = time.time()
    duration_seconds = int(os.environ.get("RUN_DURATION_SEC", "270"))  # 4m30s
    print(f"=== [KickBoost Cloud Worker Iniciado] ===")
    print(f"Duracao deste ciclo na nuvem: {duration_seconds} segundos")

    while time.time() - start_time < duration_seconds:
        run_cycle()
        time.sleep(45)

    print("=== [Ciclo na nuvem concluido com sucesso. Aguardando proximo disparo.] ===")
