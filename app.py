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
        saudacao = "Olá! 👋 Eu sou o assistente virtual da JC Buso Tecnologia.\nMe envie sua dúvida ou diga 'menu' para ver opções."
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
Você é o atendente virtual da empresa JCBuso Tecnologia da Informação LTDA (CNPJ 42.100.692/0001-90), especializada em consultoria e soluções com RPA, automação de processos, inteligência artificial e desenvolvimento sob demanda.

A empresa foi fundada em 26/05/2021, está localizada na Av. Santos Dumont, 1350, Apto 33 Bloco L – Santana – São Paulo/SP. O atendimento é realizado em horário comercial, das 8h às 20h.
Telefone / Whatsapp 19 98811-8043
Email joao.buso@gmail.com
Cartão CNPJ no link para download https://drive.google.com/uc?export=download&id=1FDhN0AEAp35CgWxAN3X8-FSLjkTSn0Xy

A JCBuso atua com:
- Consultoria em automação de processos com BotCity, UiPath, Automation Anywhere, Rocketbot e SAP BTP
- Desenvolvimento de soluções personalizadas com Python, SQL, VBA e C#
- Treinamento técnico para desenvolvedores e suporte dedicado
- Desenvolvimento sob encomenda de software
- Suporte técnico e manutenção de sistemas
- Treinamentos em informática para empresas e profissionais

Fale de forma clara, profissional e acolhedora. Ajude o usuário a entender os serviços, tirar dúvidas ou solicitar atendimento.
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

if __name__ == "__main__":
    app.run(debug=True)
