import os
import time
from flask import Flask, render_template_string, jsonify
import ccxt

app = Flask(__name__)

# ==========================================
# ESTADO GLOBAL DO ROBÔ
# ==========================================
estado_bot = {
    "rodando": False,
    "saldo": 50.00,
    "max_posicoes": 3,
    "posicoes_ativas": {},
    "logs": ["🤖 Servidor Web V3 Crypto-Max iniciado na Nuvem. Aguardando comando..."],
    "indice_moeda": 0
}

# Inicialização simplificada da Binance
exchange = ccxt.binance({
    'enableRateLimit': True,
    'timeout': 5000
})

universo_cripto = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
    'ADA/USDT', 'AVAX/USDT', 'LINK/USDT', 'NEAR/USDT', 'SUI/USDT',
    'FET/USDT', 'RENDER/USDT', 'INJ/USDT', 'OP/USDT', 'ARB/USDT'
]

def adicionar_log(msg):
    timestamp = time.strftime("[%H:%M:%S]")
    estado_bot["logs"].append(f"{timestamp} {msg}")
    if len(estado_bot["logs"]) > 50:
        estado_bot["logs"].pop(0)

def processar_passo():
    """ Executa um único passo da varredura a cada atualização do site """
    if not estado_bot["rodando"]:
        return

    idx = estado_bot["indice_moeda"]
    par = universo_cripto[idx]
    
    try:
        ticker = exchange.fetch_ticker(par)
        preco = ticker['last']
        adicionar_log(f"🔍 Analisado {par} | Preço Atual: ${preco:.4f} | Sem sinal de entrada")
    except Exception as e:
        adicionar_log(f"⚠️ Erro ao consultar {par}: verificação ignorada")

    # Avança para a próxima moeda do universo
    estado_bot["indice_moeda"] = (idx + 1) % len(universo_cripto)

# ==========================================
# INTERFACE WEB
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V3 Crypto-Max | Dashboard Web</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
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
        .terminal-header { font-size: 14px; font-weight: bold; color: #94a3b8; margin-bottom: 10px; }
        .terminal { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; height: 350px; overflow-y: auto; color: #38bdf8; font-size: 13px; line-height: 1.6; }
        .log-line { border-bottom: 1px solid #0f172a; padding: 3px 0; }
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
                <div class="value" id="saldo">R$ 50.00</div>
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
                console.error("Erro ao atualizar terminal:", e);
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
# ROTAS DA API
# ==========================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def status():
    processar_passo()
    return jsonify(estado_bot)

@app.route('/api/iniciar', methods=['POST'])
def iniciar():
    if not estado_bot["rodando"]:
        estado_bot["rodando"] = True
        estado_bot["indice_moeda"] = 0
        adicionar_log("🚀 Comando recebido via Web: Robô INICIADO.")
    return jsonify({"success": True})

@app.route('/api/parar', methods=['POST'])
def parar():
    if estado_bot["rodando"]:
        estado_bot["rodando"] = False
        adicionar_log("🛑 Comando recebido via Web: Robô PARADO.")
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
