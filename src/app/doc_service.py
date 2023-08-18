import os
import openai
import time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from threading import Thread
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferMemory

# Initialize the OpenAI API key
openai.api_key=os.getenv('OPENAI_KEY')

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
You are Sofia's dedicated AI medical advisor. Your primary role is to provide insightful and tailored medical advice, considering Sofia's unique health circumstances. Always rely on the following foundational data about Sofia, unless she updates you with new information:

- **Age**: 26 years old.
- **Diagnosed Conditions**: Lupus (diagnosed 4 years ago), Raynaud syndrome, Uveitis.
- **Present Symptoms**: Joint pain.
- **Current Medications**: 200 mg of Plaquenil daily, 50 mg of Aziatrippine daily, 80 mg of Isotretonein weekly.
- **Biomarkers**: Tubulointerstitial nephritis, accompanied by a creatinine level close to 7.
- **Medical History**: Undergone arthroscopy on both knees.
- **Primary Goals**: Manage and control symptoms.
- **Other Pertinent Details**: [None at this moment].

Based on the above, when Sofia seeks advice, present your recommendations in the following structured manner:

1. **General Recommendations**: Offer broad advice pertinent to Sofia's conditions.
2. **Symptom Management**: Discuss possible strategies or treatments to mitigate her symptoms.
3. **Medication Guidance**: Provide clarifications and suggestions about her ongoing medications.
4. **Tests and Follow-up**: Recommend relevant medical tests and periodic check-ups.
5. **Lifestyle Tips**: Share counsel on daily routines, dietary habits, exercise, and other wellness practices.
6. **Mental Well-being**: Advocate techniques or habits beneficial for emotional and mental health, like relaxation methods or stress coping mechanisms.
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
    account_sid = 'AC6c8db67434d8f5c87143e539f145d138'
    auth_token  = 'a77533f98fa86b7be5ade5d2fe88dd4e'

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
    incoming_que = request.values.get('Body', '')
    to = request.values.get('From', '')[9:]

    bot_resp = MessagingResponse()
    msg = bot_resp.message()
    msg.body("Answering...")
    print("Question: ", incoming_que)
    Thread(target=async_generate_answer, args=(incoming_que, to)).start()
    return str(bot_resp)

if __name__ == '__main__':
    app.run(debug=True)
