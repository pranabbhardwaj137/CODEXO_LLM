from flask import Flask, request, jsonify, send_from_directory, render_template
import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM
from diffusers import StableDiffusionPipeline
import torch
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

device = "cuda" if torch.cuda.is_available() else "cpu"

# Load models
llama_tokenizer = AutoTokenizer.from_pretrained("EleutherAI/gpt-neo-2.7B")
llama_tokenizer.pad_token = llama_tokenizer.eos_token  # Set the padding token

llama_model = AutoModelForCausalLM.from_pretrained("EleutherAI/gpt-neo-2.7B").to(device)
pipe = StableDiffusionPipeline.from_pretrained("CompVis/stable-diffusion-v1-4").to(device)

# Ensure the 'static' directory exists
if not os.path.exists('static'):
    os.makedirs('static')

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/upload', methods=['POST'])
def process_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected for uploading"}), 400

        data = pd.read_excel(file)

        logging.info(f"Detected columns: {data.columns.tolist()}")
        logging.info(f"Data preview:\n{data.head()}")

        required_columns = ["Family Name", "Kids", "Occupation", "Workplace"]
        for col in required_columns:
            if col not in data.columns:
                return jsonify({"error": f"Missing column: {col}"}), 400

        if not pd.api.types.is_numeric_dtype(data["Kids"]):
            return jsonify({"error": "'Kids' column must contain numeric values"}), 400

        context = """
        You are an AI tasked with site allotment for a large residential layout divided into sectors.
        - The "Schooling District" should include parks and schools and be assigned to families with kids.
        - The "Tech Park District" should be near tech parks with limited parks and cater to IT professionals without kids.
        - The "General District" should include balanced facilities like shops, parks, and other amenities, and cater to other occupations.
        - Ensure that parks and amenities are well distributed across all districts for community benefits.
        """

        def analyze_data(row):
            prompt = f"""
            {context}
            Family Details:
            - Name: {row['Family Name']}
            - Kids: {row['Kids']}
            - Occupation: {row['Occupation']}
            - Workplace: {row['Workplace']}
            
            Question: Which sector should this family be assigned to and why?
            """
            inputs = llama_tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                padding="max_length",
                max_length=512
            )
            inputs = inputs.to(device)

            outputs = llama_model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=100,
                pad_token_id=llama_tokenizer.eos_token_id
            )
            return llama_tokenizer.decode(outputs[0], skip_special_tokens=True)

        data['Assignment'] = data.apply(analyze_data, axis=1)

        layout_description = """
        A proposed residential layout is divided into the following districts:
        - Schooling District: Focused on families with kids, including parks and schools.
        - Tech Park District: Focused on IT professionals, near tech parks with fewer parks.
        - General District: Balanced facilities for other occupations.
        """
        layout_description += "\nPlot assignments:\n"
        for _, row in data.iterrows():
            layout_description += f"{row['Family Name']} is assigned to {row['Assignment']}. "

        def truncate_to_77_tokens(text):
            tokens = text.split()
            truncated_text = " ".join(tokens[:100])
            return truncated_text

        truncated_description = truncate_to_77_tokens(layout_description)

        try:
            image = pipe(truncated_description).images[0]
            image_path = "static/final_layout.png"
            image.save(image_path)
        except Exception as e:
            logging.error(f"Image generation failed: {e}")
            return jsonify({"error": "Image generation failed"}), 500

        return jsonify({"message": layout_description, "layout_image": f"/static/final_layout.png"}), 200

    except Exception as e:
        logging.error(f"Processing failed: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    app.run(debug=True)