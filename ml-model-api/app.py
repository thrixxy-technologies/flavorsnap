from flask import Flask, request, jsonify
from PIL import Image
import io

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    try:
        # Placeholder for preprocessing & prediction
        image = Image.open(file.stream)
        # TODO: Resize, normalize, and run model here
        predicted_label = "Moi Moi"  # Dummy output for now
        return jsonify({'label': predicted_label})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
