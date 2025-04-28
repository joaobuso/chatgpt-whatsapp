from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    user_msg = request.values.get('Body', '').strip()
    print(f"Recebido: {user_msg}")

    twilio_resp = MessagingResponse()
    
    # Enviar arquivo se palavra-chave for detectada
    if "manual" in user_msg.lower():
        msg = twilio_resp.message("Segue o manual da empresa em PDF 📎")
        msg.media("https://drive.google.com/uc?export=download&id=1FDhN0AEAp35CgWxAN3X8-FSLjkTSn0Xy")
        return str(twilio_resp)


    # Saudação personalizada
    if user_msg.lower() in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
        saudacao = "Olá! 👋 Eu sou o corretor virtual da Equinos Seguros.\nEstou aqui para facilitar sua cotação de seguro!\nEm que posso te ajudar ?"
        twilio_resp.message(saudacao)
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

    twilio_resp.message(reply)
    return str(twilio_resp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
