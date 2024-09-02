# # from flask import Flask, render_template, jsonify, send_from_directory
# # from flask_socketio import SocketIO
# # import json
# # import pypylon.pylon as pylon

# # app = Flask(__name__)
# # app.config['SECRET_KEY'] = 'mysecret'
# # socketio = SocketIO(app)

# # # Directory paths
# # IMAGES_DIR = '/home/jetson/Documents/testing/testing_program_v1/captured_frames_c1'

# # @app.route('/images/<path:filename>')
# # def serve_images(filename):
# #     return send_from_directory(IMAGES_DIR, filename)

# # @app.route('/')
# # def index():
# #     return render_template('index_v1.html')

# # @app.route('/dashboard-data')
# # def dashboard_data():
# #     try:
# #         with open('dashboard_data.json', 'r') as f:
# #             data = json.load(f)
# #         return jsonify(data)
# #     except Exception as e:
# #         print(f"Failed to load dashboard data: {e}")
# #         return jsonify({})

# # def check_camera_status():
# #     """Check the camera connection status."""
# #     try:
# #         camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
# #         camera.Open()
# #         return 'Connected'
# #     except Exception as e:
# #         print(f"Camera status check error: {e}")
# #         return 'Not Available'

# # def update_dashboard():
# #     """Update dashboard data and emit to clients."""
# #     try:
# #         # Read the existing dashboard data
# #         with open('dashboard_data.json', 'r') as f:
# #             data = json.load(f)
        
# #         # Update the camera status
# #         data['camera_status'] = check_camera_status()
        
# #         # Emit updated data to all connected clients
# #         socketio.emit('update_dashboard', data)
# #     except Exception as e:
# #         print(f"Failed to load and emit dashboard data: {e}")

# # @socketio.on('connect')
# # def handle_connect():
# #     print('Client connected.')
# #     update_dashboard()

# # @socketio.on('disconnect')
# # def handle_disconnect():
# #     print('Client disconnected.')

# # if __name__ == "__main__":
# #     # Run the app with debug mode enabled
# #     socketio.run(app, debug=True)

# from flask import Flask, render_template, jsonify, send_from_directory
# from flask_socketio import SocketIO
# import json
# import pypylon.pylon as pylon

# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'mysecret'
# socketio = SocketIO(app)

# # Directory paths
# IMAGES_DIR = '/home/jetson/Documents/testing/testing_program_v1/captured_frames_c1'

# @app.route('/images/<path:filename>')
# def serve_images(filename):
#     return send_from_directory(IMAGES_DIR, filename)

# @app.route('/')
# def index():
#     return render_template('index_v1.html')

# @app.route('/dashboard-data')
# def dashboard_data():
#     try:
#         with open('/home/jetson/Documents/testing/testing_program_v1/hole_detection_results.json', 'r') as f:
#             data = json.load(f)
#         return jsonify(data)
#     except Exception as e:
#         print(f"Failed to load dashboard data: {e}")
#         return jsonify({})

# def check_camera_status():
#     """Check the camera connection status."""
#     try:
#         camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
#         camera.Open()
#         return 'Connected'
#     except Exception as e:
#         print(f"Camera status check error: {e}")
#         return 'Not Available'

# def update_dashboard():
#     """Update dashboard data and emit to clients."""
#     try:
#         # Read the existing dashboard data
#         with open('/home/jetson/Documents/testing/testing_program_v1/hole_detection_results.json', 'r') as f:
#             data = json.load(f)
        
#         # Update the camera status
#         data['camera_status'] = check_camera_status()
        
#         # Emit updated data to all connected clients
#         socketio.emit('update_dashboard', data)
#     except Exception as e:
#         print(f"Failed to load and emit dashboard data: {e}")

# @socketio.on('connect')
# def handle_connect():
#     print('Client connected.')
#     update_dashboard()

# @socketio.on('disconnect')
# def handle_disconnect():
#     print('Client disconnected.')

# if __name__ == "__main__":
#     # Run the app with debug mode enabled
#     socketio.run(app, debug=True)

from flask import Flask, render_template, jsonify, send_from_directory
from flask_socketio import SocketIO
import json
import pypylon.pylon as pylon

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app)

# Directory paths
IMAGES_DIR = '/home/jetson/Documents/testing/testing_program_v1/captured_frames_c1'

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(IMAGES_DIR, filename)

@app.route('/')
def index():
    return render_template('index_v1.html')

@app.route('/dashboard-data')
def dashboard_data():
    try:
        with open('/home/jetson/Documents/testing/testing_program_v1/hole_detection_results.json', 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"Failed to load dashboard data: {e}")
        return jsonify({})

def check_camera_status():
    """Check the camera connection status."""
    try:
        camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        camera.Open()
        return 'Connected'
    except Exception as e:
        print(f"Camera status check error: {e}")
        return 'Not Available'

def update_dashboard():
    """Update dashboard data and emit to clients."""
    try:
        # Read the existing dashboard data
        with open('/home/jetson/Documents/testing/testing_program_v1/hole_detection_results.json', 'r') as f:
            data = json.load(f)
        
        # Update the camera status
        data['camera_status'] = check_camera_status()
        
        # Add the image path to the data
        data['stitched_image_path'] = 'stitched_image_v1.jpg'
        
        # Emit updated data to all connected clients
        socketio.emit('update_dashboard', data)
    except Exception as e:
        print(f"Failed to load and emit dashboard data: {e}")

@socketio.on('connect')
def handle_connect():
    print('Client connected.')
    update_dashboard()

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected.')

if __name__ == "__main__":
    # Run the app with debug mode enabled
    socketio.run(app, debug=True)