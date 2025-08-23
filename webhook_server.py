import hmac
import hashlib
import subprocess
from flask import Flask, request, abort
import os

app = Flask(__name__)
GITHUB_SECRET = b'YCjGk8dngfmIpDhoPgkipqIeYtEzbDsi'


# Base directory for vhosts
VHOSTS_BASE = '/var/www/vhosts'
# Map project names to repo paths
PROJECTS = {
    'news10': f'{VHOSTS_BASE}/news10-related-scripts',
    # Add more projects here
}


def verify_signature(payload, signature):
    mac = hmac.new(GITHUB_SECRET, msg=payload, digestmod=hashlib.sha256)
    expected = 'sha256=' + mac.hexdigest()
    return hmac.compare_digest(expected, signature)


@app.route('/webhook', methods=['POST'])
# Accept project name as a URL parameter
@app.route('/webhook/<project>', methods=['POST'])
def webhook(project):
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature or not verify_signature(request.data, signature):
        abort(403)
    event = request.headers.get('X-GitHub-Event')
    repo_path = PROJECTS.get(project)
    if not repo_path:
        abort(404, description='Unknown project')
    if event == 'push':
        result = subprocess.run(['git', '-C', repo_path, 'pull'], capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)
        return f'Pulled latest code for {project}.', 200
    return 'Ignored.', 200



# Default status page
@app.route('/', methods=['GET'])
def index():
    return '<h1>Webhook server is running</h1>', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
