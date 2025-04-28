from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import os
import uuid
import hashlib
import glob
from dotenv import load_dotenv
import requests

load_dotenv()

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

app = Flask(__name__, static_folder="static")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Garante que a pasta static/ existe
if not os.path.exists("static"):
    os.makedirs("static")

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    twilio_resp = MessagingResponse()

    num_media = int(request.values.get('NumMedia', 0))

    if num_media > 0:
        # Recebe áudio enviado
        media_url = request.values.get('MediaUrl0')
        content_type = request.values.get('MediaContentType0')

        if "audio" in content_type:
            print(f"Áudio recebido: {media_url}")
            # Agora transcreve o áudio
            user_msg = converter_audio_para_texto(media_url)
        else:
            user_msg = "Desculpe, só consigo interpretar áudios de voz."
    else:
        # Se não é áudio, pega o texto normal
        user_msg = request.values.get('Body', '').strip()
    
    # Saudação personalizada
    if user_msg.lower() in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
        saudacao = "Olá! 👋 Eu sou o corretor virtual da Equinos Seguros.\nEstou aqui para facilitar sua cotação de seguro!\nEm que posso te ajudar ?"
        msg_text = twilio_resp.message(saudacao)

        audio_filename = gerar_ou_buscar_audio(saudacao)
        if audio_filename:
            msg_audio = twilio_resp.message()
            msg_audio.media(f"https://chatgpt-whatsapp-sc0w.onrender.com/static/{audio_filename}")

        return str(twilio_resp)

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
