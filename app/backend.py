import os
from flask import Flask, request, jsonify
import oci

app = Flask(__name__)

# ==========================================
# ORACLE CLOUD CONFIGURATION
# ==========================================
OCI_REGION = 'us-sanjose-1'
NAMESPACE = 'ax8gjz18ycrc'
BUCKET_NAME = 'goa-trip-memories-bucket'

# 1. Double-routing to catch Nginx modifications
@app.route('/api/upload', methods=['POST'])
@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files.get('file') or request.files.get('photo')
    
    if not uploaded_file or uploaded_file.filename == '':
        received_keys = list(request.files.keys())
        return jsonify({
            "error": f"No photo found! Python received these file keys: {received_keys}"
        }), 400

    try:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        os_client = oci.object_storage.ObjectStorageClient(
            config={'region': OCI_REGION}, 
            signer=signer
        )
        
        file_content = uploaded_file.read()
        
        os_client.put_object(
            namespace_name=NAMESPACE,
            bucket_name=BUCKET_NAME,
            object_name=uploaded_file.filename,
            put_object_body=file_content,
            content_type=uploaded_file.content_type
        )
        
        return jsonify({
            "message": "Upload successful!", 
            "filename": uploaded_file.filename
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 2. Add this route so your website's Gallery stops throwing 404s!
@app.route('/api/photos', methods=['GET'])
@app.route('/photos', methods=['GET'])
def get_photos():
    # We will build the download logic later. For now, return an empty gallery.
    return jsonify([])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
