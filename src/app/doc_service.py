## By Sofia De la Mora Tostado
# 2023

import openai
import time
import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from threading import Thread
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferMemory

# Initialize the OpenAI API key
openai.api_key = os.getenv('OPENAI_KEY')

LUPUS_KEYWORDS = [
    "pain", "fatigue", "rash", "swelling", "medication", "flare-up", "doctor", "treatment", "joint ache", "fever", 
    "sun sensitivity", "weight change", "hair loss", "sleep", "headache", "stress", "diet", "mood swings", "depression", 
    "anxiety", "specialist", "hospital", "therapy", "blood test", "appointment", "symptoms", "family history", "bruising", 
    "kidney issues", "breathing problems", "chest pain", "allergies", "supplements", "memory loss", "diet", "exercise", "sunburn", 
    "dry eyes", "dizziness", "nausea", "labs", "sensitivity", "referral", "immune system", "wellness", "pregnancy", "fatigue", 
    "swelling", "heartbeat", "blood pressure", "infection", "dietitian", "sunscreen", "ointment", "rest", "flare triggers", 
    "mobility", "skin", "inflammation", "counseling", "bones", "joints", "calcium", "chronic", "vaccine", "arthritis", 
    "lupus", "side effects", "vitamins", "minerals", "disability", "insurance", "diet", "hydration", "help", "choroiditis", "creatinine",
    "kidney", "assist", "role"
]

def is_medical_related(query):
    query = query.lower()  # Convert the query to lowercase for easy comparison
    return any(keyword in query for keyword in LUPUS_KEYWORDS)

# Initialization
llm = ChatOpenAI(
    temperature=0,
    openai_api_key=openai.api_key,
    model_name='gpt-3.5-turbo'
)

conversation_buf = ConversationChain(
    llm=llm,
    memory=ConversationBufferMemory()
)

assistant_prompt = """
You are Sofia's dedicated AI medical advisor. Your primary role is to provide insightful and tailored medical advice, consi>

- **Age**: ---.
- **Diagnosed Conditions**: ---.
- **Present Symptoms**: ---.
- **Current Medications**: ---.
- **Biomarkers**: ---.
- **Medical History**: ---.
- **Primary Goals**: ---.
- **Other Pertinent Details**: ---.

Based on the above, when Sofia seeks advice, present your recommendations in the following structured manner:

1. **General Recommendations**: Offer broad advice pertinent to Sofia's conditions.
2. **Symptom Management**: Discuss possible strategies or treatments to mitigate her symptoms.
3. **Medication Guidance**: Provide clarifications and suggestions about her ongoing medications.
4. **Tests and Follow-up**: Recommend relevant medical tests and periodic check-ups.
5. **Lifestyle Tips**: Share counsel on daily routines, dietary habits, exercise, and other wellness practices.
6. **Mental Well-being**: Advocate techniques or habits beneficial for emotional and mental health, like relaxation methods>
7. **Prevention & Alerts**: Highlight any warning signs or symptoms that necessitate immediate medical intervention.

At the conclusion, offer Sofia a succinct summary encapsulating all your advice.
"""

# Start the conversation with the assistant's prompt
conversation_buf.run(assistant_prompt)

def get_completion(user_prompt):
    """
    This function now leverages conversation_buf for memory.
    """
    # Use the conversation_buf's run method and extract the response
    response = conversation_buf(user_prompt)['response']
    return response

# Flask Application
app = Flask(__name__)

def send_whatsapp_message(to, body):
    # Your Account SID and Auth Token
    account_sid = os.getenv('ACCOUNT_SID')
    auth_token  = os.getenv('AUTH_TOKEN')

    client = Client(account_sid, auth_token)

    # Split the message into chunks if it's too long
    messages = [body[i:i+1600] for i in range(0, len(body), 1600)]

    for msg in messages:
        message = client.messages.create(
            body=msg,
            from_='whatsapp:+14155238886',
            to='whatsapp:' + to
        )

def async_generate_answer(question, to):
    answer = get_completion(question)
    print("BOT Answer: ", answer)
    if len(answer) > 1600:
        answer_parts = [answer[i:i + 1600] for i in range(0, len(answer), 1600)]
        for part in answer_parts:
            send_whatsapp_message(to, part)
            time.sleep(5)
    else:
        send_whatsapp_message(to, answer)    
        time.sleep(5)

@app.route('/chatgpt', methods=['POST'])
def chatgpt():
    incoming_que = request.values.get('Body', '').strip()
    to = request.values.get('From', '')[9:]

    bot_resp = MessagingResponse()
    msg = bot_resp.message()

    # Check if the query is related to lupus or general medical topics
    if is_medical_related(incoming_que):
        msg.body("Answering...")
        print("Question: ", incoming_que)
        Thread(target=async_generate_answer, args=(incoming_que, to)).start()
    else:
        msg.body("Sorry, I can only answer questions related to lupus and medical topics. Please ask a relevant question.")

    return str(bot_resp)

if __name__ == '__main__':
    app.run(debug=True)
