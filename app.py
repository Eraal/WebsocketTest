from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit
import eventlet

# Set up Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Hardcoded users - in a real app this would come from a database
users = {
    'user_a': {'id': 'user_a', 'name': 'User A', 'likes_received': 0},
    'user_b': {'id': 'user_b', 'name': 'User B', 'likes_received': 0}
}

@app.route('/')
def index():
    return render_template('index.html', users=users)

@app.route('/login/<user_id>')
def login(user_id):
    if user_id in users:
        session['user_id'] = user_id
        return render_template('dashboard.html', 
                              current_user=users[user_id],
                              users={k:v for k,v in users.items() if k != user_id})
    return "User not found", 404

@socketio.on('send_like')
def handle_like(data):
    sender_id = session.get('user_id')
    receiver_id = data['receiver_id']
    
    if sender_id and receiver_id in users:
        # Update like count for receiver
        users[receiver_id]['likes_received'] += 1
        
        # Emit notification to the specific receiver
        emit('receive_notification', {
            'message': f"{users[sender_id]['name']} liked your profile!",
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'likes_count': users[receiver_id]['likes_received']
        }, broadcast=True)  # Broadcasting to all clients, but we'll filter on the frontend
        
        return {'status': 'success'}
    return {'status': 'error'}

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)