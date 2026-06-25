import os
import psycopg2
from flask import Flask, redirect, request

app = Flask(__name__)

# 从环境变量获取数据库连接URL
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """获取数据库连接，如果 DATABASE_URL 不存在则返回 None"""
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """初始化数据库表（如果 DATABASE_URL 存在）"""
    conn = get_db_connection()
    if conn is None:
        print("⚠️ DATABASE_URL 未设置，跳过数据库初始化")
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
    print("✅ 数据库表初始化成功")

# 启动时初始化
init_db()

# =============================================
# 路由：点击跳转
# 使用方式：https://你的域名/go?url=https://t.me/任意链接&id=标识名
# =============================================
@app.route('/go')
def track_and_redirect():
    target_url = request.args.get('url')
    link_id = request.args.get('id', 'unknown')

    if not target_url:
        return "❌ 缺少 url 参数，请使用 ?url=https://t.me/你的链接"

    if not target_url.startswith('https://t.me/') and not target_url.startswith('tg://'):
        return "❌ 只支持跳转到 Telegram 链接 (https://t.me/... 或 tg://...)"

    # 记录点击（如果数据库可用）
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
            print(f"数据库记录失败: {e}")
        finally:
            conn.close()
    else:
        print("⚠️ 数据库未连接，跳过记录")

    return redirect(target_url, 302)

# =============================================
# 路由：统筹查看所有链接统计
# 访问：https://你的域名/stats
# =============================================
@app.route('/stats')
def all_stats():
    conn = get_db_connection()
    if conn is None:
        return "⚠️ 数据库未配置，请先在 Railway 添加 PostgreSQL 数据库"

    cur = conn.cursor()
    cur.execute('''
        SELECT link_id, target_url, COUNT(*) 
        FROM clicks 
        GROUP BY link_id, target_url 
        ORDER BY link_id
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return "📊 暂无任何点击数据"

    html = """
    <h1>📊 所有链接点击统计</h1>
    <table border="1" cellpadding="10" style="border-collapse:collapse;">
        <tr style="background:#f0f0f0;">
            <th>标识 (link_id)</th>
            <th>目标链接</th>
            <th>点击次数</th>
        </tr>
    """
    for link_id, target_url, count in rows:
        html += f"""
        <tr>
            <td><strong>{link_id}</strong></td>
            <td><a href="{target_url}" target="_blank">{target_url}</a></td>
            <td style="text-align:center;font-size:20px;">{count}</td>
        </tr>
        """
    html += "</table>"
    return html

# =============================================
# 路由：查看单个链接统计
# 访问：https://你的域名/stats/标识名
# =============================================
@app.route('/stats/<link_id>')
def view_stats(link_id):
    conn = get_db_connection()
    if conn is None:
        return "⚠️ 数据库未配置，请先在 Railway 添加 PostgreSQL 数据库"

    cur = conn.cursor()
    cur.execute(
        "SELECT target_url, COUNT(*) FROM clicks WHERE link_id = %s GROUP BY target_url",
        (link_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return f"未找到标识为 '{link_id}' 的点击记录"

    target_url, count = rows[0]
    return f"""
    <h1>📊 链接统计</h1>
    <p><strong>标识：</strong>{link_id}</p>
    <p><strong>目标链接：</strong><a href="{target_url}" target="_blank">{target_url}</a></p>
    <p><strong>点击次数：</strong>{count}</p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
