from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit
import eventlet
from datetime import datetime

# Set up Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Hardcoded users - in a real app this would come from a database
users = {
    'user_a': {'id': 'user_a', 'name': 'User A', 'likes_received': 0, 'unread_notifications': 0},
    'user_b': {'id': 'user_b', 'name': 'User B', 'likes_received': 0, 'unread_notifications': 0}
}

# Store chat messages
chat_messages = []

@app.route('/')
def index():
    return render_template('index.html', users=users)

@app.route('/login/<user_id>')
def login(user_id):
    if user_id in users:
        session['user_id'] = user_id
        # Reset unread notifications when user logs in
        users[user_id]['unread_notifications'] = 0
        return render_template('dashboard.html', 
                              current_user=users[user_id],
                              users={k:v for k,v in users.items() if k != user_id},
                              chat_messages=chat_messages)
    return "User not found", 404

@socketio.on('send_like')
def handle_like(data):
    sender_id = session.get('user_id')
    receiver_id = data['receiver_id']
    
    if sender_id and receiver_id in users:
        # Update like count for receiver
        users[receiver_id]['likes_received'] += 1
        users[receiver_id]['unread_notifications'] += 1
        
        # Emit notification to the specific receiver
        emit('receive_notification', {
            'message': f"{users[sender_id]['name']} liked your profile!",
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'likes_count': users[receiver_id]['likes_received'],
            'unread_count': users[receiver_id]['unread_notifications']
        }, broadcast=True)  # Broadcasting to all clients, but we'll filter on the frontend
        
        return {'status': 'success'}
    return {'status': 'error'}

@socketio.on('send_message')
def handle_message(data):
    sender_id = session.get('user_id')
    message = data['message']
    
    if sender_id and message:
        # Create message object
        new_message = {
            'sender_id': sender_id,
            'sender_name': users[sender_id]['name'],
            'message': message,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        # Store message
        chat_messages.append(new_message)
        if len(chat_messages) > 50:  # Keep only last 50 messages
            chat_messages.pop(0)
            
        # Update unread notification counts for other users
        for user_id in users:
            if user_id != sender_id:
                users[user_id]['unread_notifications'] += 1
        
        # Broadcast message to all clients
        emit('new_chat_message', new_message, broadcast=True)
        
        # Also notify users about new messages
        for user_id in users:
            if user_id != sender_id:
                emit('receive_notification', {
                    'message': f"New message from {users[sender_id]['name']}",
                    'sender_id': sender_id,
                    'receiver_id': user_id,
                    'unread_count': users[user_id]['unread_notifications']
                }, broadcast=True)
                
        return {'status': 'success'}
    return {'status': 'error'}

@socketio.on('read_notifications')
def handle_read_notifications():
    user_id = session.get('user_id')
    if user_id:
        users[user_id]['unread_notifications'] = 0
        return {'status': 'success'}
    return {'status': 'error'}

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)