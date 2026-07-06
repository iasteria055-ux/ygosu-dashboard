import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import os
import urllib.parse

# ★ 부우 게시판으로 완벽하게 수정됨!
base_url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage&page="
save_give = "ygosu_prev_rank.csv" 
save_recv = "ygosu_prev_rank_receive.csv" 

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("🔥 부우 게시판 페이지 자동 탐색 및 데이터 수집 시작...")
give_list = []
recv_list = []
page = 1
prev_html = "" 

while True:
    url = f"{base_url}{page}"
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        res.encoding = 'utf-8'
        
        if res.text == prev_html: break
        prev_html = res.text
        
        soup = BeautifulSoup(res.text, 'html.parser')
        page_has_data = False
        
        for row in soup.find_all('tr'):
            row_text = " ".join(row.stripped_strings)
            match_give = re.search(r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)', row_text)
            match_recv = re.search(r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)', row_text)
            
            if match_give or match_recv: page_has_data = True
            
            if match_give:
                mid_text = match_give.group(1).strip()
                mineral_str = match_give.group(2)
                sys_kws = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]
                if any(kw in mid_text for kw in sys_kws): continue
                parts = mid_text.split()
                if not parts: continue
                nickname = parts[0] 
                if nickname in ["운영자", "시스템", ""]: continue
                
                member_id = ""
                for a_tag in row.find_all('a'):
                    if nickname in a_tag.get_text():
                        m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(a_tag))
                        if m:
                            member_id = m.group(1) if m.group(1) else m.group(2)
                            break
                giving_num = int(mineral_str.replace(',', ''))
                give_list.append({'Nickname': nickname, 'Mineral': giving_num, 'MemberID': member_id})
                
            elif match_recv:
                mid_text = match_recv.group(1).strip()
                mineral_str = match_recv.group(2)
                if "에게" not in mid_text: continue
                parts = mid_text.split('에게')[0].split()
                if not parts: continue
                nickname = parts[-1] 
                if nickname in ["운영자", "시스템", ""]: continue
                
                member_id = ""
                for tag in row.find_all(['a', 'span', 'td']):
                    if nickname in tag.get_text():
                        m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(tag))
                        if m:
                            member_id = m.group(1) if m.group(1) else m.group(2)
                            break
                if not member_id:
                    for tag in soup.find_all(['a', 'span']):
                        if tag.get_text().strip() == nickname:
                            m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(tag))
                            if m:
                                member_id = m.group(1) if m.group(1) else m.group(2)
                                break
                recving_num = int(mineral_str.replace(',', ''))
                recv_list.append({'Nickname': nickname, 'Mineral': recving_num, 'MemberID': member_id})
                
        if not page_has_data: break
        page += 1
        time.sleep(0.1)
    except: break

def get_valid_id(series):
    for val in series:
        if val: return val
    return ""

def process_data(data_list, save_file):
    df = pd.DataFrame(data_list)
    if df.empty: return pd.DataFrame()
    ranking_df = df.groupby('Nickname', as_index=False).agg({'Mineral': 'sum', 'MemberID': get_valid_id})
    ranking_df = ranking_df.sort_values(by='Mineral', ascending=False).reset_index(drop=True).head(50)
    
    for idx, row in ranking_df.iterrows():
        if not row['MemberID']:
            try:
                s_res = requests.get(f"https://ygosu.com/all_search/?keyword={urllib.parse.quote(row['Nickname'])}&search_field=w", headers=headers)
                m = re.search(r"win_profile\(['\"]([0-9]{4,8})['\"]\)|member=([0-9]{4,8})", s_res.text)
                if m: ranking_df.at[idx, 'MemberID'] = m.group(1) if m.group(1) else m.group(2)
            except: pass
            
    prev_ranks = {}
    is_first = not os.path.exists(save_file)
    if not is_first:
        prev_df = pd.read_csv(save_file)
        for _, r in prev_df.iterrows(): prev_ranks[r['Nickname']] = r['Rank']
        
    current_save = []
    for i, r in ranking_df.iterrows(): current_save.append({'Nickname': r['Nickname'], 'Rank': i+1})
    pd.DataFrame(current_save).to_csv(save_file, index=False)
    
    ranking_df['PrevRank'] = ranking_df['Nickname'].map(prev_ranks)
    ranking_df['IsFirst'] = is_first
    return ranking_df

df_give = process_data(give_list, save_give)
df_recv = process_data(recv_list, save_recv)

def make_rows(df, type_name):
    html = ""
    if df.empty: return html
    for idx, row in df.iterrows():
        rank = idx + 1
        nick = row['Nickname']
        mid = row['MemberID']
        min_str = format(row['Mineral'], ',')
        
        change_html = "<span class='chg none'>-</span>"
        if not row['IsFirst'] and pd.notna(row['PrevRank']):
            diff = int(row['PrevRank'] - rank)
            if diff > 0: change_html = f"<span class='chg up'>▲ {diff}</span>"
            elif diff < 0: change_html = f"<span class='chg down'>▼ {abs(diff)}</span>"
        elif not row['IsFirst']:
            change_html = "<span class='chg new'>NEW</span>"
                
        link = f"https://ygosu.com/minilog/?member={mid}&m2=profile" if mid else f"https://ygosu.com/all_search/?keyword={urllib.parse.quote(nick)}&search_field=w"
        nick_disp = f"<a href='{link}' target='_blank'>{nick}</a>"
            
        row_class = "rank-row"
        if rank == 1: row_class += " gold"
        elif rank == 2: row_class += " silver"
        elif rank == 3: row_class += " bronze"
        
        rank_icon = f"🥇 1" if rank == 1 else f"🥈 2" if rank == 2 else f"🥉 3" if rank == 3 else f"{rank}"
        color_class = "txt-red" if type_name == "give" else "txt-blue"
        prefix = "+" if type_name == "give" else ""
        
        html += f"""
        <div class="{row_class}">
            <div class="col-rank">{rank_icon}<br>{change_html}</div>
            <div class="col-nick">{nick_disp}</div>
            <div class="col-min {color_class}">{prefix} {min_str}</div>
        </div>
        """
    return html

html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>부우 게시판 미네랄 통합 대시보드</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
        body {{ background: linear-gradient(135deg, #1e293b, #0f172a); color: #fff; font-family: 'Noto Sans KR', sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; }}
        .dashboard {{ width: 100%; max-width: 700px; background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1); padding: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 32px; text-shadow: 0 0 10px rgba(255,255,255,0.5); }}
        .header p {{ color: #94a3b8; font-size: 14px; margin-top: 5px; }}
        .bgm-box {{ background: rgba(0,0,0,0.3); border-radius: 15px; padding: 15px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.05); }}
        .bgm-title {{ font-size: 12px; color: #cbd5e1; margin-bottom: 10px; font-weight: bold; }}
        .tabs {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        .tab-btn {{ flex: 1; padding: 15px; text-align: center; border-radius: 12px; cursor: pointer; font-weight: bold; font-size: 16px; transition: all 0.3s ease; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #94a3b8; }}
        .tab-btn.active {{ background: linear-gradient(45deg, #3b82f6, #8b5cf6); color: #fff; box-shadow: 0 5px 15px rgba(59, 130, 246, 0.4); border-color: transparent; }}
        .tab-content {{ display: none; animation: fadeIn 0.5s ease; }}
        .tab-content.active {{ display: block; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .list-header {{ display: flex; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; font-weight: bold; color: #94a3b8; font-size: 14px; margin-bottom: 10px; text-align: center; }}
        .col-rank {{ width: 20%; }} .col-nick {{ width: 45%; }} .col-min {{ width: 35%; }}
        .rank-list {{ max-height: 500px; overflow-y: auto; padding-right: 5px; }}
        .rank-list::-webkit-scrollbar {{ width: 6px; }}
        .rank-list::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.2); border-radius: 3px; }}
        .rank-row {{ display: flex; align-items: center; padding: 12px 15px; margin-bottom: 8px; background: rgba(255,255,255,0.03); border-radius: 10px; text-align: center; transition: transform 0.2s, background 0.2s; border: 1px solid transparent; }}
        .rank-row:hover {{ transform: scale(1.02); background: rgba(255,255,255,0.08); }}
        .rank-row.gold {{ border-color: rgba(250, 204, 21, 0.5); background: rgba(250, 204, 21, 0.1); box-shadow: 0 0 15px rgba(250, 204, 21, 0.2); }}
        .rank-row.silver {{ border-color: rgba(148, 163, 184, 0.5); background: rgba(148, 163, 184, 0.1); }}
        .rank-row.bronze {{ border-color: rgba(180, 83, 9, 0.5); background: rgba(180, 83, 9, 0.1); }}
        .col-nick a {{ color: #e2e8f0; text-decoration: none; font-weight: 700; transition: color 0.2s; }}
        .col-nick a:hover {{ color: #38bdf8; text-shadow: 0 0 8px rgba(56,189,248,0.5); }}
        .txt-red {{ color: #f87171; font-weight: 900; letter-spacing: 1px; }}
        .txt-blue {{ color: #38bdf8; font-weight: 900; letter-spacing: 1px; }}
        .chg {{ font-size: 11px; padding: 2px 4px; border-radius: 4px; font-weight: bold; }}
        .chg.up {{ color: #ef4444; }} .chg.down {{ color: #3b82f6; }} .chg.none {{ color: #64748b; }} .chg.new {{ background: #f59e0b; color: #fff; font-size: 10px; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #64748b; line-height: 1.6; }}
    </style>
</head>
<body>
<div class="dashboard">
    <div class="header">
        <h1>✨ 부우 게시판 통합 랭킹 ✨</h1>
        <p>기부왕 및 일퀘왕 통합 명예의 전당 (Top 50)</p>
    </div>
    <div class="bgm-box">
        <div class="bgm-title">🎵 BGM</div>
        <iframe width="100%" height="200" src="" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen style="border-radius: 8px;"></iframe>
    </div>
    <div class="tabs">
        <div class="tab-btn active" onclick="switchTab('give')">👑 기부왕 (보낸 사람)</div>
        <div class="tab-btn" onclick="switchTab('recv')">💎 일퀘왕 (받은 사람)</div>
    </div>
    <div id="tab-give" class="tab-content active">
        <div class="list-header">
            <div class="col-rank">순위</div><div class="col-nick">닉네임</div><div class="col-min">총 기부 미네랄</div>
        </div>
        <div class="rank-list">{make_rows(df_give, 'give')}</div>
    </div>
    <div id="tab-recv" class="tab-content">
        <div class="list-header">
            <div class="col-rank">순위</div><div class="col-nick">닉네임</div><div class="col-min">총 받은 미네랄</div>
        </div>
        <div class="rank-list">{make_rows(df_recv, 'recv')}</div>
    </div>
    <div class="footer">
        * 여러 번 나누어 거래하신 분들의 내역은 자동 합산된 결과입니다.<br>
        * 순위 변동은 이전 집계 시점과 비교한 결과이며 누적 데이터 기준 상위 50명만 표시됩니다.
    </div>
</div>
<script>
    function switchTab(tabId) {{
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        event.currentTarget.classList.add('active');
        document.getElementById('tab-' + tabId).classList.add('active');
    }}
</script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
print("✅ 대시보드 index.html 생성 완료!")
