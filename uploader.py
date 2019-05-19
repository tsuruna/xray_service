import json
import os
import uuid
import sender
import socket
from flask import Flask, request, redirect, url_for, send_from_directory
import requests

UPLOAD_FOLDER = './uploads/'
ALLOWED_EXTENSIONS = set(['csv'])
BASE_CONSUL_URL = 'http://registry:8500'
SERVICE_ADDRESS = socket.gethostbyname(socket.gethostname())
PORT = 8080

RP_ENDPOINT = os.environ.get('RP_ENDPOINT', 'http://api:8080/')
RP_UUID = os.environ['RP_UUID']
RP_PROJECT = os.environ['RP_PROJECT']
RP_TAGS = []

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/healthcheck')
def health_check():
    # TODO: implement any other checking logic.
    return '', 200


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = str(uuid.uuid4())
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect('xray'+url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    sender.main(app.config['UPLOAD_FOLDER'] + filename, RP_ENDPOINT,
                RP_UUID, RP_PROJECT, RP_TAGS)
    os.remove(app.config['UPLOAD_FOLDER'] + filename)
    return '''<!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <h3>Uploaded successfully</h2>
    <form action="/xray" method=get>
    <input type=submit value="Go back">
    </form>
    '''


def register():
    url = BASE_CONSUL_URL + '/v1/agent/service/register'
    data = {
        'Name': 'xray-import',
        'Tags': [
            'traefik.frontend.rule=PathPrefixStrip:/xray, '
            'healthCheckUrlPath=/health, '
            'urlprefix-/xray opts strip=/xray'
        ],
        'Address': SERVICE_ADDRESS,
        'Port': PORT,
        'Check': {
            'http': 'http://{address}:{port}/healthcheck'.format(address=SERVICE_ADDRESS, port=PORT),
            'interval': '10s'
        }
    }
    app.logger.debug('Service registration parameters: ', data)
    res = requests.put(
        url,
        data=json.dumps(data)
    )
    print(res.text)
    return res.text


if __name__ == '__main__':
    register()
    app.run('0.0.0.0', PORT)
