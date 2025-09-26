from functools import wraps
from flask import Flask, flash, jsonify, redirect, url_for, render_template, request,session
from datetime import date, datetime, time, timedelta
from flask_mail import Mail, Message
import random
import string
import psycopg2
import os
from werkzeug.utils import secure_filename
import time
app = Flask(__name__)
app.config["SECRET_KEY"]="Namdz"
app.permanent_session_lifetime = timedelta(minutes= 4)

UPLOAD_FOLDER = 'static\images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
DB_CONFIG = {
    'dbname': 'watershop',
    'user': 'postgres',
    'password': 'admin',
    'host': 'localhost',
    'port': '5432'
}

# Thêm cấu hình email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'nam1234kan@gmail.com'
app.config['MAIL_PASSWORD'] = 'vtxuvfxjtpuwjbji'  # App password, không phải password Gmail thường
mail = Mail(app)
def generate_txid(length=16):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args,**kwargs)
    return decorated_function
@app.context_processor
def inject_unread_count():
    if "user_id" not in session:
        return dict(unread_count=0)

    conn = get_db_connection()
    cur = conn.cursor()
    user_id = session.get("user_id")

    cur.execute("SELECT customer_id FROM customer WHERE user_id = %s", (user_id,))
    customer = cur.fetchone()
    if not customer:
        return dict(unread_count=0)

    customer_id = customer[0]

    cur.execute("SELECT COUNT(*) FROM notifications WHERE customer_id = %s AND is_read = false", (customer_id,))
    unread_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return dict(unread_count=unread_count)

@app.route('/index')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        Select p.product_id, p.product_name, p.price,p.img_url , SUM(ord.quantity) AS total
        FROM product p
        JOIN orderdetail ord 
        ON p.product_id = ord.product_id
        GROUP BY p.product_id, p.product_name, p.price,p.img_url
        ORDER BY COUNT(ord.quantity) DESC
        LIMIT 3
                """)
    products = cur.fetchall()
    cur.execute("SELECT id, title, content, image_url,created_at from blog")
    rows = cur.fetchall()
    
    blogs = []
    for row in rows:
        blogs.append({
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "image_url": row[3] or "https://source.unsplash.com/800x400/?coffee",
        "date": row[4].strftime("%d/%m/%Y")
        })
    cur.close()
    conn.close()    
    product_list = [
        {
            'id': p[0],
            'name': p[1],
            'price': p[2],
            'image_url': p[3] 
        }
        for p in products
    ]
    return render_template('index.html', products=product_list, blogs= blogs)


@app.route('/')
def hello_World():
    return render_template("base.html")
@app.route('/login', methods=["POST","GET"])
def login():
     if request.method == "POST":
        user_id = request.form["user_id"]
        password= request.form["password"]

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Check admin login
            cur.execute("""
                SELECT * FROM public.adminshop
                WHERE admin_id = %s AND password = %s
            """, (user_id, password))

            admin = cur.fetchone()

            if admin:
                session.permanent = True
                session['user_id'] = user_id
                session['username'] = admin[1]  
                session['is_admin'] = True
                flash('Admin đăng nhập thành công!', 'success')
                return redirect(url_for('admin_login'))
            cur.execute("""
                SELECT * FROM public.customer
                WHERE user_id = %s AND password = %s
            """, (user_id, password))

            user = cur.fetchone()

            if user:
                session.permanent = True
                session['user_id'] = user[6]
                session['username'] = user[1] 
                session['is_admin'] = False
                flash('Đăng nhập thành công!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Tài khoản hoặc mật khẩu không đúng!', 'error')

        except Exception as e:
            flash(f'Đã xảy ra lỗi: {str(e)}', 'error')

        finally:
            cur.close()
            conn.close()

     return render_template('login.html')
           
@app.route('/logout')
def log_out():
     session.clear()
     flash ("You logged out!","info")
     return  redirect(url_for("login"))  

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        user_id = request.form['userID']
        user_name= request.form['fullname']
        password = request.form['password']
        phone= request.form['phone']
        address = request.form['Address']
        gender = request.form['gender']
        email = request.form['email']
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
            Select * FROM public.customer WHERE user_id = %s
                   """,(user_id,))
            if cur.fetchone():
                flash('ID đã có người dùng rồi. Vui lòng chọn ID khác','error')
                return render_template('register.html')
            code =''.join(random.choices(string.digits, k=6))
            session['register_info']={
                'user_id': user_id,
                'user_name': user_name,
                'password': password,
                'phone': phone,
                'address': address,
                'gender': gender,
                'email': email,
                'code': code
            }
            msg = Message("Mã xác nhận đăng ký tài khoản", sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Mã xác nhận của bạn là: {code}"
            mail.send(msg)

            flash("Mã xác nhận đã được gửi tới email của bạn. Vui lòng nhập mã để hoàn tất đăng ký.", "info")
            return redirect(url_for('verify_email'))
        except Exception as e:
            flash(f"Lỗi: {str(e)}", 'error')
            return render_template('register.html')
    return render_template('register.html')

@app.route("/verify_email", methods=["GET", "POST"])
def verify_email():
    if request.method == "POST":
        input_code = request.form["code"]
        reg_info = session.get("register_info")

        if not reg_info:
            flash("Thông tin đăng ký không tồn tại hoặc đã hết hạn.", "error")
            return redirect(url_for("register"))

        if input_code == reg_info["code"]:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT count(customer_id) FROM public.customer")
                new_id = cur.fetchone()[0] + 1

                cur.execute("""
                    INSERT INTO public.customer (customer_id, full_name, phone_number, address, gender, user_id, password, email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s,%s)
                """, (
                    new_id, reg_info["user_name"], reg_info["phone"], reg_info["address"],
                    reg_info["gender"], reg_info["user_id"], reg_info["password"], reg_info["email"]
                ))
                conn.commit()
                cur.close()
                session.pop("register_info", None)
                flash("Đăng ký thành công! Bạn có thể đăng nhập.", "success")
                return redirect(url_for("login"))

            except Exception as e:
                flash(f"Lỗi khi tạo tài khoản: {str(e)}", "error")
                return redirect(url_for("register"))

        else:
            flash("Mã xác nhận không đúng. Vui lòng thử lại.", "error")

    return render_template("verify_email.html")
@app.route('/menu')
@login_required
def menu():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT product_id, product_name, price,img_url, c.category_name FROM product p JOIN category c ON p.category_id = c.category_id")
    products = cur.fetchall()

    # Chuyển thành dict dễ dùng bên HTML
    product_list = [
        {
            'id': p[0],
            'name': p[1],
            'price': p[2],
            'image_url': p[3],
            'category':p[4]
        }
        for p in products
    ]
    cur.execute("Select customer_id from customer where customer.user_id =%s",(user_id,))
    customer_row = cur.fetchone()
    if customer_row:
        customerID = customer_row[0]
    else:
    
        customerID = None
    cur.execute("SELECT product_id FROM favorites WHERE customer_id = %s", (customerID,))
    favorite_ids = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return render_template('menu.html', products=product_list, favorite_ids= favorite_ids)
@app.route('/search')
@login_required
def search():
    user_id = session.get('user_id')
    q = request.args.get('q', '')
    category = request.args.get('category', '')
    sort_by = request.args.get('sort_by', 'name')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("Select customer_id from customer where customer.user_id =%s",(user_id,))
    customer_row = cur.fetchone()
    customerID = customer_row[0]
    where_clauses = []
    params = []

    if q:
        where_clauses.append("LOWER(product.product_name) ILIKE %s")
        params.append(f"%{q.lower()}%")

    if category:
        where_clauses.append("category.category_name = %s")
        params.append(category)

    if min_price:
        where_clauses.append("product.price >= %s")
        params.append(min_price)
    if max_price:
        where_clauses.append("product.price <= %s")
        params.append(max_price)
    
    where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''

    order_by_sql = {
        'name': 'ORDER BY product_name ASC',
        'price_asc': 'ORDER BY price ASC',
        'price_desc': 'ORDER BY price DESC'
    }.get(sort_by, 'ORDER BY product_name ASC')

    cur.execute(f"SELECT * FROM product JOIN category ON product.category_id = category.category_id {where_sql} {order_by_sql}", params)
    columns = [desc[0] for desc in cur.description]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.execute("SELECT product_id FROM favorites WHERE customer_id = %s", (customerID,))
    favorite_ids = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return render_template('search.html', results=results, favorite_ids = favorite_ids)
@app.route('/order')
@login_required
def order():
    conn = get_db_connection()
    cur = conn.cursor()
    user_id = session.get('user_id')
    cur.execute("SELECT product_id, product_name, price,img_url FROM product")
    products = cur.fetchall()
    product_list = [
        {
            'id': p[0],
            'name': p[1],
            'price': p[2],
            'image_url': p[3] 
        }
        for p in products
    ]
    cur.execute("Select customer_id from customer WHERE customer.user_id = %s",(user_id,))
    customerID_row = cur.fetchone()
    cur.execute("Select p.product_id, p.product_name, p.price,p.img_url FROM product p JOIN favorites f ON p.product_id = f.product_id WHERE customer_id = %s",(customerID_row[0],))
    favorites= cur.fetchall()
    favorites_list=[
        {
            'id': p[0],
            'name': p[1],
            'price': p[2],
            'image_url': p[3] 
        }
        for p in favorites
    ]
    if customerID_row:
     customerID = customerID_row[0]
     cur.execute("""
        SELECT v.code, v.discount_usd, v.description,v.expiry_date,v.voucher_id
        FROM vouchers v
        JOIN voucher_customers vcus ON v.voucher_id = vcus.voucher_id
        WHERE vcus.customer_id = %s
    """, (customerID,))
     discounts = cur.fetchall()
    else:
     discounts = []
    cur.close()
    conn.close()
    discount_list = [
        {
            'code': d[0],
            'discount': d[1],
            'description': d[2],
            'expiry_date':d[3],
            'id': d[4]
        }
        for d in discounts
    ]
    return render_template('order.html', products= product_list, discounts = discount_list,today = date.today(),favorites_list= favorites_list)
@app.route('/submit_order', methods=['POST'])
@login_required
def submit_order():
    data = request.get_json()
    items = data.get('items', [])
    discount_amount = 0
    discount_code = data.get('discount')  # Nếu có tên mã khuyến mãi
    total_amount = 0
    destination = data.get('destination')
    note = data.get('note')

    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("Select customer_id from customer WHERE customer.user_id = %s",(user_id,))
    customerID_row = cur.fetchone()
    if not customerID_row:
        cur.close()
        conn.close()
        return jsonify({'error': 'Không tìm thấy khách hàng'}), 400
    customerID = customerID_row[0]
    if discount_code:
        cur.execute("""
            SELECT v.discount_usd,vcus.customer_id,v.voucher_id FROM vouchers v
            JOIN voucher_customers vcus ON vcus.voucher_id = v.voucher_id
            WHERE customer_id = %s AND vcus.voucher_id = %s
        """, (customerID, discount_code))
        row = cur.fetchone()
        if row:
            discount_amount = row[0]
            cur.execute("""
            DELETE FROM voucher_customers WHERE customer_id = %s AND voucher_id = %s
            """, (customerID, discount_code))
    if not isinstance(destination, str):
        destination = str(destination)
    if not isinstance(note, str):
        note = str(note)

    if destination.strip() == "":
        cur.execute("""
            SELECT address
            FROM customer
            WHERE customer_id = %s
        """, (customerID,))
        result = cur.fetchone()
        if result and result[0]:
            destination = result[0]
    # Tạo order mới
    for item in items:
        name = item['name']
        quantity = item['quantity']
        cur.execute("SELECT product_id, price FROM product WHERE product_name = %s", (name,))
        product_row = cur.fetchone()
        if not product_row:
            continue
        product_id, price = product_row
        item_total = price * quantity
        total_amount += item_total
    total_amount -= discount_amount
    session['amount'] = total_amount

    if total_amount <= 0:
        total_amount =0
    now = datetime.now()
    cur.execute("Select COUNT(order_id) From orders")
    new_id = cur.fetchone()[0] +1 
    cur.execute("""
        INSERT INTO orders (order_id,customer_id, date_time, total_amount,destination,note)
        VALUES (%s, %s, %s,%s,%s,%s)
    """, (new_id, customerID, now, total_amount,destination,note))
    message = f"Đơn hàng của bạn đã được tạo thành tiền {total_amount} $"
    cur.execute("""
    Insert into notifications(customer_id, message, is_read, created_at) VALUES (%s,%s,%s,NOW())
                """,(customerID, message,False))
    # Thêm từng item
    for item in items:
        name = item['name']
        quantity = item['quantity']

        # Lấy product_id từ product_name
        cur.execute("SELECT product_id FROM product WHERE product_name = %s", (name,))
        product_row = cur.fetchone()
        if not product_row:
            continue  # hoặc bỏ qua nếu tên không đúng
        product_id = product_row[0]
        cur.execute("""
            INSERT INTO orderdetail (order_id, product_id, quantity)
            VALUES (%s, %s, %s)
        """, (new_id, product_id, quantity))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'order_id': new_id})
@app.route('/invoice/<order_id>')
@login_required
def invoice(order_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Lấy thông tin đơn hàng
    cur.execute("""
        SELECT o.order_id, o.date_time, o.total_amount,c.full_name,o.destination
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        WHERE o.order_id = %s
    """, (order_id,))
    row = cur.fetchone()

    if not row:
        return "Không tìm thấy đơn hàng", 404

    order = {
        'order_id': row[0],
        'date_time': row[1],
        'total': row[2],
        'customer_name': row[3],
        'destination':row[4]
    }

    # Lấy các sản phẩm trong đơn hàng
    cur.execute("""
        SELECT p.product_name, p.price, od.quantity
        FROM orderdetail od
        JOIN product p ON od.product_id = p.product_id
        WHERE od.order_id = %s
    """, (order_id,))
    items = cur.fetchall()

    order_items = []
    subtotal = 0

    for item in items:
        name, price, quantity = item
        total_price = price * quantity
        subtotal += total_price
        order_items.append({
            'name': name,
            'price': price,
            'quantity': quantity,
            'total': total_price
        })

    # Tính discount = subtotal - total
    order['subtotal'] = subtotal
    order['discount'] = subtotal - order['total'] if subtotal > order['total'] else 0

    cur.close()
    conn.close()

    return render_template('invoice.html', order=order, items = order_items)

@app.route('/review/<int:product_id>', methods=['GET', 'POST'])
@login_required
def review(product_id):
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("Select customer_id From customer where user_id = %s",(user_id,))
    customer_row = cur.fetchone()
    customerID = customer_row[0] # tim customer_id
    # Kiểm tra đã mua hàng chưa
    cur.execute("""
        SELECT 1
        FROM "orders" o
        JOIN orderdetail od ON o.order_id = od.order_id
        JOIN customer on customer.customer_id = o.customer_id
        WHERE customer.user_id = %s AND od.product_id = %s
        LIMIT 1
    """, (user_id, product_id))
    has_bought = cur.fetchone() is not None

    if request.method == 'POST' and has_bought:
        rate = int(request.form['rating'])
        comment = request.form['comment']
        cur.execute('SELECT r.customer_id FROM review r JOIN customer c ON c.customer_id = r.customer_id WHERE c.user_id = %s AND product_id = %s', (user_id, product_id))
        existing = cur.fetchone()
        
        if existing :
            cur.execute('''
                UPDATE review SET rate = %s, comment = %s
                WHERE customer_id = %s AND product_id = %s
            ''', (rate, comment, customerID, product_id))
        else:
            cur.execute("Select COUNT(review_id) FROM review")
            review_id_row = cur.fetchone()
            reviewID= review_id_row[0] +1 
            cur.execute("""
                INSERT INTO review (review_id,customer_id, product_id, rate, comment)
                VALUES (%s,%s, %s, %s, %s)
            """, (reviewID,customerID, product_id, rate, comment))
        conn.commit()

    # Lấy review cũ
    cur.execute("SELECT rate, comment FROM review r JOIN customer c ON r.customer_id = c.customer_id WHERE c.user_id = %s AND product_id = %s", (user_id, product_id))
    user_review = cur.fetchone()

    # Lấy tất cả đánh giá
    cur.execute("""
        SELECT r.rate, r.comment,c.full_name, r.customer_id
        FROM review r
        JOIN customer c ON r.customer_id = c.customer_id
        WHERE r.product_id = %s
    """, (product_id,))
    reviews = cur.fetchall()

    cur.execute("Select product_name, img_url from product where product.product_id = %s", (product_id,))
    product = cur.fetchone()

    # Trung bình đánh giá
    cur.execute("SELECT ROUND(AVG(rate), 1), COUNT(*) FROM review WHERE product_id = %s", (product_id,))
    row = cur.fetchone()
    avg_rating = float(row[0]) if row[0] else None
    total_reviews = row[1]
    cur.close()
    conn.close()

    return render_template('review.html', product_id=product_id, user_review=user_review,
                           reviews=reviews, avg_rating=avg_rating, has_bought=has_bought, product = product, total_reviews= total_reviews)

@app.route('/account')
@login_required
def account():
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("Select customer_id From customer where user_id = %s",(user_id,))
    customer_row = cur.fetchone()
    customerID = customer_row[0] # tim customer_id
    # Lấy thông tin khách hàng
    cur.execute("""
        SELECT full_name, email, phone_number, address,img_url
        FROM customer
        WHERE user_id = %s
    """, (user_id,))
    customer_info = cur.fetchone()
    # lấy đơn hàng đang trong trạng thái đặt
    cur.execute("""
        SELECT 
            o.order_id, 
            c.full_name,
            c.phone_number,
            o.status,
            STRING_AGG(p.product_name || ' (x' || od.quantity || ')', ', ') AS products,
            o.destination,
            o.note,
            o.total_amount   
        FROM orders o
        JOIN orderdetail od ON o.order_id = od.order_id
        JOIN customer c ON c.customer_id = o.customer_id
        JOIN product p ON p.product_id = od.product_id
        WHERE o.status IN ('Pending', 'Processing', 'Delivered')
        AND c.customer_id = %s
		GROUP BY o.order_id, 
            c.full_name,
            c.phone_number,
            o.status
        ORDER BY o.order_id DESC
                """,(customerID,))
    pending_order = cur.fetchall()
    # Lấy danh sách đơn hàng đã đặt thành công
    cur.execute("""
        SELECT o.order_id, o.date_time, SUM(od.quantity) as total_items,o.destination, SUM(o.total_amount) as total_amount
        FROM orders o
        JOIN orderdetail od ON o.order_id = od.order_id
        JOIN customer c ON c.customer_id = o.customer_id
        WHERE c.user_id = %s
        AND o.status = 'Completed'
        GROUP BY o.order_id, o.date_time
        ORDER BY o.date_time DESC
    """, (user_id,))
    completed_orders = cur.fetchall()

    # Thống kê sản phẩm đặt nhiều nhất
    cur.execute("""
        SELECT p.product_name, SUM(od.quantity) as total_quantity
        FROM orders o
        JOIN orderdetail od ON o.order_id = od.order_id
        JOIN product p ON od.product_id = p.product_id
        JOIN customer c ON c.customer_id = o.customer_id
        WHERE c.user_id = %s
        GROUP BY p.product_name
        ORDER BY total_quantity DESC
        LIMIT 5
    """, (user_id,))
    top_products = cur.fetchall()

    # Tổng tiền đã chi
    cur.execute("""
        SELECT SUM(o.total_amount)
        FROM orders o
        JOIN orderdetail od ON o.order_id = od.order_id
        JOIN customer c ON c.customer_id = o.customer_id
        WHERE c.user_id = %s
    """, (user_id,))
    total_spent = cur.fetchone()[0] or 0
    cur.execute("""
    SELECT
        TO_CHAR(o.date_time, 'YYYY-MM') AS month,
        SUM(o.total_amount) AS total
    FROM orders o
    JOIN orderdetail od ON o.order_id = od.order_id
    WHERE o.customer_id = %s
      AND o.date_time >= CURRENT_DATE - INTERVAL '3 months'
    GROUP BY month
    ORDER BY month
    """, (customerID,))
    spending_data = cur.fetchall()
    labels = [row[0] for row in spending_data]
    values = [float(row[1]) for row in spending_data]
    cur.execute("""
        SELECT 
    p.product_name,
    c.category_name,
    p.price,
    AVG(r.rate) AS avg_rate,
    SUM(od.quantity) AS total_quantity
FROM favorites f
JOIN product p ON f.product_id = p.product_id
JOIN category c ON p.category_id = c.category_id
LEFT JOIN review r ON f.product_id = r.product_id
LEFT JOIN orderdetail od ON od.product_id = f.product_id
WHERE f.customer_id = %s
GROUP BY p.product_name, c.category_name, p.price""",(customerID,))
    favor_product = cur.fetchall()
    cur.close()
    conn.close()
    max_value = max(values) if values else 0
    maxY = ((int(max_value / 10) + 1) * 10)
    return render_template('account.html',
                           customer=customer_info,
                           pending_orders= pending_order,
                           orders=completed_orders,
                           top_products=top_products,
                           total_spent=total_spent,
                           labels = labels,
                           values= values,
                           maxY = maxY,
                           favor_product= favor_product)
@app.route('/update_avatar', methods=['POST'])
@login_required
def update_avatar():
    if 'avatar' not in request.files:
        return {"message": "Không có file được chọn"}, 400
    
    file = request.files['avatar']
    if file.filename == '':
        return {"message": "Chưa chọn file"}, 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        user_id = session['user_id']
        filename = f"user_{user_id}_{filename}"
        upload_folder = os.path.join('static', 'images', 'avatars')
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        avatar_url = f"/static/images/avatars/{filename}"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE customer SET img_url = %s WHERE user_id = %s", (avatar_url, user_id))
        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Cập nhật avatar thành công!", "avatar_url": avatar_url}, 200
    else:
        return {"message": "File không hợp lệ"}, 400

@app.route('/confirm_received/<int:order_id>', methods=['POST'])
@login_required
def confirm_received(order_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE order_id = %s", ('Completed', order_id))
    conn.commit()
    cur.close()
    conn.close()
    flash('Đơn hàng đã được xác nhận nhận thành công!', 'success')
    return redirect(request.referrer or url_for('account'))

def adming_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Bạn không có quyền truy cập chức năng này.','erorr')
            return redirect(url_for('index'))
        return f(*args,**kwargs)
    return decorated_function
@app.route('/admin')
def admin_login():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("Select COUNT(*) from orders WHERE date_time:: date = CURRENT_DATE ")
    total_orders = cur.fetchone()
    cur.execute("Select SUM(total_amount) from orders WHERE date_time:: date = CURRENT_DATE")
    total_amount = cur.fetchone()
    cur.execute("""Select p.product_name,p.img_url, SUM(od.quantity)
                FROM product p 
                JOIN orderdetail od ON p.product_id = od.product_id
                GROUP BY p.product_name,p.img_url
                ORDER BY SUM(od.quantity) DESC
                LIMIT 1 
                """)
    top_product = cur.fetchone()
    cur.execute("""Select c.full_name, o.date_time, o.destination,o.total_amount, o.status
                FROM orders o
                JOIN customer c ON o.customer_id = c.customer_id
                WHERE date_time:: date = CURRENT_DATE""")
    order_row = cur.fetchall()
    order_list=[
        {
            'name': o[0],
            'time': o[1],
            'destination':o[2],
            'total':o[3],
            'status':o[4]

        }
        for o in order_row
    ]
    cur.execute("""
        SELECT EXTRACT(HOUR FROM date_time) AS hour,
               SUM(total_amount) AS revenue
        FROM orders
        WHERE date_time::date = CURRENT_DATE
        GROUP BY hour
        ORDER BY hour
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    # Chuyển sang danh sách đầy đủ 0-23 giờ
    revenue_by_hour = [0]*24
    for hour, revenue in rows:
        revenue_by_hour[int(hour)] = float(revenue)
    return render_template('admin.html', revenue_by_hour=revenue_by_hour, total_orders= total_orders[0], total_amount= total_amount[0],top_product = top_product[0],top_product_image=top_product[1], recent_orders= order_list)
@app.route('/admin/menu')
def admin_menu():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        Select p.product_id,p.product_name, p.price, category.category_name
        From product p
        JOIN category ON category.category_id = p.category_id
                """)
    product_row = cur.fetchall()
    products =[]

    for row in product_row:
        product_id = row[0]
        cur.execute("""
        Select c.full_name,r.rate,r.comment
        FROM review r
        JOIN customer c ON r.customer_id = c.customer_id
        WHERE r.product_id = %s            
                    """,(product_id,))
        comment_rows = cur.fetchall()
        comments=[
            {
                'customer_name':c[0],
                'rating':c[1],
                'comment':c[2]

            }
            for c in comment_rows
        ]
        products.append({
            'id': row[0],
            'name':row[1],
            'price':row[2],
            'category': row[3],
            'comments':comments
        })
    cur.close()
    conn.close()

    return render_template('admin_menu.html',products= products)
@app.route('/admin/add_menu', methods =['GET','POST'])
@adming_required
def add_product():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT category_name FROM category")
    categories = [row[0] for row in cur.fetchall()]
    if request.method == 'POST':
        product_name = request.form['product_name']
        price = float(request.form['price'])
        category_name = request.form['category_name']
        img_url = request.form['img_url']
        if not img_url:
            img_url = "https://png.pngtree.com/png-clipart/20230914/original/pngtree-coffe-cup-vector-png-image_12097117.png"
        try:
            cur.execute(" Select p.product_name from product p WHERE p.product_name = %s",(product_name,))
            existing = cur.fetchone()
            if existing:
                flash("Sản phẩm đã tồn tại",'erorr')
            else:
                cur.execute("Select count(p.product_id) from product p")
                product_id_row = cur.fetchone()
                product_id = product_id_row[0] + 101

                cur.execute("SELECT c.category_id FROM category c WHERE c.category_name = %s", (category_name,))
                category_id_row = cur.fetchone()
                if category_id_row is None:
                    flash("Loại sản phẩm không hợp lệ", 'error')
                else:
                    categoryID = category_id_row[0]

                cur.execute("Insert into product VALUES(%s,%s,%s,%s,%s)",(product_id,product_name,price,categoryID,img_url))
                conn.commit()
                flash("Thêm sản phẩm thành công", 'success')
                return redirect(url_for('admin_menu'))
        except Exception as e:
            flash(f"Lỗi khi thêm sản phẩm: {str(e)}", 'error')

        finally:
            cur.close()
            conn.close()
    return render_template('add_menu.html',categories = categories)
@app.route("/admin/edit_product/<int:product_id>", methods=["POST"])
@adming_required
def edit_product(product_id):
    product_name = request.form['name']
    price = float(request.form['price'])
    category_name = request.form['category']
    img_url = request.form['img_url']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT c.category_id FROM category c WHERE c.category_name = %s", (category_name,))
    category_id_row = cur.fetchone()
    categoryID = category_id_row[0]
    if not img_url:
        img_url = "https://png.pngtree.com/png-clipart/20230914/original/pngtree-coffe-cup-vector-png-image_12097117.png"
    cur.execute("""
        UPDATE product
        SET product_name = %s, price = %s, category_id= %s, img_url=%s
        WHERE product_id = %s
                """,(product_name,price,categoryID,img_url,product_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_menu'))
@app.route("/delete_product/<int:product_id>", methods=["POST"])
@adming_required
def delete_product(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM product WHERE product_id = %s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Xoá sản phẩm thành công!", "success")
    return redirect(url_for("admin_menu"))
@app.route("/admin/employee")
@adming_required
def admin_employee():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        Select * from employee
        ORDER BY employee_id ASC
                """)
    employees = cur.fetchall()
    employee_list = [
        {
        'id': e[0],
        'name': e[1],
        'phone':e[2],
        'dob': e[3],
        'job': e[4],
        'gender':e[5]
        }
    for e in employees
    ]
    cur.close()
    conn.close()
    return render_template("admin_employee.html",employees= employee_list)
@app.route("/admin/add_employee", methods=["POST"])
@adming_required
def add_employee():
    name = request.form["name"]
    phone = request.form["phone"]
    dob = request.form["dob"]
    job = request.form["job"]
    gender = request.form["gender"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("Select COUNT(*) FROM employee")
    employee_row= cur.fetchone()
    employeeID = employee_row[0] + 1 # employee_row la 1 tuple
    cur.execute("""
        INSERT INTO employee (employee_id,full_name, phone_number, dob, type_job, gender)
        VALUES (%s,%s, %s, %s, %s, %s)
    """, (employeeID,name, phone, dob, job, gender))
    conn.commit()
    cur.close()
    conn.close()
    flash("Thêm nhân viên thành công!", "success")
    return redirect(url_for("admin_employee"))

@app.route("/admin/delete_employee/<int:employee_id>", methods=["POST"])
@adming_required
def delete_employee(employee_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM employee WHERE id = %s", (employee_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Xoá nhân viên thành công!", "danger")
    return redirect(url_for("admin_employee"))

@app.route("/admin/edit_employee/<int:employee_id>", methods=["POST"])
@adming_required
def edit_employee(employee_id):
    name = request.form["name"]
    phone = request.form["phone"]
    dob = request.form["dob"]
    job = request.form["job"]
    gender = request.form["gender"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE employee
        SET full_name=%s, phone_number=%s, dob=%s, type_job=%s, gender=%s
        WHERE employee_id=%s
    """, (name, phone, dob, job, gender, employee_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("Cập nhật nhân viên thành công!", "success")
    return {"success": True}
@app.route("/admin/customer")
@adming_required
def admin_customer():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        Select * from customer
        ORDER BY customer_id ASC
                """)
    customers = cur.fetchall()
    customer_list = [
        {
        'id': e[0],
        'name': e[1],
        'phone':e[2],
        'type': e[3],
        'address': e[4],
        'gender':e[5],
        'email': e[8]
        }
    for e in customers
    ]
    cur.close()
    conn.close()
    return render_template("admin_customer.html",customers= customer_list)
@app.route("/admin/add_customer", methods=["POST"])
@adming_required
def add_customer():
    name = request.form["name"]
    phone = request.form["phone"]
    address = request.form["address"]
    gender = request.form["gender"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("Select COUNT(*) FROM employee")
    customer_row= cur.fetchone()
    customerID = customer_row[0] + 1 
    cur.execute("""
        INSERT INTO customer (customer_id,full_name, phone_number,address, gender)
        VALUES (%s,%s, %s, %s, %s, %s)
    """, (customerID,name, phone, address,gender))
    conn.commit()
    cur.close()
    conn.close()
    flash("Thêm nhân viên thành công!", "success")
    return redirect(url_for("admin_customer"))

@app.route("/admin/delete_customer/<int:customer_id>", methods=["POST"])
@adming_required
def delete_customer(customer_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM customer WHERE customer_id = %s", (customer_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Xoá nhân viên khách hàng!", "danger")
    return redirect(url_for("admin_customer"))

@app.route("/admin/edit_customer/<int:customer_id>", methods=["POST"])
@adming_required
def edit_customer(customer_id):
    name = request.form["name"]
    phone = request.form["phone"]
    customer_type = request.form["type"]
    address = request.form["address"]
    gender = request.form["gender"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE customer
        SET full_name=%s, phone_number=%s, customer_type =%s, gender=%s , address =%s
        WHERE customer_id=%s
    """, (name, phone, customer_type,gender, address,customer_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("Cập nhật khách hàng thành công!", "success")
    return redirect(url_for("admin_customer"))
@app.route('/update_order_status/<int:order_id>', methods=['POST'])
@adming_required
def update_order_status(order_id):
    next_status = request.form['status']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE order_id = %s", (next_status, order_id))
    cur.execute("Select customer_id from orders WHERE order_id = %s",(order_id,))
    customerID = cur.fetchone()[0]
    if next_status == 'delivered':
        message = f"Đơn hàng của bạn đang được giao tới hãy để ý điện thoại"
    message = f"Đơn hàng của bạn đã chuyển sang trạng thái {next_status}"
    cur.execute("Insert into notifications (customer_id, message,is_read, created_at) VALUES (%s,%s,%s, NOW())",(customerID, message, False))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('admin_orders'))
@app.route('/admin/orders')
@adming_required
def admin_orders():
    conn = get_db_connection()
    cur = conn.cursor()

    # Lấy đơn hàng chưa hoàn thành và gom sản phẩm
    cur.execute("""
        SELECT 
            o.order_id, 
            c.full_name,
            c.phone_number,
            o.status,
            STRING_AGG(p.product_name || ' (x' || od.quantity || ')', ', ') AS products,
            o.destination,
            o.note,
            o.total_amount
        FROM orders o
        JOIN orderdetail od ON o.order_id = od.order_id
        JOIN customer c ON c.customer_id = o.customer_id
        JOIN product p ON p.product_id = od.product_id
        WHERE o.status IN ('Pending', 'Processing', 'Delivered')
		GROUP BY o.order_id, 
            c.full_name,
            c.phone_number,
            o.status
        ORDER BY o.order_id DESC
    """)
    pending_orders = cur.fetchall()
    # Lấy đơn hàng đã hoàn thành (mỗi đơn 1 dòng)
    cur.execute("""
        SELECT o.order_id, c.full_name,o.date_time,o.destination,o.total_amount, o.status
        FROM orders o
        JOIN customer c ON c.customer_id = o.customer_id 
        WHERE o.status = 'Completed'
        ORDER BY o.order_id DESC
    """)
    completed_orders = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'admin_orders.html',
        pending_orders= pending_orders,
        completed_orders=completed_orders
    )
@app.route("/admin/shift")
@adming_required
def admin_shift():
    conn = get_db_connection()
    cur = conn.cursor()

    # Ca làm hôm nay
    cur.execute("""
        SELECT e.employee_id, e.full_name, s.date, s.shift_amount
        FROM shift s
        JOIN employee e ON s.employee_id = e.employee_id
        WHERE s.date = CURRENT_DATE
    """)
    shifts = [
        {"employee_id": r[0], "full_name": r[1], "date": r[2], "shift_amount": r[3]}
        for r in cur.fetchall()
    ]

    cur.execute("""
        SELECT e.employee_id, e.full_name, s.date, s.shift_amount
        FROM shift s
        JOIN employee e ON s.employee_id = e.employee_id
        WHERE s.date < CURRENT_DATE
        ORDER BY s.date DESC
    """)
    past_shift = [
        {"employee_id": r[0], "full_name": r[1], "date": r[2], "shift_amount": r[3]}
        for r in cur.fetchall()
    ]
    cur.execute("SELECT employee_id, full_name FROM employee ORDER BY full_name")
    employees = [
        {"employee_id": r[0], "full_name": r[1]}
        for r in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return render_template(
        'admin_shift.html',
        today_shifts=shifts,
        employees=employees,
        past_shifts=past_shift
    )

@app.route("/admin/add_shift",  methods=['POST'])
@adming_required
def add_shift():
    employee_id = request.form["employee_id"]
    shift_count = request.form["shift_count"]
    today = date.today()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO shift (employee_id, date, shift_amount)
            VALUES (%s, %s, %s)
        """, (employee_id, today, shift_count))
        conn.commit()
        flash("Đã thêm ca làm thành công!", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("Nhân viên này đã có ca làm hôm nay!", "danger")
    cur.close()
    conn.close()
    return redirect(url_for("admin_shift"))
@app.route('/admin/shifts_edit/<int:employee_id>/<path:work_date>', methods=['GET', 'POST'])
@adming_required
def shift_edit(employee_id, work_date):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        shifts_count = request.form['shifts_count']
        cur.execute("""
            UPDATE shift
            SET shifts_amount = %s
            WHERE employee_id = %s AND date = %s
        """, (shifts_count, employee_id, work_date))
        print(employee_id, work_date)
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_shift'))
    else:
        cur.execute("""
            SELECT * FROM shift
            WHERE employee_id = %s AND date = %s
        """, (employee_id, work_date))
        shift = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('admin_shift.html', shift=shift)
@app.route('/admin/voucher', methods=['GET', 'POST'])
def add_voucher():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        code = generate_unique_code(cur)
        description = request.form['description']
        discount_amount = request.form['discount_usd']
        end_date = request.form['expiry_date']
        customers = request.form.getlist('customers')  # danh sách customer_id
        cur.execute("Select count(*) from vouchers")
        voucher_row = cur.fetchone()
        voucherID = voucher_row[0]+1
        # Thêm voucher
        cur.execute("""
            INSERT INTO vouchers (voucher_id,code, description, discount_usd, expiry_date)
            VALUES (%s,%s, %s, %s, %s)
        """, (voucherID,code, description, discount_amount,  end_date))
        

        # Gán voucher cho nhiều khách
        for customer_id in customers:
            cur.execute("""
                INSERT INTO voucher_customers (voucher_id, customer_id)
                VALUES (%s, %s)
            """, (voucherID, customer_id))
            message = f"Bạn có thêm voucher mới{code} có giá trị {discount_amount} $ hết hạn lúc {end_date}"
            cur.execute("""
                Insert into notifications (customer_id, message,is_read, created_at) VALUES(%s,%s,%s,NOW())
                """,(customer_id, message,False))
        conn.commit()
        cur.close()
        conn.close()

        return redirect('/admin/voucher')
    cur.execute("""
        SELECT v.code, v.discount_usd, v.expiry_date, v.description,
               STRING_AGG(c.full_name || ' (' || c.phone_number || ')', ', ') AS customer_names
        FROM vouchers v
        LEFT JOIN voucher_customers vc ON v.voucher_id = vc.voucher_id
        LEFT JOIN customer c ON vc.customer_id = c.customer_id
        GROUP BY v.code, v.discount_usd, v.expiry_date, v.description
        ORDER BY v.expiry_date DESC
    """)
    vouchers = [
        {"code": row[0], "discount_usd": row[1], "expiry_date": row[2], "description": row[3], "customer_names": row[4]}
        for row in cur.fetchall()
    ]

    cur.execute("SELECT customer_id, full_name,phone_number FROM customer")
    customers = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('admin_voucher.html', customers=customers, vouchers=vouchers)
def generate_unique_code(cur, length=8):
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        cur.execute("SELECT COUNT(*) FROM vouchers WHERE code = %s", (code,))
        if cur.fetchone()[0] == 0:
            return code
@app.route('/admin/statistic')
def statistics():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT e.employee_id, e.full_name, COUNT(s.shift_amount) AS total_shifts,
               COUNT(s.shift_amount) * 3 AS salary_usd
        FROM employee e
        LEFT JOIN shift s ON e.employee_id = s.employee_id
        WHERE s.date >= date_trunc('month', CURRENT_DATE)
        GROUP BY e.employee_id, e.full_name
        ORDER BY salary_usd DESC;
    """)
    salaries = cur.fetchall()
    cur.execute("""
        SELECT c.full_name,c.address,c.phone_number,c.customer_type, SUM(o.total_amount) AS total_spent
        FROM customer c
        JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.full_name,c.address,c.phone_number,c.customer_type
        ORDER BY total_spent DESC
        LIMIT 10;
    """)
    top_customers = cur.fetchall()

    # 3. Biểu đồ tròn: món được đặt nhiều nhất
    cur.execute("""
        SELECT p.product_name, SUM(od.quantity) AS total_qty
        FROM orderdetail od
        JOIN product p ON od.product_id = p.product_id
        GROUP BY p.product_name
        ORDER BY total_qty DESC
        LIMIT 8;
    """)
    popular_products = cur.fetchall()

    # 4. Biểu đồ cột: doanh thu 15 ngày gần nhất
    cur.execute("""
        SELECT date_time::date, SUM(total_amount) AS daily_revenue
        FROM orders
        WHERE date_time >= CURRENT_DATE - INTERVAL '15 days'
        GROUP BY date_time::date
        ORDER BY date_time::date;
    """)
    revenue_last_15_days = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('admin_statistic.html',
                           salaries=salaries,
                           top_customers=top_customers,
                           popular_products=popular_products,
                           revenue_last_15_days=revenue_last_15_days)
@app.route('/toggle_favorite/<int:product_id>', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Bạn cần đăng nhập để sử dụng chức năng yêu thích!", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("Select customer_id from customer where customer.user_id =%s",(user_id,))
    customer_row = cur.fetchone()
    customerID = customer_row[0]
    cur.execute("SELECT 1 FROM favorites WHERE customer_id = %s AND product_id = %s", (customerID, product_id))
    exists = cur.fetchone()
    if exists:
        
        cur.execute("DELETE FROM favorites WHERE customer_id = %s AND product_id = %s", (customerID, product_id))
        flash("Đã bỏ khỏi danh sách yêu thích", "info")
    else:
        cur.execute("INSERT INTO favorites (customer_id, product_id) VALUES (%s, %s)", (customerID, product_id))
        flash("Đã thêm vào danh sách yêu thích!", "success")
    conn.commit()
    cur.close()
    conn.close()

    return redirect(request.referrer or url_for('search'))
@app.route("/blog")
def blog():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, title, content, image_url, created_at
        FROM blog
        ORDER BY created_at DESC
    """)
    blogs = []
    for row in cur.fetchall():
        blogs.append({
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "short_content": row[2][:120] + "...",  # hiển thị tóm tắt
            "image_url": row[3],
            "date": row[4].strftime("%d/%m/%Y")
        })
    
    cur.close()
    conn.close()
    return render_template("blog.html", blogs=blogs)
@app.route("/blog/<int:blog_id>")
def blog_detail(blog_id):
    user_id = session.get("user_id")
    conn = get_db_connection()
    cur = conn.cursor()

    # Lấy thông tin bài blog
    cur.execute("SELECT id, title, content, image_url, created_at FROM blog WHERE id=%s", (blog_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return "Bài viết không tồn tại", 404

    blog = {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "image_url": row[3] or "https://source.unsplash.com/800x400/?coffee",
        "date": row[4].strftime("%d/%m/%Y")
    }

    # Lấy số lượt like
    cur.execute("SELECT COUNT(*) FROM blog_likes WHERE blog_id=%s", (blog_id,))
    blog["likes"] = cur.fetchone()[0]

    # Lấy danh sách comment
    cur.execute("""
        SELECT c.full_name,bc.content, bc.created_at,c.img_url
        FROM blog_comments bc
        JOIN customer c ON bc.customer_id = c.customer_id
        WHERE bc.blog_id=%s
        ORDER BY bc.created_at ASC
    """, (blog_id,))
    comments = []
    for customer, text, created_at,img_url in cur.fetchall():
        comments.append({
            "user": customer,
            "text": text,
            "created_at": created_at.strftime("%d/%m/%Y %H:%M"),
            "img_url": img_url
        })

    blog["comments"] = comments
    liked = False
    if user_id:
        cur.execute("SELECT customer_id FROM customer WHERE user_id=%s", (user_id,))
        customer_row = cur.fetchone()
        if customer_row:
            customer_id = customer_row[0]
            cur.execute("SELECT 1 FROM blog_likes WHERE blog_id=%s AND customer_id=%s", (blog_id, customer_id))
            liked = cur.fetchone() is not None

    cur.close()
    conn.close()
    return render_template("blog_detail.html", blog=blog, liked= liked)
@app.route("/blog/like", methods=["POST"])
def blog_like():
    conn = get_db_connection()
    cur= conn.cursor()
    blog_id = request.form["blog_id"]
    user_id = session.get('user_id')
    cur.execute("Select customer_id from customer where customer.user_id =%s",(user_id,))
    customerID = cur.fetchone()[0]
    try:
        cur.execute("Select * from blog_likes WHERE blog_id = %s AND customer_id = %s",(blog_id,customerID))
        exist = cur.fetchone()
        if exist:
            cur.execute("DELETE FROM blog_likes WHERE blog_id = %s AND customer_id =%s",(blog_id,customerID))
            conn.commit()
        else:
            cur.execute("INSERT INTO blog_likes (blog_id, customer_id) VALUES (%s,%s)", (blog_id, customerID))
            conn.commit()
    except:
        conn.rollback()  # user đã like rồi thì bỏ qua

    cur.execute("SELECT COUNT(*) FROM blog_likes WHERE blog_id=%s", (blog_id,))
    likes = cur.fetchone()[0]
    cur.close()
    return jsonify({"likes": likes})

@app.route("/blog/comment", methods=["POST"])
def blog_comment():
    if "user_id" not in session:
        return jsonify({"error": "Bạn cần đăng nhập để bình luận"}), 403

    conn = get_db_connection()
    cur = conn.cursor()

    blog_id = request.form["blog_id"]
    text = request.form["text"]
    user_id = session.get("user_id")
    cur.execute("SELECT customer_id, full_name, img_url FROM customer WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "Không tìm thấy người dùng"}), 404

    customerID, name, avatar_url = row
    if not avatar_url:
        avatar_url = "/static/img/default_avatar.png"

    created_at = datetime.now()
    cur.execute(
        "INSERT INTO blog_comments (blog_id, customer_id, content, created_at) VALUES (%s,%s,%s,%s)",
        (blog_id, customerID, text, created_at)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({
        "user": name,
        "avatar_url": avatar_url,
        "content": text,
        "created_at": created_at.strftime("%Y-%m-%d %H:%M")
    })


# Route form thêm blog
@app.route('/admin/add_blog', methods=['GET', 'POST'])
@adming_required
def add_blog():
    conn = get_db_connection()
    cur= conn.cursor()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename) 
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            image_url = f"/static\images\{filename}"  

            cur.execute("""
                    Select COUNT(*) from blog    
                        """)
            blog_id = cur.fetchone()[0] +1 
            cur.execute("Insert into blog VALUES(%s,%s,%s,%s)",(blog_id,title,content,image_url,))
            message = f"Đã có blog mới về <b style='color:brown'>{title}</b>, hãy cùng khám phá ngay thôi nào!"
            cur.execute("Select customer_id from customer")
            customers = cur.fetchall()
            for cus in customers:
                customer_id = cus[0]
                cur.execute("Insert into notifications (customer_id, message,is_read,created_at) VALUES(%s,%s,%s,NOW())",(customer_id,message,False))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('admin_login'))
    cur.execute("""
        SELECT id, title, content, image_url, created_at
        FROM blog
        ORDER BY created_at DESC
    """)
    blogs = []
    for row in cur.fetchall():
        blogs.append({
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "short_content": row[2][:120] + "...",  # hiển thị tóm tắt
            "image_url": row[3],
            "date": row[4].strftime("%d/%m/%Y")
        })
    return render_template('add_blog.html',blogs= blogs)
@app.route("/contact")
def contact():
    return render_template("contact.html")
@app.route('/update_user_info', methods=['POST'])
def update_user_info():
    print("UPDATE_USER_INFO route called")
    data = request.get_json()
    print("data:", data)

    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401
    data = request.get_json()
    username = data.get('username')
    phone = data.get('phone')
    address = data.get('address')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE customer SET full_name =%s, phone_number=%s, address=%s WHERE user_id=%s
        """, (username, phone, address, session['user_id']))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(str(e))
        return jsonify({'success': False, 'message': str(e)})
@app.route("/notifications")
@login_required
def notifications_page():
    return render_template("notice.html") 
@app.route("/notification")
@login_required
def notification():
        conn = get_db_connection()
        cur= conn.cursor()
        user_id = session.get("user_id")
        cur.execute("Select customer_id from customer WHERE user_id = %s",(user_id,))
        customerid = cur.fetchone()[0]
        cur.execute("Select * from notifications WHERE customer_id = %s ORDER BY created_at DESC",(customerid,))
        notifications = cur.fetchall()
        notification_list=[
            {
                "id" : n[0],
                "message" : n[2],
                "is_read" : n[3],
                "time": n[4].strftime("%Y-%m-%d %H:%M")

            }
            for n in notifications
        ]
        return jsonify(notification_list)
@app.route("/notifications/read/<int:notif_id>", methods=["POST"])
def mark_notification_as_read(notif_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s", (notif_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
@app.route("/pay", methods=["POST"])
def pay():
    method = request.form.get("payment_method")
    order_id = request.form.get("order_id")

    if method == "cash":
        return f"Đơn hàng {order_id} sẽ thanh toán tiền mặt."
    elif method == "qr":
        return redirect(url_for("choose_bank", order_id=order_id))
@app.route("/choose_bank")
def choose_bank():
    return render_template("choose_bank.html")

@app.route("/login_bank", methods=["POST"])
def login_bank():
    conn = get_db_connection()
    cur= conn.cursor()
    user_id = session.get("user_id")
    if not user_id:
            print("Session user_id không tồn tại!", flush=True)
            return redirect(url_for("login"))
    cur.execute("Select customer_id from customer WHERE user_id = %s",(user_id,))
    customerid = cur.fetchone()[0]
    cur.execute("Select email from customer WHERE customer_id = %s",(customerid,))
    email = cur.fetchone()[0]
    otp_code = str(random.randint(100000, 999999))  
    session["otp"] = otp_code
    msg = Message("Mã OTP xác thực thanh toán",sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f"Mã OTP của bạn là: {otp_code}. Vui lòng nhập trong vòng 5 phút."
    mail.send(msg)
    session["otp_expire"] = time.time() + 300 
    print("OTP gửi tới email:", otp_code, flush=True) 
    bank_name = request.form.get("bank_code")
    amount = float(session.get("amount",0))
    transaction_code = generate_txid(32)
    bank_info = {
        "VCB": {
            "name": "Vietcombank",
            "logo": "/static/logo/vietcombank.jpg"
        },
        "NCB": {
            "name": "NCB",
            "logo": "/static/logo/vietcombank.jpg"
        },
        "ACB": {
            "name": "ACB",
            "logo": "/static/logo/acb.jpg"
        },
        "TCB": {
            "name": "Techcombank",
            "logo": "/static/logo/techcombank.png"
        },
        "MB":{
            "name": "MB Bank",
            "logo": "/static/logo/mb.png"
        },
        "BIDV":{
            "name": "BIDV",
            "logo": "/static/logo/bidv.png"
        },
        "Agribank":{
            "name": "Agribank",
            "logo": "/static/logo/Agribank.png"
        },
        "NAMA":{
            "name": "NAMA",
            "logo": "/static/logo/NAMA.jpg"
        },
        "SHB":{
            "name": "SHB",
            "logo": "/static/logo/SHB.png"
        },
        "TPBank":{
            "name": "TPBank",
            "logo": "/static/logo/TPBank.jpg"
        },
        "Vietinbank":{
            "name": "VietinBank",
            "logo": "/static/logo/vietinbank.jpg"
        },
        "VPBank":{
            "name": "VPBank",
            "logo": "/static/logo/VPBank.jpg"
        }

    }

    selected_bank = bank_info.get(bank_name, {})
    return render_template(
        "bank_login.html",
        bank=selected_bank,
        amount=amount,
        transaction_code=transaction_code
    )

@app.route("/confirm_otp", methods=["GET", "POST"])
def confirm_otp():
    if request.method == "GET":
        return render_template("otp_bank.html", message="Mã OTP đã được gửi. Vui lòng nhập trong 5 phút.")
    else:  
        otp = request.form.get("otp")
        saved_otp = session.get("otp")
        expire_time = session.get("otp_expire")
        if not saved_otp or not expire_time:
            return render_template("otp_bank.html", error="⚠️ OTP không tồn tại hoặc đã hết hạn.")

        if time.time() > expire_time:
            return render_template("otp_bank.html", error="❌ OTP đã hết hạn, vui lòng yêu cầu gửi lại.")
        print(otp)
        if otp == saved_otp:
            session.pop("otp", None)
            session.pop("otp_expire", None)
            return redirect(url_for("index"))
        else:
            return redirect(url_for("confirm_otp"))

@app.route("/payment_return")
def payment_return():
    return "✅ Thanh toán thành công (giả lập)!"

if __name__ == "__main__":
    app.run(debug=True)

