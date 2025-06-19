# -*- coding: utf-8 -*-
"""
Created on Thu Jun 19 22:26:11 2025

@author: Flyer
"""

from flask import Flask, request, abort
import json
import requests
import pandas as pd
import os
import threading
import time

app = Flask(__name__)

# LINE Bot 設定 - 從環境變數讀取
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET')

# LINE API URLs
LINE_API_REPLY = 'https://api.line.me/v2/bot/message/reply'
LINE_API_PUSH = 'https://api.line.me/v2/bot/message/push'

# Headers for LINE API
def get_headers():
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }

# 載入數據
try:
    df = pd.read_csv("Player Per Game.csv")
    print(f"數據載入成功：{len(df)} 筆記錄")
except FileNotFoundError:
    print("找不到 Player Per Game.csv 文件")
    df = pd.DataFrame()
except Exception as e:
    print(f"載入數據時發生錯誤: {e}")
    df = pd.DataFrame()

@app.route('/')
def home():
    """首頁 - 顯示 Bot 狀態"""
    token_status = "✅ 已設定" if LINE_CHANNEL_ACCESS_TOKEN != 'YOUR_CHANNEL_ACCESS_TOKEN' else "❌ 未設定"
    secret_status = "✅ 已設定" if LINE_CHANNEL_SECRET != 'YOUR_CHANNEL_SECRET' else "❌ 未設定"
    
    return f"""
    <h1>🏀 NBA LINE Bot 服務器</h1>
    <p>✅ 服務器正在運行中</p>
    <p>📊 數據已載入：{len(df) if not df.empty else 0} 筆球員記錄</p>
    <p>🤖 LINE Bot Webhook: <code>/callback</code></p>
    <p>🌐 部署平台: Render</p>
    
    <hr>
    <h3>設定狀態：</h3>
    <p>📱 Channel Access Token: {token_status}</p>
    <p>🔐 Channel Secret: {secret_status}</p>
    
    <hr>
    <h3>使用方法：</h3>
    <p>在 LINE 中發送訊息給 Bot：</p>
    <ul>
        <li><code>!LeBron James</code> - 查詢生涯數據</li>
        <li><code>!LeBron James 2012</code> - 查詢特定年份</li>
        <li><code>!2012 LAL</code> - 查詢球隊名單</li>
        <li><code>help</code> - 查看說明</li>
    </ul>
    
    <hr>
    <h3>測試連接：</h3>
    <p><a href="/test">點擊測試 Webhook</a></p>
    <p><a href="/health">健康檢查</a></p>
    """

@app.route('/test')
def test_webhook():
    """測試端點"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is working",
        "platform": "Render",
        "data_loaded": not df.empty,
        "data_records": len(df) if not df.empty else 0,
        "token_configured": LINE_CHANNEL_ACCESS_TOKEN != 'YOUR_CHANNEL_ACCESS_TOKEN',
        "secret_configured": LINE_CHANNEL_SECRET != 'YOUR_CHANNEL_SECRET'
    }

@app.route('/health')
def health_check():
    """健康檢查端點 - 防止 Render 睡眠"""
    return {
        'status': 'healthy', 
        'message': 'NBA LINE Bot is running on Render',
        'data_status': 'loaded' if not df.empty else 'not_loaded'
    }

def send_reply_message(reply_token, messages):
    """發送回覆訊息"""
    try:
        data = {
            'replyToken': reply_token,
            'messages': messages
        }
        
        response = requests.post(
            LINE_API_REPLY,
            headers=get_headers(),
            data=json.dumps(data)
        )
        
        if response.status_code != 200:
            print(f"Reply failed: {response.status_code}, {response.text}")
        else:
            print("Reply sent successfully")
        
    except Exception as e:
        print(f"發送回覆失敗: {e}")

def send_push_message(user_id, messages):
    """發送推送訊息"""
    try:
        data = {
            'to': user_id,
            'messages': messages
        }
        
        response = requests.post(
            LINE_API_PUSH,
            headers=get_headers(),
            data=json.dumps(data)
        )
        
        if response.status_code != 200:
            print(f"Push failed: {response.status_code}, {response.text}")
        else:
            print("Push message sent successfully")
        
    except Exception as e:
        print(f"發送推送失敗: {e}")

def get_team_roster(year, team):
    """獲取特定年份特定球隊的所有球員名單"""
    try:
        # 從本地 CSV 獲取特定年份和球隊的數據
        team_data = df[(df['season'] == year) & (df['tm'].str.upper() == team.upper())]
        
        if team_data.empty:
            # 檢查該年份是否有數據
            year_data = df[df['season'] == year]
            if year_data.empty:
                available_years = sorted(df['season'].unique())
                years_text = "、".join(map(str, available_years[-10:]))  # 顯示最近10年
                return None, f"找不到 {year} 年的數據。\n\n📅 可查詢年份(最近10年)：{years_text}"
            
            # 該年份有數據但找不到球隊，列出該年份所有球隊
            available_teams = sorted(year_data['tm'].unique())
            teams_text = "、".join(available_teams)
            return None, f"找不到 {year} 年 {team.upper()} 隊的數據。\n\n🏀 {year} 年可查詢球隊：\n{teams_text}"
        
        # 獲取球員名單，按照場均得分排序
        players = team_data.sort_values('pts_per_game', ascending=False)
        
        # 格式化球員名單
        roster_text = f"""🏀 {year} 年 {team_data['tm'].iloc[0]} 隊球員名單

👥 共 {len(players)} 名球員：

"""
        
        # 添加每個球員的基本資訊
        for i, (_, player) in enumerate(players.iterrows(), 1):
            roster_text += f"{i:2d}. {player['player']} ({player['pos']}) - {player['pts_per_game']:.1f}分\n"
        
        roster_text += f"""
📊 球隊統計：
• 平均得分：{players['pts_per_game'].mean():.1f} 分
• 最高得分：{players['pts_per_game'].max():.1f} 分 ({players.loc[players['pts_per_game'].idxmax(), 'player']})
• 最多助攻：{players['ast_per_game'].max():.1f} 次 ({players.loc[players['ast_per_game'].idxmax(), 'player']})
• 最多籃板：{players['trb_per_game'].max():.1f} 個 ({players.loc[players['trb_per_game'].idxmax(), 'player']})

💡 查詢個別球員數據：
輸入 !球員名字 {year}
"""
        
        return roster_text, f"{year} 年 {team_data['tm'].iloc[0]} 隊"
        
    except Exception as e:
        print(f"獲取球隊名單失敗: {e}")
        return None, f"處理 {year} 年 {team} 隊數據時發生錯誤"

def get_player_season_stats(player_name, year):
    """獲取球員特定賽季統計數據"""
    try:
        # 從本地 CSV 獲取球員數據
        player_data = df[df['player'].str.contains(player_name, case=False, na=False)]
        
        if player_data.empty:
            return None, f"找不到球員 '{player_name}'，請檢查拼寫。"
        
        actual_player_name = player_data['player'].iloc[0]
        
        # 找特定年份的數據
        season_data = player_data[player_data['season'] == year]
        
        if season_data.empty:
            # 列出該球員有數據的年份
            available_years = sorted(player_data['season'].unique())
            years_text = "、".join(map(str, available_years))
            return None, f"找不到 {actual_player_name} 在 {year} 年的數據。\n\n📅 可查詢年份：{years_text}"
        
        # 獲取該賽季數據
        season_stats = season_data.iloc[0]
        
        # 格式化賽季統計文字
        stats_text = f"""🏀 {actual_player_name} {year} 賽季數據

📊 場均數據：
• 得分：{season_stats['pts_per_game']:.1f} 分
• 助攻：{season_stats['ast_per_game']:.1f} 次
• 籃板：{season_stats['trb_per_game']:.1f} 個
• 抄截：{season_stats['stl_per_game']:.1f} 次
• 阻攻：{season_stats['blk_per_game']:.1f} 次

🎯 投籃數據：
• 投籃命中率：{(season_stats['fg_percent'] * 100):.1f}%
• 三分命中率：{(season_stats['x3p_percent'] * 100) if pd.notna(season_stats['x3p_percent']) else 0:.1f}%
• 罰球命中率：{(season_stats['ft_percent'] * 100) if pd.notna(season_stats['ft_percent']) else 0:.1f}%

📈 詳細數據：
• 球隊：{season_stats['tm']}
• 位置：{season_stats['pos']}
• 年齡：{season_stats['age']:.0f} 歲
• 出賽：{season_stats['g']} 場
• 先發：{season_stats['gs']:.0f} 場
• 上場時間：{season_stats['mp_per_game']:.1f} 分鐘

💡 想看詳細圖表？請訪問：
https://nba-alltime-search-charts.onrender.com/

💡 查詢生涯數據：
輸入 !{actual_player_name}
"""
        
        return stats_text, actual_player_name
        
    except Exception as e:
        print(f"獲取球員賽季數據失敗: {e}")
        return None, f"處理 {player_name} {year} 年數據時發生錯誤"

def get_player_stats_text(player_name):
    """獲取球員統計文字資料 (不使用圖片)"""
    try:
        # 從本地 CSV 獲取球員數據
        player_data = df[df['player'].str.contains(player_name, case=False, na=False)]
        
        if player_data.empty:
            return None, f"找不到球員 '{player_name}'，請檢查拼寫。"
        
        actual_player_name = player_data['player'].iloc[0]
        
        # 計算生涯平均數據
        career_stats = {
            '得分': player_data['pts_per_game'].mean(),
            '助攻': player_data['ast_per_game'].mean(),
            '籃板': player_data['trb_per_game'].mean(),
            '抄截': player_data['stl_per_game'].mean(),
            '阻攻': player_data['blk_per_game'].mean(),
            '投籃命中率': (player_data['fg_percent'].mean() * 100) if 'fg_percent' in player_data.columns else 0,
            '出賽場數': player_data['g'].sum(),
            '賽季數': len(player_data)
        }
        
        # 最佳賽季
        best_scoring_season = player_data.loc[player_data['pts_per_game'].idxmax()]
        
        # 格式化統計文字
        stats_text = f"""🏀 {actual_player_name} 生涯數據

📊 生涯平均：
• 得分：{career_stats['得分']:.1f} 分
• 助攻：{career_stats['助攻']:.1f} 次
• 籃板：{career_stats['籃板']:.1f} 個
• 抄截：{career_stats['抄截']:.1f} 次
• 阻攻：{career_stats['阻攻']:.1f} 次
• 投籃命中率：{career_stats['投籃命中率']:.1f}%

🎯 生涯總計：
• 總出賽：{career_stats['出賽場數']:.0f} 場
• 職業生涯：{career_stats['賽季數']} 個賽季

⭐ 最佳得分賽季：
• {best_scoring_season['season']} 賽季
• 場均 {best_scoring_season['pts_per_game']:.1f} 分

💡 想看詳細圖表？請訪問：
https://nba-alltime-search-charts.onrender.com/

💡 查詢特定年份數據：
輸入 !球員名字 年份 (例如：!LeBron James 2012)
"""
        
        return stats_text, actual_player_name
        
    except Exception as e:
        print(f"獲取球員數據失敗: {e}")
        return None, f"處理 {player_name} 數據時發生錯誤"

def verify_signature(signature, body):
    """驗證 LINE 簽名"""
    import hashlib
    import hmac
    import base64
    
    if not signature:
        print("沒有收到簽名")
        return False
        
    if LINE_CHANNEL_SECRET == 'YOUR_CHANNEL_SECRET':
        print("Channel Secret 尚未設定")
        return False
    
    try:
        hash = hmac.new(
            LINE_CHANNEL_SECRET.encode('utf-8'),
            body,  # 使用原始 bytes，不要轉換為字串
            hashlib.sha256
        ).digest()
        
        expected_signature = base64.b64encode(hash).decode()
        
        print(f"收到的簽名: {signature}")
        print(f"計算的簽名: {expected_signature}")
        
        return expected_signature == signature
        
    except Exception as e:
        print(f"簽名驗證錯誤: {e}")
        return False

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取請求簽名和內容
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data()  # 獲取原始 bytes
    body_text = body.decode('utf-8')  # 轉換為文字用於解析
    
    print(f"收到 POST 請求")
    print(f"簽名: {signature}")
    print(f"內容長度: {len(body)}")
    
    # 如果是開發階段，可以暫時跳過簽名驗證
    SKIP_SIGNATURE_CHECK = False  # 設為 True 可暫時跳過驗證
    
    if not SKIP_SIGNATURE_CHECK:
        # 驗證簽名
        if not verify_signature(signature, body):
            print("簽名驗證失敗")
            abort(400)
    else:
        print("跳過簽名驗證 (開發模式)")
    
    try:
        # 解析請求
        data = json.loads(body_text)
        print(f"解析的數據: {data}")
        
        for event in data.get('events', []):
            if event['type'] == 'message' and event['message']['type'] == 'text':
                handle_text_message(event)
                
    except Exception as e:
        print(f"處理請求時發生錯誤: {e}")
        abort(400)
    
    return 'OK'

def handle_text_message(event):
    """處理文字訊息"""
    reply_token = event['replyToken']
    user_id = event['source']['userId']
    user_message = event['message']['text'].strip()
    
    print(f"收到訊息: {user_message}")
    
    # 檢查是否為球員查詢
    if user_message.startswith('!') or user_message.startswith('/'):
        # 移除命令前綴
        query = user_message[1:].strip()
        
        if not query:
            reply_text = """請輸入查詢指令：

🏀 查詢生涯數據：
• !LeBron James

📅 查詢特定年份：
• !LeBron James 2012

👥 查詢球隊名單：
• !2012 LAL
• !2016 GSW"""
            send_reply_message(reply_token, [
                {'type': 'text', 'text': reply_text}
            ])
            return
        
        # 解析查詢內容
        parts = query.split()
        
        # 檢查是否為球隊查詢格式 (年份 球隊)
        if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 4:
            # 球隊查詢：年份 + 球隊縮寫
            year = int(parts[0])
            team = parts[1]
            
            print(f"球隊查詢 - 年份: {year}, 球隊: {team}")
            
            stats_text, actual_name = get_team_roster(year, team)
            
            if stats_text is None:
                send_reply_message(reply_token, [
                    {'type': 'text', 'text': actual_name}  # actual_name 此時是錯誤訊息
                ])
                return
            
            # 發送球隊名單
            send_reply_message(reply_token, [
                {'type': 'text', 'text': stats_text}
            ])
            return
        
        # 球員查詢邏輯 (原有功能)
        year = None
        player_name = query
        
        # 檢查最後一個部分是否為年份 (4位數字)
        if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 4:
            year = int(parts[-1])
            player_name = ' '.join(parts[:-1])  # 移除年份，剩下的就是球員名字
        
        print(f"球員查詢 - 球員: '{player_name}', 年份: {year}")
        
        # 根據是否有年份來決定查詢類型
        if year:
            # 查詢特定年份數據
            stats_text, actual_name = get_player_season_stats(player_name, year)
            query_type = f"{year} 年數據"
        else:
            # 查詢生涯數據
            stats_text, actual_name = get_player_stats_text(player_name)
            query_type = "生涯數據"
        
        if stats_text is None:
            # 球員不存在或年份不存在
            send_reply_message(reply_token, [
                {'type': 'text', 'text': actual_name}  # actual_name 此時是錯誤訊息
            ])
            return
        
        # 發送統計資料
        send_reply_message(reply_token, [
            {'type': 'text', 'text': stats_text}
        ])
    
    elif user_message.lower() in ['help', '幫助', '說明']:
        help_text = """🏀 NBA 球員數據查詢 Bot

使用方法：

🔍 查詢生涯數據：
• !球員名字
• 例如：!LeBron James
• 例如：/Kobe Bryant

📅 查詢特定年份：
• !球員名字 年份
• 例如：!LeBron James 2012
• 例如：/Kobe Bryant 2006

👥 查詢球隊名單：
• !年份 球隊縮寫
• 例如：!2012 LAL
• 例如：/2016 GSW

功能：
📊 生涯統計數據
🎯 最佳賽季表現
📅 特定年份場均數據
👥 球隊完整名單
📈 詳細圖表分析

📱 查看完整圖表：
https://nba-alltime-search-charts.onrender.com/

輸入 'help' 查看此說明"""
        
        send_reply_message(reply_token, [
            {'type': 'text', 'text': help_text}
        ])
    
    else:
        # 一般回復
        reply_text = """請輸入指令來查詢NBA數據：

🏀 查詢生涯數據：
!LeBron James

📅 查詢特定年份：
!LeBron James 2012

👥 查詢球隊名單：
!2012 LAL

輸入 'help' 查看詳細說明"""
        send_reply_message(reply_token, [
            {'type': 'text', 'text': reply_text}
        ])

def keep_alive():
    """保持服務喚醒，避免 Render 免費版睡眠"""
    while True:
        try:
            # 每14分鐘 ping 一次健康檢查端點
            base_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
            requests.get(f'{base_url}/health', timeout=30)
            print("Keep alive ping sent")
        except Exception as e:
            print(f"Keep alive ping failed: {e}")
        time.sleep(14 * 60)  # 14分鐘

if __name__ == "__main__":
    print("NBA LINE Bot 啟動中...")
    print("平台: Render")
    print("請確保已在 Render 環境變數中設定 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET")
    
    # 檢查必要文件
    if not os.path.exists("Player Per Game.csv"):
        print("⚠️  警告: 找不到 Player Per Game.csv 文件")
    
    # 檢查環境變數設定
    if LINE_CHANNEL_ACCESS_TOKEN == 'YOUR_CHANNEL_ACCESS_TOKEN':
        print("⚠️  警告: 請在 Render 中設定 LINE_CHANNEL_ACCESS_TOKEN 環境變數")
    if LINE_CHANNEL_SECRET == 'YOUR_CHANNEL_SECRET':
        print("⚠️  警告: 請在 Render 中設定 LINE_CHANNEL_SECRET 環境變數")
    
    # 啟動 keep-alive 線程 (防止 Render 免費版睡眠)
    if os.environ.get('RENDER_EXTERNAL_URL'):
        threading.Thread(target=keep_alive, daemon=True).start()
        print("Keep-alive 線程已啟動")
    
    try:
        # 從環境變數獲取端口，Render 會自動設定
        port = int(os.environ.get('PORT', 5000))
        print(f"在端口 {port} 啟動服務器")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"啟動失敗: {e}")
        print("請檢查所有設定是否正確")
