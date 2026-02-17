import os
import requests
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route('/executar-rpa', methods=['POST'])
def executar_rpa():
    # 1. Recebe os dados do corpo (body) da requisição enviada pelo n8n
    dados = request.json
    
    # Validação de segurança básica corrigida
    campos_obrigatorios = ['data_inicio', 'data_fim', 'login', 'password']
    if not dados or not all(campo in dados for campo in campos_obrigatorios):
        return jsonify({"erro": "Faltam parametros no body. Certifique-se de enviar data_inicio, data_fim, login e password"}), 400

    data_inicio = dados['data_inicio']
    data_fim = dados['data_fim']
    login = dados['login']
    password = dados['password']

    # 2. Monta a URL dinâmica com as datas recebidas do n8n
    url_alvo = f"https://sharkcodersteste.sincelo.pt/index.php?m=faturacao&act=listarecibos&nomeCliente=&datainicioRecibo={data_inicio}&datafimRecibo={data_fim}"
    
    # 3. Executa o Playwright
    try:
        with sync_playwright() as playwright:
            # ATENÇÃO: Deixe headless=True no Railway!
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            print("Acessando o sistema...")
            page.goto("https://sharkcodersteste.sincelo.pt/login.php")
            
            # Usando as variáveis limpas para preencher o formulário
            page.get_by_role("textbox", name="Username").click()
            page.get_by_role("textbox", name="Username").fill(login)
            
            page.get_by_role("textbox", name="Password").click()
            page.get_by_role("textbox", name="Password").fill(password)
            
            page.get_by_role("button", name="Entrar").click()
            
            print(f"Navegando para: {url_alvo}")
            page.goto(url_alvo)
            
            print("Realizando o download...")
            with page.expect_download() as download_info:
                page.get_by_title("Abrir em Excel").click()
            download = download_info.value

            file_path = "recibos_temp.xls"
            download.save_as(file_path)
            
            # 4. Envia o arquivo para o Webhook do n8n
            webhook_url = "https://n8n.erp24.pt/webhook/sharkcoders-recibos-rpa"
            print("Enviando arquivo para o n8n...")
            
            with open(file_path, "rb") as f:
                files = {"file": (file_path, f, "application/vnd.ms-excel")}
                response = requests.post(webhook_url, files=files)
                
            if os.path.exists(file_path):
                os.remove(file_path)
                
            context.close()
            browser.close()
            
        # 5. Retorna sucesso para o nó HTTP Request inicial do n8n
        return jsonify({"status": "sucesso", "mensagem": "Arquivo extraído e enviado ao webhook!", "url_acessada": url_alvo}), 200

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
