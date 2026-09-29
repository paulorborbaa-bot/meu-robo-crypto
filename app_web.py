import os
import time
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# ==========================================
# ESTADO GLOBAL DO ROBÔ
# ==========================================
estado_bot = {
    "rodando": False,
    "saldo": 50.00,
    "saldo_inicial": 50.00,
    "max_posicoes": 3,
    "posicoes_ativas": {},
    "historico_trades": [],
    "logs": ["🤖 Servidor Web V3 Crypto-Max iniciado na Nuvem. Aguardando comando..."],
    "stats": {"vitorias": 0, "derrotas": 0}
}

universo_cripto = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
    'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'NEARUSDT', 'SUIUSDT'
]

def adicionar_log(msg):
    timestamp = time.strftime("[%H:%M:%S]")
    estado_bot["logs"].append(f"{timestamp} {msg}")
    if len(estado_bot["logs"]) > 50:
        estado_bot["logs"].pop(0)

# ==========================================
# INTERFACE WEB AVANÇADA
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V3 Crypto-Max | Estratégia de Impulso</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 1050px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; margin-bottom: 20px; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card { background-color: #1e293b; padding: 18px; border-radius: 12px; border: 1px solid #334155; }
        .card h3 { margin: 0 0 8px 0; font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
        .card .value { font-size: 24px; font-weight: bold; color: #38bdf8; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; }
        .btn { padding: 12px 24px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 15px; transition: 0.2s; }
        .btn-start { background-color: #22c55e; color: #052e16; }
        .btn-start:hover { background-color: #16a34a; }
        .btn-stop { background-color: #ef4444; color: #450a0a; }
        .btn-stop:hover { background-color: #dc2626; }
        
        .section-title { font-size: 15px; font-weight: bold; color: #cbd5e1; margin: 20px 0 10px 0; display: flex; align-items: center; gap: 8px; }
        
        table { width: 100%; border-collapse: collapse; background-color: #1e293b; border-radius: 10px; overflow: hidden; margin-bottom: 20px; border: 1px solid #334155; }
        th, td { padding: 12px 15px; text-align: left; font-size: 13px; }
        th { background-color: #0f172a; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; }
        tr:not(:last-child) { border-bottom: 1px solid #334155; }
        
        .lucro-positivo { color: #22c55e; font-weight: bold; }
        .lucro-negativo { color: #ef4444; font-weight: bold; }
        
        .terminal-container { background-color: #020617; border: 1px solid #1e293b; border-radius: 12px; padding: 15px; }
        .terminal { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; height: 260px; overflow-y: auto; color: #38bdf8; font-size: 13px; line-height: 1.6; }
        .log-line { border-bottom: 1px solid #0f172a; padding: 3px 0; }
        .empty-row { text-align: center; color: #64748b; font-style: italic; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin:0;">🤖 V3 Crypto-Max Web</h2>
            <span style="font-size: 12px; background: #334155; padding: 4px 8px; border-radius: 4px;">Modo Impulso Ativo</span>
        </div>
        
        <!-- CARDS DE METRICAS -->
        <div class="card-grid">
            <div class="card">
                <h3>Banca Atual</h3>
                <div class="value" id="saldo">R$ 50.00</div>
            </div>
            <div class="card">
                <h3>Posições Abertas</h3>
                <div class="value" id="posicoes">0 / 3</div>
            </div>
            <div class="card">
                <h3>Taxa de Vitória</h3>
                <div class="value" id="winrate">0%</div>
            </div>
            <div class="card">
                <h3>Status do Robô</h3>
                <div class="value" id="status" style="color: #ef4444;">PARADO</div>
            </div>
        </div>

        <!-- CONTROLES -->
        <div class="controls">
            <button class="btn btn-start" onclick="iniciar()">▶️ Iniciar Robô</button>
            <button class="btn btn-stop" onclick="parar()">⏹️ Parar Robô</button>
        </div>

        <!-- TABELA DE POSIÇÕES ATIVAS -->
        <div class="section-title">📊 Posições em Aberto (PnL ao Vivo)</div>
        <table>
            <thead>
                <tr>
                    <th>Paridade</th>
                    <th>Preço Entrada</th>
                    <th>Preço Atual</th>
                    <th>Stop Loss (-1.5%)</th>
                    <th>Alvo (+3.0%)</th>
                    <th>Retorno (PnL %)</th>
                </tr>
            </thead>
            <tbody id="tabela-posicoes">
                <tr><td colspan="6" class="empty-row">Nenhuma posição aberta no momento.</td></tr>
            </tbody>
        </table>

        <!-- TERMINAL DE LOGS -->
        <div class="section-title">📜 Terminal de Operações ao Vivo</div>
        <div class="terminal-container">
            <div class="terminal" id="terminal"></div>
        </div>
        
        <!-- HISTÓRICO DE TRADES -->
        <div class="section-title" style="margin-top: 25px;">🏁 Histórico Recente de Trades</div>
        <table>
            <thead>
                <tr>
                    <th>Paridade</th>
                    <th>Resultado</th>
                    <th>Entrada</th>
                    <th>Saída</th>
                    <th>Lucro / Prejuízo (R$)</th>
                </tr>
            </thead>
            <tbody id="tabela-historico">
                <tr><td colspan="5" class="empty-row">Nenhum trade encerrado ainda.</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        const universo = [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
            'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'NEARUSDT', 'SUIUSDT'
        ];
        let idxMoeda = 0;
        let botRodando = false;
        
        // Memória local para guardar histórico de preços e detetar impulsos
        const historicoPrecos = {};

        async function buscarPrecoCliente(symbol) {
            try {
                const res = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}`);
                if (res.ok) {
                    const data = await res.json();
                    return parseFloat(data.price);
                }
            } catch (e) {
                try {
                    const base = symbol.replace('USDT', '-USD');
                    const resAlt = await fetch(`https://api.coinbase.com/v2/prices/${base}/spot`);
                    if (resAlt.ok) {
                        const dataAlt = await resAlt.json();
                        return parseFloat(dataAlt.data.amount);
                    }
                } catch (err) {}
            }
            return null;
        }

        async function loopAnalisar() {
            if (!botRodando) return;

            const par = universo[idxMoeda];
            const preco = await buscarPrecoCliente(par);

            let variacao = 0;
            if (preco && historicoPrecos[par]) {
                const precoAnterior = historicoPrecos[par];
                variacao = ((preco - precoAnterior) / precoAnterior) * 100;
            }
            
            if (preco) {
                historicoPrecos[par] = preco;
            }

            await fetch('/api/registrar_analise', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ par: par, preco: preco, variacao: variacao })
            });

            idxMoeda = (idxMoeda + 1) % universo.length;
        }

        async function atualizar() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                botRodando = data.rodando;
                document.getElementById('saldo').innerText = `R$ ${data.saldo.toFixed(2)}`;
                document.getElementById('posicoes').innerText = `${Object.keys(data.posicoes_ativas).length} / ${data.max_posicoes}`;
                
                // Win Rate
                const totalTrades = data.stats.vitorias + data.stats.derrotas;
                const winrate = totalTrades > 0 ? ((data.stats.vitorias / totalTrades) * 100).toFixed(0) : 0;
                document.getElementById('winrate').innerText = `${winrate}%`;

                // Status
                const statusEl = document.getElementById('status');
                if (data.rodando) {
                    statusEl.innerText = "RODANDO";
                    statusEl.style.color = "#22c55e";
                    await loopAnalisar();
                } else {
                    statusEl.innerText = "PARADO";
                    statusEl.style.color = "#ef4444";
                }

                // Tabela de Posições
                const posTable = document.getElementById('tabela-posicoes');
                const posKeys = Object.keys(data.posicoes_ativas);
                if (posKeys.length === 0) {
                    posTable.innerHTML = '<tr><td colspan="6" class="empty-row">Nenhuma posição aberta no momento.</td></tr>';
                } else {
                    posTable.innerHTML = posKeys.map(k => {
                        const p = data.posicoes_ativas[k];
                        const pnlClass = p.pnl >= 0 ? 'lucro-positivo' : 'lucro-negativo';
                        const sinal = p.pnl >= 0 ? '+' : '';
                        return `<tr>
                            <td><b>${p.par}</b></td>
                            <td>$${p.preco_entrada.toFixed(4)}</td>
                            <td>$${p.preco_atual.toFixed(4)}</td>
                            <td style="color:#ef4444;">$${p.stop.toFixed(4)}</td>
                            <td style="color:#22c55e;">$${p.target.toFixed(4)}</td>
                            <td class="${pnlClass}">${sinal}${p.pnl.toFixed(2)}%</td>
                        </tr>`;
                    }).join('');
                }

                // Histórico
                const histTable = document.getElementById('tabela-historico');
                if (data.historico_trades.length === 0) {
                    histTable.innerHTML = '<tr><td colspan="5" class="empty-row">Nenhum trade encerrado ainda.</td></tr>';
                } else {
                    histTable.innerHTML = data.historico_trades.slice(-5).reverse().map(h => {
                        const pnlClass = h.lucro >= 0 ? 'lucro-positivo' : 'lucro-negativo';
                        const sinal = h.lucro >= 0 ? '+' : '';
                        return `<tr>
                            <td><b>${h.par}</b></td>
                            <td>${h.resultado}</td>
                            <td>$${h.entrada.toFixed(4)}</td>
                            <td>$${h.saida.toFixed(4)}</td>
                            <td class="${pnlClass}">${sinal}R$ ${h.lucro.toFixed(2)}</td>
                        </tr>`;
                    }).join('');
                }

                // Terminal
                const terminal = document.getElementById('terminal');
                terminal.innerHTML = data.logs.map(log => `<div class="log-line">${log}</div>`).join('');
                terminal.scrollTop = terminal.scrollHeight;
            } catch (e) {
                console.error("Erro ao atualizar:", e);
            }
        }

        async function iniciar() { await fetch('/api/iniciar', { method: 'POST' }); atualizar(); }
        async function parar() { await fetch('/api/parar', { method: 'POST' }); atualizar(); }

        setInterval(atualizar, 2500);
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
    return jsonify(estado_bot)

@app.route('/api/registrar_analise', methods=['POST'])
def registrar_analise():
    if not estado_bot["rodando"]:
        return jsonify({"success": False})

    data = request.get_json()
    par = data.get('par')
    preco = data.get('preco')
    variacao = data.get('variacao', 0)

    par_formatado = f"{par[:-4]}/{par[-4:]}"

    if preco is not None:
        # Se o par já está numa posição aberta, atualiza PnL e verifica Stop/Target
        if par_formatado in estado_bot["posicoes_ativas"]:
            pos = estado_bot["posicoes_ativas"][par_formatado]
            pos["preco_atual"] = preco
            pos["pnl"] = ((preco - pos["preco_entrada"]) / pos["preco_entrada"]) * 100
            
            # Checa Stop Loss (-1.5%)
            if preco <= pos["stop"]:
                lucro_brl = (pos["pnl"] / 100) * (estado_bot["saldo"] / 3)
                estado_bot["saldo"] += lucro_brl
                estado_bot["stats"]["derrotas"] += 1
                estado_bot["historico_trades"].append({
                    "par": par_formatado, "resultado": "🛑 STOP LOSS",
                    "entrada": pos["preco_entrada"], "saida": preco, "lucro": lucro_brl
                })
                adicionar_log(f"🛑 [STOP LOSS ATINGIDO] {par_formatado} fechado a ${preco:.4f} ({lucro_brl:.2f} R$)")
                del estado_bot["posicoes_ativas"][par_formatado]
            
            # Checa Take Profit (+3.0%)
            elif preco >= pos["target"]:
                lucro_brl = (pos["pnl"] / 100) * (estado_bot["saldo"] / 3)
                estado_bot["saldo"] += lucro_brl
                estado_bot["stats"]["vitorias"] += 1
                estado_bot["historico_trades"].append({
                    "par": par_formatado, "resultado": "🎯 TAKE PROFIT",
                    "entrada": pos["preco_entrada"], "saida": preco, "lucro": lucro_brl
                })
                adicionar_log(f"🎯 [ALVO ATINGIDO] {par_formatado} fechado a ${preco:.4f} (+{lucro_brl:.2f} R$)")
                del estado_bot["posicoes_ativas"][par_formatado]

        # Se não está aberto, avalia a REGRA DE ENTRADA (Impulso / Variação)
        else:
            total_abertas = len(estado_bot["posicoes_ativas"])
            
            # Regra: Variação positiva rápida OU pequena variação acumulada quando houver espaço na carteira
            if total_abertas < estado_bot["max_posicoes"] and (variacao > 0.05 or variacao < -0.10):
                stop_loss = preco * 0.985   # -1.5%
                take_profit = preco * 1.030 # +3.0%
                
                estado_bot["posicoes_ativas"][par_formatado] = {
                    "par": par_formatado,
                    "preco_entrada": preco,
                    "preco_atual": preco,
                    "stop": stop_loss,
                    "target": take_profit,
                    "pnl": 0.0
                }
                adicionar_log(f"🚀 [COMPRA EXECUTADA] {par_formatado} a ${preco:.4f} | Variação: {variacao:+.2f}%")
            else:
                adicionar_log(f"🔍 Analisado {par_formatado} | Preço: ${preco:.4f} | Variação: {variacao:+.2f}%")
    else:
        adicionar_log(f"⚠️ Erro ao obter cotação de {par_formatado}")

    return jsonify({"success": True})

@app.route('/api/iniciar', methods=['POST'])
def iniciar():
    if not estado_bot["rodando"]:
        estado_bot["rodando"] = True
        adicionar_log("🚀 Comando recebido via Web: Robô INICIADO com Estratégia de Impulso.")
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
