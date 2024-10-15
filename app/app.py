from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # ใช้สำหรับจัดการ session

# ฟังก์ชันการเชื่อมต่อกับฐานข้อมูล
def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    return connection

# หน้าแรก
@app.route('/')
def index():
    return redirect(url_for('login'))

# หน้า login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))

    return render_template('login.html')

# หน้า register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))
        conn.commit()

        # สร้างบัญชีใหม่สำหรับผู้ใช้
        user_id = cursor.lastrowid
        cursor.execute('INSERT INTO accounts (user_id, balance) VALUES (%s, %s)', (user_id, 0))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

# หน้าหลัก (dashboard)
@app.route('/dashboard')
def dashboard():
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # ดึงยอดคงเหลือ
    cursor.execute('SELECT balance FROM accounts WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()

    # ดึงประวัติธุรกรรม
    cursor.execute('SELECT * FROM transactions WHERE user_id = %s ORDER BY id DESC', (user_id,))
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('dashboard.html', balance=balance['balance'] if balance else 0, transactions=transactions)

# ฝากเงิน
@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        amount = request.form['amount']
        user_id = session['user_id']

        if not amount.isdigit() or float(amount) <= 0:
            flash('Invalid amount. Please enter a positive number.')
            return redirect(url_for('deposit'))

        amount = float(amount)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE accounts SET balance = balance + %s WHERE user_id = %s', (amount, user_id))
            cursor.execute('INSERT INTO transactions (user_id, amount, transaction_type) VALUES (%s, %s, %s)', (user_id, amount, 'deposit'))
            conn.commit()

            flash('Deposit successful!')
        except Exception as e:
            flash('An error occurred while processing your deposit.')
            print(e)  # หรือบันทึกลงใน log
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard'))

    return render_template('deposit.html')

# โอนเงิน
@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        to_user = request.form['to_user']
        amount = request.form['amount']
        from_user = session['user_id']

        if not amount.isdigit() or float(amount) <= 0:
            flash('Invalid amount. Please enter a positive number.')
            return redirect(url_for('transfer'))

        amount = float(amount)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # ตรวจสอบว่าผู้รับเงินมีอยู่ในระบบ
            cursor.execute('SELECT id FROM users WHERE username = %s', (to_user,))
            to_user_record = cursor.fetchone()

            if not to_user_record:
                flash('Recipient not found.')
                return redirect(url_for('transfer'))

            to_user_id = to_user_record[0]

            # ตรวจสอบยอดเงินของผู้ใช้
            cursor.execute('SELECT balance FROM accounts WHERE user_id = %s', (from_user,))
            balance = cursor.fetchone()

            if balance is None:
                flash('Account not found.')
                return redirect(url_for('dashboard'))

            balance = balance[0]

            if balance >= amount:
                cursor.execute('UPDATE accounts SET balance = balance - %s WHERE user_id = %s', (amount, from_user))
                cursor.execute('UPDATE accounts SET balance = balance + %s WHERE user_id = %s', (amount, to_user_id))
                
                # บันทึกประวัติการโอนเงิน
                cursor.execute('INSERT INTO transactions (user_id, amount, transaction_type) VALUES (%s, %s, %s)', (from_user, -amount, 'transfer'))
                cursor.execute('INSERT INTO transactions (user_id, amount, transaction_type) VALUES (%s, %s, %s)', (to_user_id, amount, 'transfer'))
                conn.commit()
                
                flash('Transfer successful!')
            else:
                flash('Insufficient balance!')

        except Exception as e:
            conn.rollback()  # ยกเลิกการดำเนินการในกรณีมีข้อผิดพลาด
            flash('An error occurred during the transfer. Please try again.')
            print(f"Error: {e}")  # แสดงข้อผิดพลาดใน console เพื่อการดีบั๊ก

        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard'))

    return render_template('transfer.html')


# ออกจากระบบ
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
