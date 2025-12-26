from flask import Flask
from flask_cors import CORS
import os

from routes.students import students
from routes.status import estados
from routes.components import components
from routes.files import files
from routes.session import auth


app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

app.register_blueprint(estados)
app.register_blueprint(students)
app.register_blueprint(components)
app.register_blueprint(files)
app.register_blueprint(auth)




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
