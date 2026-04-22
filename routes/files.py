from flask import Blueprint, send_file, abort
import os

files = Blueprint('files', __name__)
UPLOAD_FOLDER = os.getenv('FILE_PATH')
SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MEDIA_FOLDER = os.path.join(SERVER_ROOT, 'media')


def _safe_join(base_path, relative_path):
    # Evita path traversal y garantiza que el archivo quede dentro del directorio base.
    full_path = os.path.abspath(os.path.join(base_path, relative_path))
    if not full_path.startswith(os.path.abspath(base_path) + os.sep):
        abort(404)
    return full_path


@files.route('/foto/<path:filename>')
def get_foto(filename):
    try:
        file_path = _safe_join(UPLOAD_FOLDER, filename)
        return send_file(file_path)
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        return {'error': str(e)}, 500

@files.route('/media/<path:filename>')
def get_media(filename):
    try:
        file_path = _safe_join(MEDIA_FOLDER, filename)
        return send_file(file_path)
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        return {'error': str(e)}, 500

@files.route('/foto-password/<path:filename>')
def get_foto_password(filename):
    try:
        file_path = _safe_join(UPLOAD_FOLDER, filename)
        return send_file(file_path)
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        return {'error': str(e)}, 500