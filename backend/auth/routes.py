from flask import Blueprint, request, jsonify, current_app
from flask_bcrypt import Bcrypt
import jwt
import datetime
from functools import wraps

auth_bp = Blueprint("auth", __name__)
bcrypt = Bcrypt()

# --- TOKEN KONTROL MEKANİZMASI (DECORATOR) ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Token header'da 'x-access-token' veya 'Authorization' olarak gelebilir
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        elif 'Authorization' in request.headers:
            # Genelde "Bearer <token>" formatında gelir
            token = request.headers['Authorization'].replace("Bearer ", "")

        if not token:
            return jsonify({'message': 'Token eksik! Lütfen giriş yapın.'}), 401

        try:
            # Token'ı çöz ve geçerliliğini kontrol et
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            # İsterseniz burada user_id ile veritabanı kontrolü de yapabilirsiniz
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token süresi dolmuş. Tekrar giriş yapın.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Geçersiz token!'}), 401

        return f(*args, **kwargs)

    return decorated

# --- KAYIT OLMA (SIGNUP) ---
@auth_bp.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    # ... (Mevcut kodlarınızın aynısı buraya gelecek) ...
    # Kodu kısaltmak için burayı özet geçiyorum, eski signup kodunuzu koruyun.
    # Sadece importlar ve üstteki decorator yeni eklendi.
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('userType', 'student')

    if not all([username, email, password]):
        return jsonify({"success": False, "error": "Tüm alanlar zorunludur"}), 400

    db = current_app.config.get("DB")
    
    if user_type == 'teacher':
        auth_col = db.auth_teachers
    else:
        auth_col = db.auth_users
    
    if auth_col.find_one({'email': email}):
        return jsonify({"success": False, "error": "Bu e-posta zaten kayıtlı"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    user_doc = {
        "username": username,
        "email": email,
        "password": hashed_pw,
        "userType": user_type,
        "status": "active",
        "created_at": datetime.datetime.utcnow()
    }
    
    # Teacher özel alanları
    if user_type == 'teacher':
        user_doc["employeeId"] = data.get('employeeId')
        user_doc["department"] = data.get('department')
    
    auth_col.insert_one(user_doc)

    return jsonify({"success": True, "message": "Kayıt başarılı"})

# --- GİRİŞ YAPMA (SIGNIN - GÜNCELLENDİ) ---
@auth_bp.route('/api/signin', methods=['POST'])
def api_signin():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('userType', 'student')

    if not all([email, password]):
        return jsonify({"success": False, "error": "Email ve şifre zorunlu"}), 400

    db = current_app.config.get("DB")
    
    if user_type == 'teacher':
        auth_col = db.auth_teachers
    else:
        auth_col = db.auth_users
    
    user = auth_col.find_one({'email': email})
    
    if not user or not bcrypt.check_password_hash(user['password'], password):
        return jsonify({"success": False, "error": "Geçersiz email veya şifre"}), 401
    
    # --- JWT TOKEN ÜRETİMİ ---
    # Token 24 saat geçerli olacak
    token = jwt.encode({
        'user_id': str(user['_id']),
        'email': user['email'],
        'userType': user_type,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")

    user_info = {
        "_id": str(user['_id']),
        "username": user['username'],
        "email": user['email'],
        "userType": user_type
    }

    return jsonify({
        "success": True, 
        "message": "Giriş başarılı",
        "token": token,  # <-- Token'ı frontend'e gönderiyoruz
        "user": user_info
    })

# --- ÖRNEK KORUMALI ROTA (TEST İÇİN) ---
@auth_bp.route('/api/protected-test', methods=['GET'])
@token_required  # <-- Bu decorator rotayı korur
def protected_route():
    return jsonify({"message": "Bu mesajı görüyorsanız token geçerlidir!"})