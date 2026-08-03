from flask import Flask, request, jsonify
import oci
import uuid

app = Flask(__name__)

# --- OCI Authentication (Instance Principals) ---
try:
    # This automatically authenticates using your VM's identity!
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    object_storage_client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
except Exception as e:
    print(f"Warning: Could not initialize OCI signer. {e}")
    object_storage_client = None

NAMESPACE = "ax8gjz18ycrc"
BUCKET_NAME = "goa-trip-memories-bucket"
REGION = "us-sanjose-1"

@app.route('/api/upload', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({"error": "No photo provided"}), 400

    photo = request.files['photo']
    uploader = request.form.get('uploader', 'Unknown')
    caption = request.form.get('caption', 'No caption')
    
    file_extension = photo.filename.split('.')[-1]
    unique_filename = f"{uploader}_{uuid.uuid4().hex[:8]}.{file_extension}"
    
    try:
        # Push the image to your OCI bucket
        object_storage_client.put_object(
            namespace_name=NAMESPACE,
            bucket_name=BUCKET_NAME,
            object_name=unique_filename,
            put_object_body=photo.read(),
            content_type=photo.content_type,
            # We attach who uploaded it and the caption directly to the image metadata
            opc_meta={
                "uploader": uploader,
                "caption": caption
            }
        )
        return jsonify({"message": "Successfully uploaded!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/photos', methods=['GET'])
def get_photos():
    try:
        # Get all files inside the bucket
        objects = object_storage_client.list_objects(
            namespace_name=NAMESPACE, 
            bucket_name=BUCKET_NAME,
            fields="name"
        ).data.objects
        
        photo_data = []
        for obj in objects:
            try:
                # Read the metadata tag to see who uploaded it
                head_req = object_storage_client.head_object(
                    namespace_name=NAMESPACE,
                    bucket_name=BUCKET_NAME,
                    object_name=obj.name
                )
                
                metadata = head_req.headers
                uploader = "Squad Member"
                caption = "Goa Trip!"
                
                for key, value in metadata.items():
                    if key.lower() == 'opc-meta-uploader':
                        uploader = value
                    elif key.lower() == 'opc-meta-caption':
                        caption = value
                
                # Build the direct link so the web browser can display the image
                public_url = f"https://objectstorage.{REGION}.oraclecloud.com/n/{NAMESPACE}/b/{BUCKET_NAME}/o/{obj.name}"
                
                photo_data.append({
                    "url": public_url,
                    "uploader": uploader,
                    "caption": caption
                })
            except Exception:
                continue
            
        return jsonify(photo_data), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)