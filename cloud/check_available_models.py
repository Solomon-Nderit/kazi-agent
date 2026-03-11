from google import genai


from dotenv import load_dotenv



load_dotenv()
client = genai.Client()

for model in client.models.list():
    print(f"Name: {model.name}, Display Name: {model.display_name}")
