import os
import psycopg2
from flask import Flask, redirect, request

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db_connection()
    if conn is None:
        print("⚠️ 数据库未配置，跳过初始化")
        return
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id SERIAL PRIMARY KEY,
            link_id TEXT NOT NULL,
            target_url TEXT NOT NULL,
            click_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip TEXT,
            user_agent TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()
    print("✅ 数据库初始化成功")

init_db()

@app.route('/go')
def track_and_redirect():
    target_url = request.args.get('url')
    link_id = request.args.get('id', 'unknown')
    if not target_url:
        return "❌ 缺少 url 参数"
    if not target_url.startswith('https://t.me/') and not target_url.startswith('tg://'):
        return "❌ 只支持 Telegram 链接"
    conn = get_db_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO clicks (link_id, target_url, ip, user_agent) VALUES (%s, %s, %s, %s)",
                (link_id, target_url, request.remote_addr, request.headers.get('User-Agent'))
            )
            conn.commit()
            cur.close()
        except Exception as e:
            print(f"记录失败: {e}")
        finally:
            conn.close()
    return redirect(target_url, 302)

@app.route('/stats')
def all_stats():
    conn = get_db_connection()
    if conn is None:
        return "⚠️ 数据库未配置"
    cur = conn.cursor()
    cur.execute('SELECT link_id, target_url, COUNT(*) FROM clicks GROUP BY link_id, target_url ORDER BY link_id')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return "暂无数据"
    html = "<h1>📊 统计</h1><table border='1'><tr><th>标识</th><th>链接</th><th>点击</th></tr>"
    for link_id, target_url, count in rows:
        html += f"<tr><td>{link_id}</td><td><a href='{target_url}'>{target_url}</a></td><td>{count}</td></tr>"
    html += "</table>"
    return html

@app.route('/stats/<link_id>')
def view_stats(link_id):
    conn = get_db_connection()
    if conn is None:
        return "⚠️ 数据库未配置"
    cur = conn.cursor()
    cur.execute("SELECT target_url, COUNT(*) FROM clicks WHERE link_id = %s GROUP BY target_url", (link_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return f"未找到 {link_id}"
    target_url, count = rows[0]
    return f"<h1>📊 {link_id}</h1><p>链接：{target_url}</p><p>点击次数：{count}</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
