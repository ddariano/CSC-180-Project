import os
import requests
from flask import Flask, request, jsonify, render_template
import openai
import re

app = Flask(__name__)

# Make sure your OpenAI API key is set in environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Default Kroki server URL
KROKI_URL = "https://kroki.io"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    text = request.form.get("text", "").strip()
    diagram_type = request.form.get("diagram_type", "mermaid").strip()
    revision = request.form.get("revision", "").strip()
    previous_code = request.form.get("previous_code", "").strip()

    # Build prompt based on whether it's a revision or initial diagram
    if previous_code and revision:
        # Apply revision to previous code
        print("Applying revision to previous code.")
        prompt = f"""
You previously generated this diagram code:

{previous_code}

Apply the following revision instructions:

{revision}

Only output the corrected diagram code for {diagram_type}. No explanations, no markdown, just pure code.
"""
    else:
        # Initial diagram generation
        if diagram_type == "plantuml":
            prompt = f"""
Generate a PlantUML diagram based on the following description:

{text}

Only output the diagram code. No explanations, no markdown. Wrap it in @startuml and @enduml.
"""
        else:
            prompt = f"""
Generate a {diagram_type} diagram based on the following description:

{text}

Only output the diagram code. No explanations, no markdown.
"""
            

    try:
        # Call OpenAI to generate diagram code
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        diagram_code = response.choices[0].message.content.strip()
        # Remove code fences if present
        diagram_code = re.sub(r"^```.*\n|```$", "", diagram_code, flags=re.MULTILINE).strip()
        diagram_code = diagram_code.strip("`\"'")

        # Send diagram code to Kroki
        kroki_api_url = f"{KROKI_URL}/{diagram_type}/svg"
        kroki_response = requests.post(kroki_api_url, data=diagram_code.encode("utf-8"))

        if kroki_response.status_code != 200:
            return jsonify({"error": f"Kroki error: {kroki_response.text}"}), 500

        diagram_svg = kroki_response.text

        # Always return latest diagram code for next revision
        return jsonify({
            "diagram_code": diagram_code,
            "diagram_svg": diagram_svg
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)