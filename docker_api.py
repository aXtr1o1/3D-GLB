
from flask import Flask, request, jsonify
from all_in_one import main_function

app = Flask(__name__)

@app.route('/run', methods=['POST'])
def run_main():
    data = request.get_json()

    if not data or 'gender' not in data:
        return jsonify({'error': 'Missing "gender" in request body'}), 400

    gender = data['gender']

    try:
        result = main_function(gender)
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Only for local development; not used in production with gunicorn
    app.run(host='0.0.0.0', port=5000, debug=False)
