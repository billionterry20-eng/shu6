"""
步数自动提交系统
支持多账号管理、定时任务、提交记录
"""

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import pytz
import os
import json
import time as time_module

# 创建应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'step-automation-secret-key-2026')

# 数据库配置 - 使用绝对路径
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, 'step_automation.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False}
}

db = SQLAlchemy(app)

# 北京时区
beijing_tz = pytz.timezone('Asia/Shanghai')

# API 配置
API_URL = "http://8.140.250.130/king/api/step"

# 有效的 Token（从用户提供的成功请求中提取）
# 注意：这些 token 可能需要定期更新
DEFAULT_AUTH_TOKEN = "5740554d9df2c55b707e0240034920ff"
DEFAULT_TIME_TOKEN = "1772282799860"

# 全局定时任务调度器（延迟初始化）
scheduler = None


# ==================== 数据库模型 ====================

class Account(db.Model):
    """账号模型"""
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    steps = db.Column(db.Integer, default=38889)
    hour = db.Column(db.Integer, default=0)
    minute = db.Column(db.Integer, default=5)
    enabled = db.Column(db.Boolean, default=True)
    auth_token = db.Column(db.String(64), default=DEFAULT_AUTH_TOKEN)
    time_token = db.Column(db.String(20), default=DEFAULT_TIME_TOKEN)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(beijing_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(beijing_tz), onupdate=lambda: datetime.now(beijing_tz))
    
    def to_dict(self):
        return {
            'id': self.id,
            'phone': self.phone,
            'password': '********',
            'steps': self.steps,
            'hour': self.hour,
            'minute': self.minute,
            'enabled': self.enabled,
            'schedule': f"{self.hour:02d}:{self.minute:02d}",
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class SubmitRecord(db.Model):
    """提交记录模型"""
    __tablename__ = 'submit_records'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    steps = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(500))
    response_code = db.Column(db.Integer)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(beijing_tz))
    
    def to_dict(self):
        account = Account.query.get(self.account_id)
        return {
            'id': self.id,
            'account_phone': account.phone if account else 'Unknown',
            'steps': self.steps,
            'status': self.status,
            'message': self.message,
            'response_code': self.response_code,
            'submitted_at': self.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if self.submitted_at else None
        }


class SystemLog(db.Model):
    """系统日志模型"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), default='INFO')
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(beijing_tz))
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


# ==================== 核心功能 ====================

def add_log(message, level='INFO'):
    """添加系统日志"""
    try:
        log = SystemLog(level=level, message=message)
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"[LOG ERROR] {message} - {e}")
        db.session.rollback()


def submit_steps_to_api(phone, password, steps, auth_token=None, time_token=None):
    """
    提交步数到 API
    
    Args:
        phone: 账号
        password: 密码
        steps: 步数
        auth_token: Authorization token（可选）
        time_token: Time token（可选）
    
    Returns:
        (success: bool, message: str, response_code: int)
    """
    # 使用提供的 token 或默认 token
    auth = auth_token if auth_token else DEFAULT_AUTH_TOKEN
    time_val = time_token if time_token else DEFAULT_TIME_TOKEN
    
    headers = {
        "Host": "8.140.250.130",
        "Accept": "*/*",
        "Authorization": auth,
        "X-Requested-With": "XMLHttpRequest",
        "time": time_val,
        "Accept-Language": "zh-TW,zh-Hant;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "http://8.140.250.130",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
        "Referer": "http://8.140.250.130/bushu/",
        "Connection": "keep-alive"
    }
    
    data = {
        "phone": phone,
        "pwd": password,
        "num": str(steps)
    }
    
    try:
        print(f"[DEBUG] 提交请求: phone={phone}, steps={steps}")
        print(f"[DEBUG] 使用 token: auth={auth[:16]}..., time={time_val}")
        
        response = requests.post(API_URL, headers=headers, data=data, timeout=30)
        result = response.json()
        
        print(f"[DEBUG] 响应: {result}")
        
        success = result.get('code') == 200 and result.get('msg') == 'success'
        message = result.get('data') or result.get('msg', 'Unknown response')
        response_code = result.get('code', 0)
        
        return success, message, response_code
        
    except requests.exceptions.RequestException as e:
        error_msg = f"网络请求错误: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg, 0
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg, 0


def record_submission(account_id, steps, success, message, response_code):
    """记录提交结果"""
    try:
        record = SubmitRecord(
            account_id=account_id,
            steps=steps,
            status='success' if success else 'failed',
            message=message,
            response_code=response_code
        )
        db.session.add(record)
        db.session.commit()
    except Exception as e:
        print(f"记录提交结果失败: {e}")
        db.session.rollback()


# ==================== 定时任务 ====================

def init_scheduler():
    """初始化定时任务调度器"""
    global scheduler
    
    if scheduler is not None:
        return
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BackgroundScheduler(timezone=beijing_tz)
        scheduler.start()
        
        # 加载所有账号的定时任务
        with app.app_context():
            try:
                accounts = Account.query.all()
                for account in accounts:
                    if account.enabled:
                        schedule_job(account)
                add_log(f"定时任务调度器已启动，已加载 {len([a for a in accounts if a.enabled])} 个任务", 'INFO')
            except Exception as e:
                add_log(f"加载定时任务失败: {e}", 'ERROR')
                
    except Exception as e:
        print(f"初始化调度器失败: {e}")


def schedule_job(account):
    """为账号设置定时任务"""
    global scheduler
    
    if scheduler is None:
        return
    
    job_id = f"job_{account.id}"
    
    # 移除已存在的任务
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
    except:
        pass
    
    # 添加新任务
    try:
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger(hour=account.hour, minute=account.minute)
        scheduler.add_job(
            func=execute_job,
            trigger=trigger,
            id=job_id,
            args=[account.id],
            replace_existing=True,
            misfire_grace_time=3600
        )
        print(f"[SCHEDULER] 账号 {account.phone} 定时任务已设置: {account.hour:02d}:{account.minute:02d}")
    except Exception as e:
        add_log(f"设置账号 {account.phone} 定时任务失败: {e}", 'ERROR')


def execute_job(account_id):
    """执行定时任务"""
    with app.app_context():
        try:
            account = Account.query.get(account_id)
            if not account:
                add_log(f"账号 ID {account_id} 不存在", 'ERROR')
                return
            
            if not account.enabled:
                add_log(f"账号 {account.phone} 已禁用，跳过", 'INFO')
                return
            
            add_log(f"开始执行账号 {account.phone} 的定时任务", 'INFO')
            
            success, message, code = submit_steps_to_api(
                account.phone, 
                account.password, 
                account.steps,
                account.auth_token,
                account.time_token
            )
            
            record_submission(account.id, account.steps, success, message, code)
            
            if success:
                add_log(f"账号 {account.phone} 提交成功: {account.steps} 步", 'INFO')
            else:
                add_log(f"账号 {account.phone} 提交失败: {message}", 'WARNING')
                
        except Exception as e:
            add_log(f"执行任务失败: {e}", 'ERROR')


def remove_job(account_id):
    """移除定时任务"""
    global scheduler
    
    if scheduler is None:
        return
    
    job_id = f"job_{account_id}"
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
    except:
        pass


# ==================== 路由 ====================

@app.route('/')
def index():
    """首页"""
    try:
        accounts = Account.query.all()
        recent_records = SubmitRecord.query.order_by(SubmitRecord.submitted_at.desc()).limit(10).all()
        
        total_accounts = len(accounts)
        enabled_accounts = sum(1 for a in accounts if a.enabled)
        
        today = datetime.now(beijing_tz).date()
        today_records = SubmitRecord.query.filter(
            db.func.date(SubmitRecord.submitted_at) == today
        ).all()
        today_success = sum(1 for r in today_records if r.status == 'success')
        
        return render_template('index.html', 
                              accounts=accounts, 
                              recent_records=recent_records,
                              total_accounts=total_accounts,
                              enabled_accounts=enabled_accounts,
                              today_submissions=len(today_records),
                              today_success=today_success)
    except Exception as e:
        add_log(f"首页加载失败: {e}", 'ERROR')
        return f"Error: {e}", 500


@app.route('/accounts')
def accounts_page():
    """账号管理页面"""
    try:
        accounts = Account.query.all()
        return render_template('accounts.html', accounts=accounts)
    except Exception as e:
        add_log(f"账号页面加载失败: {e}", 'ERROR')
        return f"Error: {e}", 500


@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """获取所有账号"""
    try:
        accounts = Account.query.all()
        return jsonify({'success': True, 'data': [a.to_dict() for a in accounts]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/accounts', methods=['POST'])
def create_account():
    """创建账号"""
    try:
        data = request.get_json()
        
        if not data or not data.get('phone') or not data.get('password'):
            return jsonify({'success': False, 'message': '账号和密码不能为空'}), 400
        
        account = Account(
            phone=data['phone'],
            password=data['password'],
            steps=data.get('steps', 38889),
            hour=data.get('hour', 0),
            minute=data.get('minute', 5),
            enabled=data.get('enabled', True),
            auth_token=data.get('auth_token', DEFAULT_AUTH_TOKEN),
            time_token=data.get('time_token', DEFAULT_TIME_TOKEN)
        )
        
        db.session.add(account)
        db.session.commit()
        
        # 设置定时任务
        schedule_job(account)
        
        add_log(f"创建账号: {account.phone}", 'INFO')
        return jsonify({'success': True, 'message': '账号创建成功', 'data': account.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    """更新账号"""
    try:
        account = Account.query.get_or_404(account_id)
        data = request.get_json()
        
        if 'phone' in data:
            account.phone = data['phone']
        if 'password' in data:
            account.password = data['password']
        if 'steps' in data:
            account.steps = data['steps']
        if 'hour' in data:
            account.hour = data['hour']
        if 'minute' in data:
            account.minute = data['minute']
        if 'enabled' in data:
            account.enabled = data['enabled']
        if 'auth_token' in data:
            account.auth_token = data['auth_token']
        if 'time_token' in data:
            account.time_token = data['time_token']
        
        db.session.commit()
        
        # 重新设置定时任务
        schedule_job(account)
        
        add_log(f"更新账号: {account.phone}", 'INFO')
        return jsonify({'success': True, 'message': '账号更新成功', 'data': account.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """删除账号"""
    try:
        account = Account.query.get_or_404(account_id)
        phone = account.phone
        
        # 移除定时任务
        remove_job(account_id)
        
        db.session.delete(account)
        db.session.commit()
        
        add_log(f"删除账号: {phone}", 'INFO')
        return jsonify({'success': True, 'message': '账号删除成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/accounts/<int:account_id>/submit', methods=['POST'])
def manual_submit(account_id):
    """手动提交"""
    try:
        account = Account.query.get_or_404(account_id)
        
        print(f"[API] 手动提交: account_id={account_id}, phone={account.phone}")
        
        success, message, code = submit_steps_to_api(
            account.phone,
            account.password,
            account.steps,
            account.auth_token,
            account.time_token
        )
        
        record_submission(account.id, account.steps, success, message, code)
        
        if success:
            return jsonify({'success': True, 'message': f'提交成功: {account.steps} 步'})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/records')
def records_page():
    """提交记录页面"""
    try:
        page = request.args.get('page', 1, type=int)
        pagination = SubmitRecord.query.order_by(SubmitRecord.submitted_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        return render_template('records.html', pagination=pagination)
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/api/records', methods=['GET'])
def get_records():
    """获取提交记录"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        account_id = request.args.get('account_id', type=int)
        
        query = SubmitRecord.query
        if account_id:
            query = query.filter_by(account_id=account_id)
        
        pagination = query.order_by(SubmitRecord.submitted_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [r.to_dict() for r in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/logs')
def logs_page():
    """系统日志页面"""
    try:
        page = request.args.get('page', 1, type=int)
        pagination = SystemLog.query.order_by(SystemLog.created_at.desc()).paginate(
            page=page, per_page=50, error_out=False
        )
        return render_template('logs.html', pagination=pagination)
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取系统日志"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        level = request.args.get('level')
        
        query = SystemLog.query
        if level:
            query = query.filter_by(level=level)
        
        pagination = query.order_by(SystemLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [l.to_dict() for l in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        total_accounts = Account.query.count()
        enabled_accounts = Account.query.filter_by(enabled=True).count()
        
        today = datetime.now(beijing_tz).date()
        today_records = SubmitRecord.query.filter(
            db.func.date(SubmitRecord.submitted_at) == today
        ).all()
        
        today_success = sum(1 for r in today_records if r.status == 'success')
        
        return jsonify({
            'success': True,
            'data': {
                'accounts': {'total': total_accounts, 'enabled': enabled_accounts},
                'today': {'total': len(today_records), 'success': today_success}
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/test-submit', methods=['POST'])
def test_submit():
    """测试提交 API"""
    try:
        data = request.get_json() or {}
        phone = data.get('phone', 'Tbh2356@126.com')
        password = data.get('password', '112233qq')
        steps = data.get('steps', 38889)
        
        success, message, code = submit_steps_to_api(phone, password, steps)
        
        return jsonify({
            'success': success,
            'message': message,
            'code': code
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 初始化 ====================

def init_db():
    """初始化数据库"""
    with app.app_context():
        try:
            db.create_all()
            print("[INIT] 数据库表已创建")
            
            # 创建默认账号（使用新的成功参数）
            if Account.query.count() == 0:
                default_account = Account(
                    phone="Tbh2356@126.com",
                    password="112233qq",
                    steps=38889,
                    hour=0,
                    minute=5,
                    enabled=True,
                    auth_token=DEFAULT_AUTH_TOKEN,
                    time_token=DEFAULT_TIME_TOKEN
                )
                db.session.add(default_account)
                db.session.commit()
                print(f"[INIT] 默认账号已创建: Tbh2356@126.com")
                
        except Exception as e:
            print(f"[INIT] 初始化数据库失败: {e}")


# 应用启动时初始化
@app.before_request
def before_first_request():
    """第一次请求时初始化"""
    if not hasattr(app, '_initialized'):
        init_scheduler()
        app._initialized = True


# 如果是直接运行
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
