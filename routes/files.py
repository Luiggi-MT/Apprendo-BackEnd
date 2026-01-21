from flask import Blueprint, send_file, abort
import os

files = Blueprint('files', __name__)
UPLOAD_FOLDER = os.getenv('FILE_PATH')


@files.route('/foto/<path:filename>')
def get_foto(filename): 
    try:
        
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        """ Hay que arreglar esta parte 
            if not file_path.startswith(os.path.abspath(UPLOAD_FOLDER)):
            abort(404)
        """
        return send_file(file_path)
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        return {'error': str(e)}, 500
    
@files.route('/foto-password/<path:filename>')
def get_foto_password(filename):
    try: 
        root_dit = os.getcwd()
        full_path = os.path.join(root_dit, filename)
        return send_file(full_path)
    except FileNotFoundError: 
        abort(404)
    except Exception as e: 
        return {'error': str(e)}, 500