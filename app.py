from flask import Flask
from flask_cors import CORS
from routes import routes
import os

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.register_blueprint(routes)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
