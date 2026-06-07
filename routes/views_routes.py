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
            {"role": "system", "content": "You are CeraAI. Respond naturally like a real doctor."},
            {"role": "user", "content": prompt}
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
Explain this health topic like a professional medical learning dashboard: {disease}

Return ONLY valid JSON. No markdown. No extra text.

Use simple, clean, student-friendly medical language.
Keep the content minimal, professional, and easy to scan.
Each field must be ONLY 1 short sentence.
Maximum 18 words per field.
visual_story must be maximum 2 short professional sentences.
Avoid long paragraphs.
Do not give scary or emergency-only wording unless medically necessary.

JSON format:
{{
  "disease": "{disease}",
  "cause": "1 short professional sentence about cause",
  "body_effect": "1 short professional sentence about body effect",
  "symptoms": "1 short professional sentence about symptoms",
  "diagnosis": "1 short professional sentence about diagnosis",
  "treatment": "1 short professional sentence about treatment",
  "prevention": "1 short professional sentence about prevention",
  "visual_story": "maximum 2 short professional sentences"
}}
"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are CeraAI Learning Teacher. Return only valid JSON with short professional medical content."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.35,
        "max_tokens": 500
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

        disease_lower = disease.lower()

        video_query = f"{disease} medical animation 3D anatomy patient education"

        if "fever" in disease_lower or "temperature" in disease_lower:
            video_query = "fever pathophysiology medical animation thermoregulation patient education"

        search_response = youtube.search().list(
            q=video_query,
            part="snippet",
            maxResults=15,
            type="video",
            safeSearch="strict",
            videoEmbeddable="true",
            videoSyndicated="true",
            relevanceLanguage="en"
        ).execute()

        items = search_response.get("items", [])

        print("YOUTUBE QUERY:", video_query)
        print("YOUTUBE ITEMS COUNT:", len(items))

        if not items:
            return jsonify({
                "success": False,
                "error": "No YouTube result found"
            })

        blocked_words = [
            "kids", "kid", "children", "baby", "mom", "hack",
            "shorts", "#shorts", "tiktok", "reel", "vlog",
            "funny", "home remedy"
        ]

        preferred_words = [
            "animation", "animated", "3d", "anatomy",
            "medical", "patient education", "explained",
            "pathophysiology", "thermoregulation", "fever",
            "osmosis", "nucleus", "mechanism"
        ]

        clean_items = []

        for item in items:
            title = item["snippet"]["title"].lower()
            desc = item["snippet"].get("description", "").lower()
            text = title + " " + desc

            if any(word in text for word in blocked_words):
                continue

            if any(word in text for word in preferred_words):
                clean_items.append(item)

        item = clean_items[0] if clean_items else items[0]

        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        thumbnail = item["snippet"]["thumbnails"].get(
            "high",
            item["snippet"]["thumbnails"]["default"]
        )["url"]

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
            "error": str(e)
        })