## By Sofia De la Mora Tostado
# 2023

import os
import time
import pickle
from threading import Thread

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

import openai

from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain, RetrievalQA
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.llms import OpenAI as LangchainOpenAI
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.indexes import VectorstoreIndexCreator
from langchain.chains import RetrievalQA,  ConversationalRetrievalChain
from langchain.prompts.prompt import PromptTemplate


from tqdm import tqdm

from dotenv import load_dotenv
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
FOLDER_PATH = os.getenv('FOLDER_PATH')


class DocumentManager:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.documents = []

    def load_documents(self):
        loaders = [PyPDFLoader(os.path.join(self.folder_path, fn)) for fn in os.listdir(self.folder_path)]
        for loader in tqdm(loaders):
            try:
                self.documents.extend(loader.load())
            except:
                pass

        with open('my_documents.pkl', 'wb') as f: #DELETED PERSONAL DOCUMENTS
            pickle.dump(self.documents, f)

        return self.documents


class ChatAssistant:
    def __init__(self, documents, assistant_prompt, llm, retriever, memory):
        self.documents = documents
        self.assistant_prompt = assistant_prompt
        self.llm = ChatOpenAI(
                temperature=0,
                openai_api_key=OPENAI_API_KEY,
                model_name='gpt-4'
            )
        self.retriever = retriever
        self.memory = memory
        self.qa = ConversationalRetrievalChain.from_llm(
        llm=self.llm, 
        chain_type="stuff", 
        condense_question_prompt=self.assistant_prompt,
        retriever=self.retriever, 
        memory=self.memory)

    def get_completion(self, user_prompt):
        response = self.qa({"question": user_prompt})['answer']
        return response


class WhatsAppMessenger:
    def __init__(self, account_sid, auth_token):
        self.client = Client(account_sid, auth_token)

    def send_message(self, to, body):

        # Split the message into chunks if it's too long
        messages = [body[i:i+1600] for i in range(0, len(body), 1600)]

        for msg in messages:
            message = self.client.messages.create(
                body=msg,
                from_='whatsapp:+14155238886',
                to='whatsapp:' + to
            )


class MedicalChatApp:
    def __init__(self, assistant, messenger):
        self.assistant = assistant
        self.messenger = messenger
        self.app = Flask(__name__)

    def async_generate_answer(self, question, to):
        answer = self.assistant.get_completion(question)
        print("BOT Answer: ", answer)
        if len(answer) > 1600:
            answer_parts = [answer[i:i + 1600] for i in range(0, len(answer), 1600)]
            for part in answer_parts:
                self.messenger.send_message(to, part)
                time.sleep(5)
        else:
            self.messenger.send_message(to, answer)  
            time.sleep(5)

    def chatgpt(self):
        incoming_que = request.values.get('Body', '').strip()
        to = request.values.get('From', '')[9:]

        bot_resp = MessagingResponse()
        msg = bot_resp.message()

        # Check if the query is related to lupus or general medical topics
        msg.body("Answering...")
        print("Question: ", incoming_que)
        Thread(target=self.async_generate_answer, args=(incoming_que, to)).start()

        return str(bot_resp)

    def run(self, debug=True):
        self.app.run(debug=debug)

# Initialize the document manager and load documents
doc_manager = DocumentManager(FOLDER_PATH)
documents = doc_manager.load_documents()

assistant_prompt = """
You are Sofia's dedicated AI medical advisor. Your primary role is to provide insightful and tailored medical advice to her based on her medical history. This are some important facts about her:

- **Birthday**: January 30 1997.
- **Diagnosed Conditions**: lupus erythematosus systemic, raynaud's syndrome, uveitis.
- **Present Symptoms**: hand pain, joint pain, dry eyes.
- **Current Medications**: 200 mg of plaquenil daily, 50 mg azioatriopine daily.

You also have access to all her medical records in the documents provided. They consist of different test since 2019 till today. You don't always have to look at the documents, answer her questions with medical information you possess too.

This is Sofia's question: {question}

Based on the above, when Sofia seeks advice, present your recommendations in the following structured manner:

1. **General Recommendations**: Offer broad advice pertinent to Sofia's conditions.
2. **Symptom Management**: Discuss possible strategies or treatments to mitigate her symptoms.
3. **Medication Guidance**: Provide clarifications and suggestions about her ongoing medications.
4. **Tests and Follow-up**: Recommend relevant medical tests and periodic check-ups.
5. **Lifestyle Tips**: Share counsel on daily routines, dietary habits, exercise, and other wellness practices.
6. **Mental Well-being**: Advocate techniques or habits beneficial for emotional and mental health, like relaxation methods>
7. **Prevention & Alerts**: Highlight any warning signs or symptoms that necessitate immediate medical intervention.

At the conclusion, offer Sofia a succinct summary encapsulating all your advice.

Chat History:
{chat_history}
"""



# Initialize the chat assistant with necessary parameters

embeddings = OpenAIEmbeddings()
db = Chroma.from_documents(documents, embeddings)

chat_assistant = ChatAssistant(
    documents=documents, 
    assistant_prompt=assistant_prompt, 
    llm=ChatOpenAI(
    temperature=0,
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    model_name='gpt-4'), 
    retriever=db.as_retriever(search_type="similarity", search_kwargs={"k":2}), 
    memory=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
)

# Initialize the WhatsApp messenger with Twilio credentials
whatsapp_messenger = WhatsAppMessenger(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize the medical chat app with the chat assistant and messenger
app = MedicalChatApp(chat_assistant, whatsapp_messenger)

if __name__ == '__main__': 
    app.run(debug=True)