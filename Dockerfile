# Usa a imagem oficial do Playwright da Microsoft (já com os navegadores)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto dos seus arquivos (o seu script .py)
COPY . .

# Comando que o Railway vai rodar para iniciar o bot
# Substitua "seu_script.py" pelo nome real do seu arquivo
CMD ["python", "teste2.py"]