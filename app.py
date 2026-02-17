import os
import subprocess
from flask import Flask, jsonify

app = Flask(__name__)

# Esta é a URL (endpoint) que o n8n vai chamar
@app.route('/executar-rpa', methods=['GET', 'POST'])
def executar_rpa():
    try:
        # Popen executa o seu robô em background (segundo plano).
        # Substitua "bot.py" pelo nome exato do ficheiro que tem o seu código do Playwright.
        subprocess.Popen(["python", "teste2.py"])
        
        # Responde imediatamente ao n8n para não dar erro de "Timeout"
        return jsonify({"status": "sucesso", "mensagem": "Robô acionado e a iniciar o processo!"}), 200
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

if __name__ == '__main__':
    # O Railway atribui a porta automaticamente através desta variável
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
