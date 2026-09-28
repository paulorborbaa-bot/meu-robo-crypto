import os
import time
import threading
from flask import Flask, render_template_string, jsonify
import ccxt
import pandas as pd
import numpy as np

app = Flask(__name__)

# ==========================================
# ESTADO GLOBAL DO ROBÔ
# ==========================================
estado_bot = {
    "rodando": False,
    "saldo": 50.00,
    "max_posicoes": 3,
    "posicoes_ativas": {},
    "logs": ["🤖 Servidor Web V3 Crypto-Max iniciado na Nuvem. Aguardando comando..."]
}

exchange = ccxt.binance({'enableRateLimit': True})

universo_cripto = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
    'ADA/USDT', 'AVAX/USDT', 'LINK/USDT', 'NEAR/USDT', 'SUI/USDT',
    'FET/USDT', 'RENDER/USDT', 'INJ/USDT', 'OP/USDT', 'ARB/USDT',
    'MATIC/USDT', 'ATOM/USDT', 'AAVE/USDT', 'LTC/USDT', 'BCH/USDT'
]

def adicionar_log(msg):
    timestamp = time.strftime("[%H:%M:%S]")
    estado_bot["logs"].append(f"{timestamp} {msg}")
    if len(estado_bot["logs"]) > 60:
        estado_bot["logs"].pop(0)

# ==========================================
# CÁLCULOS E INDICADORES TÉCNICOS
# ==========================================
def buscar_dados(simbolo, timeframe='1h', limit=200):
    try:
        ohlcv = exchange.fetch_ohlcv(simbolo, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        return None

def calcular_indicadores(df):
    df = df.copy()
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    ganho = (delta.where(delta > 0, 0)).rolling(14).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = ganho / (perda + 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    up = df['high'] - df['high'].shift()
    down = df['low'].shift() - df['low']
    p_dm = np.where((up > down) & (up > 0), up, 0.0)
    m_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr_s = tr.rolling(14).sum()
    p_di = 100 * (pd.Series(p_dm, index=df.index).rolling(14).sum() / (tr_s + 1e-9))
    m_di = 100 * (pd.Series(m_dm, index=df.index).rolling(14).sum() / (tr_s + 1e-9))
    dx = 100 * (p_di - m_di).abs() / (p_di + m_di + 1e-9)
    df['adx'] = dx.rolling(14).mean()
    
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['forte_volume'] = df['volume'] > (df['vol_ma'] * 1.5)
    
    return df

def executar_scanner():
    adicionar_log("🔍 Escaneando as 20 moedas no mercado...")
    
    df_btc = buscar_dados('BTC/USDT')
    if df_btc is None:
        adicionar_log("⚠️ Erro de conexão ao buscar BTC na Binance.")
        return
        
    df_btc = calcular_indicadores(df_btc)
    btc_close = df_btc['close'].iloc[-1]
    btc_ema200 = df_btc['ema_200'].iloc[-1]
    
    if btc_close < btc_ema200:
        adicionar_log(f"🛑 [TRAVA MACRO] BTC em tendência de baixa (${btc_close:.2f} <${btc_ema200:.2f}). Novas entradas bloqueadas.")
        return

    if len(estado_bot["posicoes_ativas"]) >= estado_bot["max_posicoes"]:
        adicionar_log("🔒 Limite máximo de 3 posições simultâneas mantido. Monitorando posições abertas.")
        return

    candidatos = []
    for par in universo_cripto:
        if not estado_bot["rodando"]:
            return
        if par in estado_bot["posicoes_ativas"]:
            continue
            
        df = buscar_dados(par)
        if df is None or len(df) < 200:
            continue
            
        df_ind = calcular_indicadores(df)
        row = df_ind.iloc[-1]
        
        gatilho = (
            row['close'] > row['ema_200'] and
            row['ema_9'] > row['ema_21'] and
            row['adx'] >= 28 and
            55 <= row['rsi'] <= 70 and
            row['forte_volume']
        )
        
        if gatilho:
            candidatos.append({
                'par': par,
                'preco': float(row['close']),
                'adx': float(row['adx']),
                'stop': float(row['close'] - (row['atr'] * 2.0)),
                'target': float(row['close'] + (row['atr'] * 4.5))
            })

    if candidatos:
        candidatos.sort(key=lambda x: x['adx'], reverse=True)
        escolhido = candidatos[0]
        estado_bot["posicoes_ativas"][escolhido['par']] = escolhido
        p = escolhido['preco']
        st = escolhido['stop']
        tg = escolhido['target']
        par_nome = escolhido['par']
        msg_log = f"🔥 [ENTRADA EXECUTADA] {par_nome} | Entrada: ${p:.4f} | Stop: ${st:.4f} | Alvo: ${tg:.4f}"
        adicionar_log(msg_log)
    else:
        adicionar_log("✅ Escaneamento concluído: Mercado sem oportunidades dentro do filtro no momento.")

# ==========================================
# ENGINE DE SEGUNDO PLANO (THREAD)
# ==========================================
def motor_robo():
    while True:
        if estado_bot["rodando"]:
            executar_scanner()
            for _ in range(3600):
                if not estado_bot["rodando"]:
                    break
                time.sleep(1)
        else:
            time.sleep(2)

thread_engine = threading.Thread(target=motor_robo, daemon=True)
thread_engine.start()

# ==========================================
# INTERFACE WEB (HTML + CSS + JS)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V3 Crypto-Max | Dashboard Web</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; margin-bottom: 20px; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card { background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; }
        .card h3 { margin: 0 0 10px 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; }
        .card .value { font-size: 26px; font-weight: bold; color: #38bdf8; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; }
        .btn { padding: 12px 24px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 15px; transition: 0.2s; }
        .btn-start { background-color: #22c55e; color: #052e16; }
        .btn-start:hover { background-color: #16a34a; }
        .btn-stop { background-color: #ef4444; color: #450a0a; }
        .btn-stop:hover { background-color: #dc2626; }
        .terminal-container { background-color: #020617; border: 1px solid #1e293b; border-radius: 12px; padding: 15px; }
        .terminal-header { font-size: 14px; font-weight: bold; color: #94a3b8; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        .terminal { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; height: 350px; overflow-y: auto; color: #38bdf8; font-size: 13px; line-height: 1.6; }
        .log-line { border-bottom: 1px solid #0f172a; padding: 2px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin:0;">🤖 V3 Crypto-Max Web</h2>
            <span style="font-size: 12px; background: #334155; padding: 4px 8px; border-radius: 4px;">Render Cloud Engine</span>
        </div>
        
        <div class="card-grid">
            <div class="card">
                <h3>Saldo Reinvestido</h3>
                <div class="value" id="saldo">R$ 50,00</div>
            </div>
            <div class="card">
                <h3>Posições Abertas</h3>
                <div class="value" id="posicoes">0 / 3</div>
            </div>
            <div class="card">
                <h3>Status do Robô</h3>
                <div class="value" id="status" style="color: #ef4444;">PARADO</div>
            </div>
        </div>

        <div class="controls">
            <button class="btn btn-start" onclick="iniciar()">▶️ Iniciar Robô</button>
            <button class="btn btn-stop" onclick="parar()">⏹️ Parar Robô</button>
        </div>

        <div class="terminal-container">
            <div class="terminal-header">📜 Terminal de Operações ao Vivo</div>
            <div class="terminal" id="terminal"></div>
        </div>
    </div>

    <script>
        async function atualizar() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('saldo').innerText = `R$ ${data.saldo.toFixed(2)}`;
                document.getElementById('posicoes').innerText = `${Object.keys(data.posicoes_ativas).length} / ${data.max_posicoes}`;
                
                const statusEl = document.getElementById('status');
                if (data.rodando) {
                    statusEl.innerText = "RODANDO";
                    statusEl.style.color = "#22c55e";
                } else {
                    statusEl.innerText = "PARADO";
                    statusEl.style.color = "#ef4444";
                }

                const terminal = document.getElementById('terminal');
                terminal.innerHTML = data.logs.map(log => `<div class="log-line">${log}</div>`).join('');
                terminal.scrollTop = terminal.scrollHeight;
            } catch (e) {
                console.error("Erro ao atualizar painel:", e);
            }
        }

        async function iniciar() { await fetch('/api/iniciar', { method: 'POST' }); atualizar(); }
        async function parar() { await fetch('/api/parar', { method: 'POST' }); atualizar(); }

        setInterval(atualizar, 3000);
        atualizar();
    </script>
</body>
</html>
"""

# ==========================================
# ROTAS DA API WEB
# ==========================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def status():
    return jsonify(estado_bot)

@app.route('/api/iniciar', methods=['POST'])
def iniciar():
    estado_bot["rodando"] = True
    adicionar_log("🚀 Comando recebido via Web: Robô INICIADO.")
    return jsonify({"success": True})

@app.route('/api/parar', methods=['POST'])
def parar():
    estado_bot["rodando"] = False
    adicionar_log("🛑 Comando recebido via Web: Robô PARADO.")
    return jsonify({"success": True})

# ==========================================
# INICIALIZAÇÃO ADAPTADA PARA O RENDER
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
