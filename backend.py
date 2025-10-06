# -*- coding: utf-8 -*-
"""
Backend para o projeto AirQ-SAT.
API RESTful para servir, gravar e processar dados de qualidade do ar via openEO.
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import time
from datetime import datetime
import re
import unicodedata
# import openeo # Descomente quando a biblioteca openeo estiver instalada

# Inicialização da aplicação Flask
app = Flask(__name__)
CORS(app)

# --- Arquivos de Configuração e Dados ---
DADOS_FILE = 'dados_mock.json'
CONFIG_FILE = 'config.json'

# --- Lógica de Manipulação de Dados ---

def carregar_json(filepath, default_data):
    """Função genérica para carregar um arquivo JSON."""
    if not os.path.exists(filepath):
        return default_data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

def salvar_json(filepath, data):
    """Função genérica para salvar dados em um arquivo JSON."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def slugify(value):
    """Normaliza a string para criar um ID amigável."""
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    value = re.sub(r'[-\s]+', '-', value)
    return value
    
# (As funções get_nivel_risco_e_aqi e determinar_risco_poluente permanecem as mesmas da versão anterior)
def get_nivel_risco_e_aqi(poluentes):
    mapeamento_risco = {"Bom": 50, "Moderado": 100, "Ruim": 150, "Muito Ruim": 200, "Péssimo": 300}
    niveis_ordem = ["Bom", "Moderado", "Ruim", "Muito Ruim", "Péssimo"]
    pior_nivel = "Bom"
    for p in poluentes:
        if niveis_ordem.index(p['nivel_risco']) > niveis_ordem.index(pior_nivel):
            pior_nivel = p['nivel_risco']
    return pior_nivel, mapeamento_risco.get(pior_nivel, 50)

def determinar_risco_poluente(nome, valor):
    valor = float(valor)
    if nome == 'NO₂':
        if valor < 10: return "Bom";
        if valor < 40: return "Moderado";
        if valor < 100: return "Ruim";
        return "Muito Ruim"
    # Adicionar outras lógicas de risco para outros poluentes aqui
    return "Bom"


# Carregamento inicial de dados e configurações
DADOS_DB = carregar_json(DADOS_FILE, {"regioes": [], "dados_qualidade_ar": {}})
CONFIG = carregar_json(CONFIG_FILE, {"openeo_url": "", "client_id": "", "client_secret": ""})


# --- Rotas da API ---

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Obtém ou atualiza as configurações da API externa."""
    global CONFIG
    if request.method == 'POST':
        data = request.json
        CONFIG['openeo_url'] = data.get('openeo_url', '')
        CONFIG['client_id'] = data.get('client_id', '')
        # Em um app real, a 'client_secret' deve ser criptografada
        CONFIG['client_secret'] = data.get('client_secret', '')
        salvar_json(CONFIG_FILE, CONFIG)
        return jsonify({"status": "sucesso", "mensagem": "Configurações salvas."})
    
    # GET request
    return jsonify(CONFIG)


@app.route('/api/regioes', methods=['GET'])
def get_regioes():
    """Retorna a lista de regiões disponíveis."""
    return jsonify(DADOS_DB.get("regioes", []))


@app.route('/api/qualidade_ar', methods=['GET'])
def get_qualidade_ar():
    """Retorna dados de qualidade do ar para uma região específica."""
    regiao_id = request.args.get('regiao_id')
    if not regiao_id:
        return jsonify({"erro": "Parâmetro 'regiao_id' obrigatório."}), 400
    dados_regiao = DADOS_DB.get("dados_qualidade_ar", {}).get(regiao_id)
    if not dados_regiao:
        return jsonify({"erro": f"Dados para '{regiao_id}' não encontrados."}), 404
    time.sleep(0.5)
    return jsonify(dados_regiao)

@app.route('/api/nova_analise', methods=['POST'])
def nova_analise_manual():
    """Cria uma nova análise a partir de dados manuais."""
    data = request.json
    nome_regiao = data.get('nome_regiao')
    if not nome_regiao:
        return jsonify({"erro": "Nome da região é obrigatório."}), 400
        
    regiao_id = slugify(f"{nome_regiao}-{int(datetime.now().timestamp())}")

    poluentes = [
        {"nome": "Dióxido de Nitrogênio", "formula": "NO₂", "valor": float(data.get('no2', 0)), "unidade": "μmol/m²", "nivel_risco": determinar_risco_poluente('NO₂', data.get('no2', 0))},
        # Adicionar outros poluentes do formulário
    ]
    
    nivel_risco_geral, aqi_geral = get_nivel_risco_e_aqi(poluentes)
    
    nova_entrada = {
        "nome_regiao": nome_regiao,
        "ultima_atualizacao": datetime.now().isoformat() + "Z",
        "satelite": data.get('satelite', 'Manual'),
        "aqi_geral": aqi_geral,
        "nivel_risco": nivel_risco_geral,
        "poluentes": poluentes
    }
    
    DADOS_DB["regioes"].append({"id": regiao_id, "nome": nome_regiao})
    DADOS_DB["dados_qualidade_ar"][regiao_id] = nova_entrada
    salvar_json(DADOS_FILE, DADOS_DB)
    
    return jsonify({"status": "sucesso", "mensagem": "Análise salva.", "nova_regiao": {"id": regiao_id, "nome": nome_regiao}}), 201

@app.route('/api/automated_analysis', methods=['POST'])
def automated_analysis():
    """Inicia uma análise automática usando openEO."""
    params = request.json
    
    # Valida se as configurações estão presentes
    if not all([CONFIG.get('openeo_url'), CONFIG.get('client_id'), CONFIG.get('client_secret')]):
        return jsonify({"erro": "As credenciais do Copernicus não estão configuradas. Por favor, vá para a aba de Configurações."}), 400

    # Simulação do processo de automação
    # --- INÍCIO DO CÓDIGO openEO (simulado) ---
    print("Iniciando análise automática com os parâmetros:", params)
    print("URL do openEO:", CONFIG['openeo_url'])
    
    try:
        # 1. Conectar e Autenticar
        # connection = openeo.connect(CONFIG['openeo_url'])
        # connection.authenticate_oidc(
        #     client_id=CONFIG['client_id'],
        #     client_secret=CONFIG['client_secret'],
        #     provider_id='egi' # Exemplo, pode variar
        # )
        print("Autenticação com openEO (simulada) bem-sucedida.")
        
        # 2. Carregar coleção
        # datacube = connection.load_collection(
        #     "SENTINEL_5P_L2",
        #     spatial_extent={
        #         "west": params['west'], "south": params['south'],
        #         "east": params['east'], "north": params['north']
        #     },
        #     temporal_extent=[params['start_date'], params['end_date']],
        #     bands=["NO2_column_number_density"]
        # )
        print("Coleção Sentinel-5P (simulada) carregada.")

        # 3. Processar (ex: média temporal)
        # mean_datacube = datacube.reduce_dimension(dimension="t", reducer="mean")
        print("Processo de redução de dimensão (média) adicionado.")

        # 4. Iniciar job
        # job = mean_datacube.execute_batch(title=f"AirQ-SAT Analysis for {params['nome_regiao']}")
        job_id = f"job_{int(time.time())}"
        print(f"Job (simulado) iniciado com ID: {job_id}")

        # --- FIM DO CÓDIGO openEO (simulado) ---
        
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Análise automática para '{params['nome_regiao']}' foi iniciada.",
            "job_id": job_id
        }), 202

    except Exception as e:
        print(f"Erro na simulação do openEO: {e}")
        return jsonify({"erro": f"Falha ao iniciar a tarefa de análise automática: {e}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

