import re
import os
import requests
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route('/executar-rpa', methods=['POST'])
def executar_rpa():
    dados = request.json
    campos_obrigatorios = ['data_inicio', 'data_fim', 'login', 'password']
    if not dados or not all(campo in dados for campo in campos_obrigatorios):
        return jsonify({"erro": "Faltam parametros no body. Certifique-se de enviar data_inicio, data_fim, login e password"}), 400

    data_inicio = dados['data_inicio']
    data_fim = dados['data_fim']
    login = dados['login']
    password = dados['password']

    url_alvo = f"https://sharkcodersteste.sincelo.pt/index.php?m=faturacao&act=listarecibos&nomeCliente=&datainicioRecibo={data_inicio}&datafimRecibo={data_fim}"
    
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            print("Acessando o sistema...")
            page.goto("https://sharkcodersteste.sincelo.pt/login.php")
            
            page.get_by_role("textbox", name="Username").click()
            page.get_by_role("textbox", name="Username").fill(login)
            
            page.get_by_role("textbox", name="Password").click()
            page.get_by_role("textbox", name="Password").fill(password)
            
            page.get_by_role("button", name="Entrar").click()
            
            print(f"Navegando para: {url_alvo}")
            page.goto(url_alvo)
            page.locator(".search-choice-close").click()
            print("Realizando o download...")
            with page.expect_download() as download_info:
                page.get_by_title("Abrir em Excel").click()
            download = download_info.value

            file_path = "recibos_temp.xls"
            download.save_as(file_path)
            
            webhook_url = "https://n8n.erp24.pt/webhook/sharkcoders-recibos-rpa"
            print("Enviando arquivo para o n8n...")
            
            with open(file_path, "rb") as f:
                files = {"file": (file_path, f, "application/vnd.ms-excel")}
                response = requests.post(webhook_url, files=files)
                
            if os.path.exists(file_path):
                os.remove(file_path)
                
            context.close()
            browser.close()
            
        return jsonify({"status": "sucesso", "mensagem": "Arquivo extraído e enviado ao webhook!", "url_acessada": url_alvo}), 200

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route('/rpa-pendentes', methods=['POST'])
def rpa_pendentes():
    dados = request.json
    
    campos_obrigatorios = ['login', 'password']
    if not dados or not all(campo in dados for campo in campos_obrigatorios):
        return jsonify({"erro": "Faltam parametros no body. Certifique-se de enviar login e password"}), 400

    login = dados['login']
    password = dados['password']
    
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            print("Acessando o sistema...")
            page.goto("https://sharkcodersteste.sincelo.pt/login.php", timeout=60000)
            
            # Login dinâmico usando o n8n
            page.get_by_role("textbox", name="Username").click()
            page.get_by_role("textbox", name="Username").fill(login)
            
            page.get_by_role("textbox", name="Password").click()
            page.get_by_role("textbox", name="Password").fill(password)
            
            page.get_by_role("button", name="Entrar").click()

            print("Aguardando carregamento pós-login...")
            page.wait_for_timeout(2000)
            
            print("Navegando pelos menus...")
            # Pega o PRIMEIRO link que contém "Entidades"
            link_entidades = page.locator("a", has_text=re.compile("Entidades", re.IGNORECASE)).first
            link_entidades.wait_for(state="visible", timeout=15000)
            link_entidades.click()

            print("Aguardando carregamento do menu entidades...")
            page.wait_for_timeout(2000)

            # Se o #cartaoteclado falhar, tentaremos seguir sem ele
            try:
                cartaoteclado = page.locator("#cartaoteclado")
                if cartaoteclado.is_visible(timeout=5000):
                    cartaoteclado.click()
            except Exception as e:
                print("Elemento #cartaoteclado não encontrado ou desnecessário, prosseguindo...")
            
            print("Aguardando menu Pendentes...")
            link_pendentes = page.locator("a", has_text=re.compile("Pendentes", re.IGNORECASE)).first
            link_pendentes.wait_for(state="visible", timeout=15000)
            link_pendentes.click()
            
            print("Aguardando 3 segundos para a página carregar corretamente...")
            page.wait_for_timeout(3000)
            
            print("Realizando o primeiro download (Resumo)...")
            with page.expect_download() as download_info:
                # VOLTAMOS A USAR O TITLE
                page.get_by_title(re.compile("Abrir em Excel", re.IGNORECASE)).first.click()
            download = download_info.value
            
            file_path_1 = "pendentes_resumo_temp.xls"
            download.save_as(file_path_1)

            print("Marcando a checkbox de linhas da fatura...")
            # Deixei a busca flexível para a checkbox
            page.get_by_role("checkbox", name=re.compile("Mostra linhas", re.IGNORECASE)).first.check()
            
            # Uma pequena espera após marcar a caixa
            page.wait_for_timeout(1000)
            
            print("Realizando o segundo download (Detalhado)...")
            with page.expect_download() as download1_info:
                # Clica novamente no botão do Excel
                page.get_by_title(re.compile("Abrir em Excel", re.IGNORECASE)).first.click()
            download1 = download1_info.value
            
            file_path_2 = "pendentes_linhas_temp.xls"
            download1.save_as(file_path_2)
            
            # 4. Envia os dois arquivos para o Webhook do n8n na mesma requisição
            webhook_url = "https://n8n.erp24.pt/webhook/sharkcoders-faturas-pendentes"
            print("Enviando os dois arquivos para o n8n...")
            
            with open(file_path_1, "rb") as f1, open(file_path_2, "rb") as f2:
                files = {
                    "arquivo_resumo": (file_path_1, f1, "application/vnd.ms-excel"),
                    "arquivo_linhas": (file_path_2, f2, "application/vnd.ms-excel")
                }
                response = requests.post(webhook_url, files=files)
                
            # Limpeza do servidor
            if os.path.exists(file_path_1):
                os.remove(file_path_1)
            if os.path.exists(file_path_2):
                os.remove(file_path_2)
                
            context.close()
            browser.close()
            
        return jsonify({"status": "sucesso", "mensagem": "Os DOIS arquivos foram extraídos e enviados ao webhook!"}), 200

    except Exception as e:
        import traceback
        erro_detalhado = traceback.format_exc()
        print(f"ERRO CRÍTICO NO PLAYWRIGHT:\n{erro_detalhado}")
        return jsonify({"status": "erro", "mensagem": str(e), "detalhes": erro_detalhado}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
