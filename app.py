from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import os
import uuid
import hashlib
import glob
from dotenv import load_dotenv
import requests
from collections import defaultdict

memoria_usuarios = defaultdict(dict)
app = Flask(__name__, static_folder="static")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Garante que a pasta static/ existe
if not os.path.exists("static"):
    os.makedirs("static")

load_dotenv()
def atualizar_memoria(user_number, mensagem):
    # Aqui você analisa o texto e extrai Nome, Valor, Raça, etc.
    # Exemplo ultra simples (para demonstrar):
    if "manga larga" in mensagem.lower():
        memoria_usuarios[user_number]['Raça'] = "Manga Larga"
    if "endereço" in mensagem.lower():
        memoria_usuarios[user_number]['Endereço'] = mensagem
    # (ideal usar regex ou IA para extrair melhor)

def checar_campos_faltando(user_number):
    campos_obrigatorios = ['Nome', 'Valor', 'Raça', 'Nascimento', 'Sexo', 'Utilização', 'Endereço']
    preenchidos = memoria_usuarios[user_number].keys()
    return [campo for campo in campos_obrigatorios if campo not in preenchidos]

def converter_audio_para_texto(media_url):
    try:
        # Baixar o arquivo de áudio
        response = requests.get(media_url)
        with open("temp_audio.ogg", "wb") as f:
            f.write(response.content)

        # Chamar OpenAI Whisper
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        with open("temp_audio.ogg", "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        return transcription
    except Exception as e:
        print(f"Erro na transcrição: {str(e)}")
        return "Desculpe, não consegui interpretar seu áudio."


@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    user_number = request.values.get('From', '')  # Ex: 'whatsapp:+5511999999999'
    num_media = int(request.values.get('NumMedia', 0))
    
    if num_media > 0:
        media_url = request.values.get('MediaUrl0')
        user_msg = converter_audio_para_texto(media_url)
    else:
        user_msg = request.values.get('Body', '').strip()

    twilio_resp = MessagingResponse()

    # ⚡ Se o usuário ainda não começou a mandar informações
    if user_number not in memoria_usuarios or not memoria_usuarios[user_number]:
        # Primeira interação ou sem dados capturados ainda
        iniciar_cotacao = ["quero fazer seguro", "gostaria de fazer um seguro", "quero cotar", "quero uma cotação"]

        if any(palavra in user_msg.lower() for palavra in iniciar_cotacao):
            resposta = "Ótimo! Vamos iniciar sua cotação. Me informe o Nome do Animal, por favor. 🐎"
        else:
            resposta = "Olá! 👋 Estou aqui para ajudar na cotação de seguro para seu animal. Diga 'quero fazer seguro' para começarmos."

        twilio_resp.message(resposta)
        return str(twilio_resp)

    # Se já começou a cotação, atualiza a memória
    atualizar_memoria(user_number, user_msg)

    # Verifica campos faltantes
    falta = checar_campos_faltando(user_number)

    if falta:
        resposta = f"Faltam as seguintes informações para continuar a cotação: {', '.join(falta)}"
    else:
        resposta = "Perfeito! Todas as informações foram preenchidas. Vamos prosseguir com a cotação."

    twilio_resp.message(resposta)
    #return str(twilio_resp)

    # Resposta com IA
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """
    Você é o corretor virtual da empresa **Equinos Seguros**, especializado em cotação de seguros Pecuário Individual, Rebanhos ou animais de de Competição e Exposição.

    Sua função é orientar o cliente a fornecer todas as informações obrigatórias para realizar a cotação.

    As informações obrigatórias são:
    - Nome do Animal
    - Valor do Animal
    - Número de Registro ou Passaporte (se tiver)
    - Raça
    - Data de Nascimento
    - Sexo (inteiro, castrado ou fêmea)
    - Utilização (lazer, salto, laço etc.)
    - Endereço da Cocheira (CEP e cidade)

    A cotação **somente será iniciada** após o preenchimento completo de todas essas informações.  
    Caso falte alguma informação, informe gentilmente ao usuário **quais campos estão faltando** e solicite o preenchimento.

    Quando todas as informações forem enviadas, avise ao usuário que os resultados serão entregues em dois documentos:
    - Cotação Seguradora SwissRe: https://drive.google.com/file/d/1duauc3jLLkpi-7eTN3TJLi2RypTA4_Qk/view?usp=sharing
    - Cotação Seguradora Fairfax: https://drive.google.com/file/d/1duauc3jLLkpi-7eTN3TJLi2RypTA4_Qk/view?usp=sharing

    Comunique-se de forma clara, acolhedora e profissional.

    Responda de maneira educada, perguntando dados adicionais sempre que necessário.
    """
                },
                {"role": "user", "content": user_msg}
            ]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Erro ao processar resposta com IA:\n{str(e)}"

    # Envia o texto da resposta
    msg_text = twilio_resp.message(reply)

    # Gera ou recupera áudio
    audio_filename = gerar_ou_buscar_audio(reply)
    if audio_filename:
        msg_audio = twilio_resp.message()
        msg_audio.media(f"https://SEU_DOMINIO/static/{audio_filename}")

    return str(twilio_resp)

# Função para gerar OU buscar áudio já existente
def gerar_ou_buscar_audio(texto):
    try:
        # Gera hash do texto para identificar áudios únicos
        texto_hash = hashlib.md5(texto.encode('utf-8')).hexdigest()
        audio_filename = f"audio_{texto_hash}.mp3"
        audio_path = os.path.join("static", audio_filename)

        # Se já existe o áudio, não gera de novo
        if os.path.exists(audio_path):
            return audio_filename

        # Gera novo áudio usando OpenAI TTS
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",  # vozes disponíveis: nova, echo, fable, onyx, shimmer
            input=texto
        )

        with open(audio_path, "wb") as f:
            f.write(response.content)

        # Opcional: limpar áudios antigos para evitar lotar disco
        limpar_audios_antigos()

        return audio_filename
    except Exception as e:
        print(f"Erro ao gerar áudio: {str(e)}")
        return None

# Função para limpar áudios antigos
def limpar_audios_antigos(max_files=50):
    arquivos = sorted(glob.glob('static/audio_*.mp3'), key=os.path.getmtime)
    if len(arquivos) > max_files:
        for arquivo in arquivos[:-max_files]:
            try:
                os.remove(arquivo)
            except Exception as e:
                print(f"Erro ao apagar {arquivo}: {str(e)}")

# Serve arquivos da pasta static/
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
