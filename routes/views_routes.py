from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from database.models import ChatHistory, Conversation
from googleapiclient.discovery import build
import os
import json
import ssl
import urllib.request
import urllib.error

views_bp = Blueprint('views', __name__)


def get_voice_ai_response(user_message):
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")

    if not api_key:
        return "API key missing. Please check .env file."

    prompt = f"""
You are CeraAI, a real-time medical voice assistant.

LANGUAGE RULE:
- If user speaks English, reply ONLY in SIMPLE English.
- If user speaks Tamil or Tanglish, reply ONLY in NATURAL SPOKEN Tamil.
- NEVER mix languages.

VOICE STYLE:
- Speak like a REAL doctor talking casually to a patient.
- Very natural spoken tone.

LENGTH:
- ONLY 2–4 short sentences.

User: {user_message}
"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are CeraAI. Respond naturally like a real doctor."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 140
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        },
        method="POST"
    )

    try:
        context = ssl._create_unverified_context()

        with urllib.request.urlopen(req, timeout=25, context=context) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]

    except urllib.error.HTTPError as e:
        print("VOICE AI ERROR:", e.code)
        print(e.read().decode("utf-8", errors="ignore"))
        return "Server error."

    except Exception as e:
        print("Voice AI Error:", e)
        return "System error. Try again later."


@views_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('views.chatbot'))
    return render_template('index.html')


@views_bp.route('/chatbot', methods=['GET', 'POST'])
@views_bp.route('/chatbot/<int:conversation_id>', methods=['GET', 'POST'])
@login_required
def chatbot(conversation_id=None):

    if request.method == 'POST':
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({"response": "Please ask a question."})

        bot_reply = get_voice_ai_response(user_message)
        return jsonify({"response": bot_reply})

    conversations = Conversation.query.filter_by(
        user_id=current_user.id
    ).order_by(Conversation.timestamp.desc()).all()

    history = []

    if conversation_id:
        conv = Conversation.query.get_or_404(conversation_id)

        if conv.user_id != current_user.id:
            return "Unauthorized", 403

        history = ChatHistory.query.filter_by(
            conversation_id=conversation_id
        ).order_by(ChatHistory.timestamp.asc()).all()

    return render_template(
        'chatbot.html',
        conversations=conversations,
        history=history,
        current_conversation_id=conversation_id
    )


@views_bp.route('/disease-awareness')
@login_required
def disease_awareness():
    return render_template('disease_awareness.html')


@views_bp.route('/learning')
@login_required
def learning():
    return render_template('learning.html')


@views_bp.route('/medical-hub')
@login_required
def medical_hub():
    return render_template('medical_hub.html')


@views_bp.route("/api/learn-disease", methods=["POST"])
@login_required
def learn_disease():
    data = request.get_json()
    disease = data.get("disease", "").strip()

    if not disease:
        return jsonify({
            "success": False,
            "error": "Disease name missing"
        })

    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")

    if not api_key:
        return jsonify({
            "success": False,
            "error": "API key missing"
        })

    prompt = f"""
Explain this health topic like professional medical visual learning: {disease}

Return ONLY valid JSON. No markdown. No extra text.

Use simple, clear, student-friendly medical language.
Each field must be 2 to 3 clear sentences.
Do not give scary or emergency-only wording unless it is medically necessary.

JSON format:
{{
  "disease": "{disease}",
  "cause": "explain the cause clearly in 2-3 simple sentences",
  "body_effect": "explain how it affects the body in 2-3 simple sentences",
  "symptoms": "explain main symptoms clearly in 2-3 simple sentences",
  "diagnosis": "explain how doctors identify it in 2-3 simple sentences",
  "treatment": "explain basic treatment approach in 2-3 simple sentences",
  "prevention": "explain prevention clearly in 2-3 simple sentences",
  "visual_story": "short professional medical visual explanation for students in 3-4 simple sentences"
}}
"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are CeraAI Learning Teacher. Explain like a professional medical educator. Return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.45,
        "max_tokens": 950
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        },
        method="POST"
    )

    try:
        context = ssl._create_unverified_context()

        with urllib.request.urlopen(req, timeout=30, context=context) as response:
            result = json.loads(response.read().decode("utf-8"))

        ai_text = result["choices"][0]["message"]["content"].strip()

        if ai_text.startswith("```"):
            ai_text = ai_text.replace("```json", "").replace("```", "").strip()

        learning_data = json.loads(ai_text)

        return jsonify({
            "success": True,
            "data": learning_data
        })

    except Exception as e:
        print("Learning API Error:", e)
        return jsonify({
            "success": False,
            "error": "AI learning failed"
        })


@views_bp.route("/api/learning-video", methods=["POST"])
@login_required
def learning_video():
    data = request.get_json()
    disease = data.get("disease", "").strip()

    if not disease:
        return jsonify({
            "success": False,
            "error": "Disease name missing"
        })

    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        return jsonify({
            "success": False,
            "error": "YouTube API key missing"
        })

    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        search_request = youtube.search().list(
            q=f"{disease} 3D medical animation patient education anatomy",
            part="snippet",
            maxResults=8,
            type="video",
            safeSearch="strict",
            videoEmbeddable="true",
            videoSyndicated="true",
            videoDuration="medium",
            videoDefinition="high",
            relevanceLanguage="en"
        )

        search_response = search_request.execute()
        items = search_response.get("items", [])

        if not items:
            return jsonify({
                "success": False,
                "error": "Video not found"
            })

        blocked_words = [
            "kids",
            "kid",
            "children",
            "cartoon",
            "peekaboo",
            "dr binocs",
            "nursery",
            "rhymes",
            "for kids",
            "baby",
            "school kids",
            "kindergarten"
        ]

        preferred_words = [
            "medical",
            "animation",
            "3d",
            "anatomy",
            "patient",
            "education",
            "health",
            "clinical",
            "nucleus",
            "osmosis"
        ]

        filtered_items = []

        for item in items:
            title = item["snippet"]["title"].lower()
            description = item["snippet"].get("description", "").lower()
            text = title + " " + description

            has_blocked = any(word in text for word in blocked_words)
            has_preferred = any(word in text for word in preferred_words)

            if not has_blocked and has_preferred:
                filtered_items.append(item)

        if filtered_items:
            item = filtered_items[0]
        else:
            clean_items = []

            for item in items:
                title = item["snippet"]["title"].lower()
                description = item["snippet"].get("description", "").lower()
                text = title + " " + description

                if not any(word in text for word in blocked_words):
                    clean_items.append(item)

            if not clean_items:
                return jsonify({
                    "success": False,
                    "error": "Professional video not found"
                })

            item = clean_items[0]

        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        thumbnail = item["snippet"]["thumbnails"]["high"]["url"]

        return jsonify({
            "success": True,
            "video_id": video_id,
            "title": title,
            "thumbnail": thumbnail,
            "embed_url": f"https://www.youtube.com/embed/{video_id}?rel=0"
        })

    except Exception as e:
        print("YouTube Video Error:", e)
        return jsonify({
            "success": False,
            "error": "Video search failed"
        })