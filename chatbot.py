from flask import Flask, request, jsonify, render_template, session
from fuzzywuzzy import fuzz
import openai
import dotenv
import os

# Load environment variables
dotenv.load_dotenv()

# Set your OpenAI API key
openai.api_key = dotenv.get_key(".env", "OPENAI_API_KEY")
client = openai.OpenAI(api_key=dotenv.get_key(".env","OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Predefined responses with key phrases in French
predefined_responses = {
    "Je suis votre chatbot amical!": ["quel est votre nom", "qui êtes-vous", "ton nom?", "c'est quoi ton nom?"],
    "Oui je suis juste un bout de code et je fonctionne comme prévu!": ["comment allez-vous", "comment te sens-tu", "ça va ?", "comment ça va?"],
    "Je peux répondre à des questions prédéfinies et utiliser ChatGPT pour d'autres.": ["que pouvez-vous faire", "quelles sont vos capacités", "tu fais quoi?", "que fais-tu?"],
}

special_responses = {
    "Quel est mon prénom ?": ["quel est mon prénom", "mon prénom"]
}

def get_best_match(user_query, predefined_responses):
    best_response = None
    highest_score = 0

    for response, phrases in predefined_responses.items():
        for phrase in phrases:
            score = fuzz.token_set_ratio(user_query.lower(), phrase.lower())
            if score > highest_score:
                highest_score = score
                best_response = response

    return best_response, highest_score

@app.route("/")
def index():
    return render_template("viewer.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_query = request.json.get("query")
    if not user_query:
        return jsonify({"error": "Aucune requête fournie"}), 400

    if 'context' not in session:
        session['context'] = []
        session['name_asked'] = False

    # Ask for user's name if not already asked
    if not session.get('name_asked'):
        session['name_asked'] = True
        session['context'].append({"role": "assistant", "content": "Quel est votre prénom ?"})
        return jsonify({"response": "Quel est votre prénom ?"})

    # If user's name is not set, assume the response is the name
    if 'name' not in session:
        session['name'] = user_query
        session['context'].append({"role": "user", "content": user_query})
        session['context'].append({"role": "assistant", "content": f"Ravi de vous rencontrer, {user_query} ! Comment puis-je vous aider aujourd'hui ?"})
        return jsonify({"response": f"Ravi de vous rencontrer, {user_query} ! Comment puis-je vous aider aujourd'hui ?"})

    # Check for special responses like "quel est mon prénom"
    for response, phrases in special_responses.items():
        for phrase in phrases:
            if fuzz.token_set_ratio(user_query.lower(), phrase.lower()) > 80:
                if 'name' in session:
                    return jsonify({"response": f"Votre prénom est {session['name']}."})
                else:
                    return jsonify({"response": "Je ne connais pas encore votre prénom. Quel est votre prénom ?"})

    # Check for predefined responses
    response, score = get_best_match(user_query, predefined_responses)
    if score > 80:  # Threshold for similarity, can be adjusted
        session['context'].append({"role": "assistant", "content": response})
        return jsonify({"response": response})
    else:
        # Fallback to OpenAI API
        context = session['context']
        response = get_chatgpt_response(user_query, context)
        session['context'].append({"role": "user", "content": user_query})
        session['context'].append({"role": "assistant", "content": response})
        return jsonify({"response": response})

def get_chatgpt_response(user_query, context):
    try:
        messages = [{"role": "system", "content": "Vous êtes un assistant compétent."}]
        messages += context
        messages.append({"role": "user", "content": user_query})

        response = client.chat.completions.create(model="gpt-3.5-turbo",
        messages=messages)
        return response.choices[0].message.content.strip()
    except openai.RateLimitError:
        return "Désolé, le quota de requêtes a été dépassé. Veuillez réessayer plus tard."
    except openai.OpenAIError as e:
        return f"Une erreur s'est produite : {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)
