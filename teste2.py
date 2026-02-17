import re
import os
import requests
from playwright.sync_api import Playwright, sync_playwright, expect

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    print("Acessando o sistema...")
    page.goto("https://sharkcodersteste.sincelo.pt/login.php")
    page.get_by_role("textbox", name="Username").click()
    page.get_by_role("textbox", name="Username").fill("teste_automacao")
    page.get_by_role("textbox", name="Password").click()
    page.get_by_role("textbox", name="Password").fill("/|Yv:~~?}pZh3")
    page.get_by_role("button", name="Entrar").click()
    
    print("Navegando para a página de recibos...")
    page.goto("https://sharkcodersteste.sincelo.pt/index.php?m=faturacao&act=listarecibos&nomeCliente=&datainicioRecibo=2025-01-01&datafimRecibo=2025-02-01")
    page.locator(".search-choice-close").click()
    print("Realizando o download...")
    with page.expect_download() as download_info:
        page.get_by_title("Abrir em Excel").click()
    download = download_info.value

    # --- INÍCIO DA LÓGICA DE ENVIO PARA O N8N ---
    
    # 1. Salvar o arquivo localmente
    file_path = "recibos_temp.xls"
    download.save_as(file_path)
    print(f"Arquivo salvo com sucesso em: {file_path}")

    # 2. Configurar e enviar para o Webhook
    webhook_url = "https://n8n.erp24.pt/webhook/sharkcoders-recibos-rpa"
    print("Enviando arquivo para o n8n...")
    
    try:
        # Abre o arquivo em modo leitura binária ("rb")
        with open(file_path, "rb") as f:
            # Prepara o payload do arquivo. 
            # "file" será o nome do campo binário que vai chegar no n8n.
            files = {"file": (file_path, f, "application/vnd.ms-excel")}
            
            # Dispara o POST
            response = requests.post(webhook_url, files=files)
            
        if response.status_code == 200:
            print("Sucesso! Arquivo recebido pelo n8n.")
        else:
            print(f"Falha no envio. Status Code: {response.status_code} | Resposta: {response.text}")
            
    except Exception as e:
        print(f"Erro ao tentar conectar com o webhook: {e}")

    # 3. Limpeza: apaga o arquivo local para não acumular lixo no servidor/container
    if os.path.exists(file_path):
        os.remove(file_path)
        print("Arquivo temporário removido da máquina.")

    # ---------------------
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)