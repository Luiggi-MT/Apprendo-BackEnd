from flask import Blueprint, send_file, abort
from db import Database
import os

db = Database()
components = Blueprint('components', __name__)
FOLDER_COMPONENTS = os.getenv('FILE_COMPONENTS')

@components.route('/component/<path:filename>')
def get_component(filename): 
    try: 
        file_path = os.path.join(FOLDER_COMPONENTS, filename)
        return send_file(file_path)
    except FileExistsError: 
        abort(404)
    except Exception as e: 
        return {'error': str(e)}, 500