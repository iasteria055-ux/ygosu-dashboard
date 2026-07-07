import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import os
import urllib.parse

base_url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage&page="
max_pages = 30 # 수집 속도를 위해 30페이지 제한
save_give = "ygosu_prev_rank.csv"
save_recv = "ygosu_prev_rank_receive.csv"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

give_list = []
recv_list = []
print(f"🎵 리듬게임 UI 스타일 데이터 수집 시작...\n")

pattern_give = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
pattern_recv = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'

for page in range(1, max_pages + 1):
    url = f"{base_url}{page}"
    try:
        res = requests.get(url, headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all('tr')
        
        if not rows: break

        for row in rows:
            row_text = " ".join(row.stripped_strings)
            m_give = re.search(pattern_give, row_text)
            m_recv = re.search(pattern_recv, row_text)

            # 1. 기부 데이터 (+)
            if m_give:
                mid_text = m_give.group(1).strip()
                min_str = m_give.group(2)
                sys_kws = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]
                if not any(kw in mid_text for kw in sys_kws):
                    parts = mid_text.split()
                    if parts:
                        nick = parts[0]
                        if nick not in ["운영자", "시스템", ""]:
                            member_id = ""
                            for a_tag in row.find_all('a'):
                                if nick in a_tag.get_text():
                                    m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(a_tag))
                                    if m:
                                        member_id = m.group(1) if m.group(1) else m.group(2)
                                        break
                            
                            # [핵심] XOXA -> 초우코송이 자동 변환
                            if nick == "XOXA":
                                nick = "초우코송이"
                                member_id = "705225"
                                
                            give_list.append({'Nickname': nick, 'Mineral': int(min_str.replace(',', '')), 'MemberID': member_id})

            # 2. 일퀘 데이터 (-)
            if m_recv:
                mid_text = m_recv.group(1).strip()
                min_str = m_recv.group(2)
                if "에게" in mid_text:
                    parts = mid_text.split('에게')[0].split()
                    if parts:
                        nick = parts[-1]
                        if nick not in ["운영자", "시스템", ""]:
                            member_id = ""
                            for tag in row.find_all(['a', 'span']):
                                if nick in tag.get_text():
                                    m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(tag))
                                    if m:
                                        member_id = m.group(1) if m.group(1) else m.group(2)
                                        break
                            
                            # [핵심] XOXA -> 초우코송이 자동 변환
                            if nick == "XOXA":
                                nick = "초우코송이"
                                member_id = "705225"

                            recv_list.append({'Nickname': nick, 'Mineral': int(min_str.replace(',', '')), 'MemberID': member_id})
                            
    except Exception as e:
        break

# 데이터 처리
def process_data(d_list, s_file):
    if not d_list: return pd.DataFrame(), True
    df = pd.DataFrame(d_list)
    def get_valid_id(series):
        for val in series:
            if val: return val
        return ""
    
    rdf = df.groupby('Nickname', as_index=False).agg({'Mineral': 'sum', 'MemberID': get_valid_id})
    rdf = rdf.sort_values(by='Mineral', ascending=False).reset_index(drop=True).head(50)
    
    prev_ranks = {}
    is_first = not os.path.exists(s_file)
    if not is_first:
        try:
            prev_df = pd.read_csv(s_file)
            for idx, r in prev_df.iterrows(): prev_ranks[r['Nickname']] = r['Rank']
        except: pass
        
    current_save = []
    for idx, row in rdf.iterrows(): current_save.append({'Nickname': row['Nickname'], 'Rank': idx + 1})
    pd.DataFrame(current_save).to_csv(s_file, index=False)
    
    rdf['PrevRank'] = rdf['Nickname'].map(prev_ranks)
    return rdf, is_first

df_give, first_give = process_data(give_list, save_give)
df_recv, first_recv = process_data(recv_list, save_recv)

# 리듬게임 UI 스타일 HTML 생성
def make_table_html(df, is_first, type_name):
    html = ""
    for idx, row in df.iterrows():
        rank = idx + 1
        nick = row['Nickname']
        mid = row['MemberID']
        mineral = format(row['Mineral'], ',')
        
        chg = "<span class='chg none'>-</span>"
        if not is_first and pd.notna(row['PrevRank']):
            diff = int(row['PrevRank'] - rank)
            if diff > 0: chg = f"<span class='chg up'>▲{diff}</span>"
            elif diff < 0: chg = f"<span class='chg down'>▼{abs(diff)}</span>"
        elif not is_first:
            chg = "<span class='chg new'>NEW</span>"

        link = f"https://ygosu.com/minilog/?member={mid}&m2=profile" if mid else f"https://ygosu.com/all_search/?keyword={urllib.parse.quote(nick)}&search_field=w"
        
        r_class = "rank-num"
        if rank == 1: r_class += " gold"
        elif rank == 2: r_class += " silver"
        elif rank == 3: r_class += " bronze"
        
        color_class = "min-give" if type_name == "give" else "min-recv"
        prefix = "+" if type_name == "give" else "-"
        
        html += f"""
        <div class="dj-row">
            <div class="col-r"><span class="{r_class}">{rank:02d}</span> {chg}</div>
            <div class="col-n"><a href="{link}" target="_blank">{nick}</a></div>
            <div class="col-m {color_class}">{prefix} {mineral}</div>
        </div>
        """
    return html

html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>부우 게시판 명예의 전당</title>
    <style>
        /* 몬세라트 영문 폰트(기울임, 굵게)와 노토산스 한글 폰트 적용 */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,800;1,900&family=Noto+Sans+KR:wght@500;700;900&display=swap');
        
        body {{
            /* 배경: 그리드(모눈종이) 패턴 */
            background-color: #f4f2f7;
            background-image: linear-gradient(#e5e0f0 1px, transparent 1px), linear-gradient(90deg, #e5e0f0 1px, transparent 1px);
            background-size: 20px 20px;
            font-family: 'Noto Sans KR', sans-serif;
            color: #2b1a5a;
            margin: 0; padding: 40px 20px; display: flex; justify-content: center;
        }}
        
        .dashboard-container {{
            max-width: 1100px; width: 100%;
            background: #ffffff;
            border: 8px solid #2b1a5a; /* 딥 퍼플 테두리 */
            box-shadow: 20px 20px 0px rgba(43, 26, 90, 0.1);
            position: relative; padding: 40px; box-sizing: border-box;
        }}
        
        /* UI 장식 요소 */
        .dashboard-container::before {{
            content: '+ X O';
            position: absolute; top: -35px; left: 10px; font-weight: 900; 
            font-family: 'Montserrat'; font-size: 24px; color: #2b1a5a; letter-spacing: 5px;
        }}
        .deco-line {{
            width: 100%; height: 12px; margin-bottom: 20px;
            background: repeating-linear-gradient(45deg, #2b1a5a, #2b1a5a 10px, transparent 10px, transparent 20px);
        }}

        .header {{ text-align: center; margin-bottom: 40px; position: relative; z-index: 2; }}
        .header .sub {{
            font-family: 'Montserrat', sans-serif; font-style: italic; font-weight: 900; 
            font-size: 24px; color: #ff3a3a; text-transform: uppercase; letter-spacing: 3px; margin: 0;
        }}
        .header h1 {{
            font-family: 'Montserrat', sans-serif; font-style: italic; font-weight: 900; 
            font-size: 56px; color: #2b1a5a; margin: -10px 0 10px 0; text-transform: uppercase; 
            letter-spacing: -2px; text-shadow: 5px 5px 0px #ffc107;
        }}
        .header p {{ font-size: 16px; font-weight: 700; color: #666; margin: 0; }}

        .board-wrapper {{ display: flex; gap: 30px; flex-wrap: wrap; }}
        
        .panel {{
            flex: 1; min-width: 350px;
            border: 4px solid #2b1a5a; position: relative; background: #fff;
        }}
        
        .panel-title {{
            background: #2b1a5a; color: #fff; font-family: 'Montserrat', 'Noto Sans KR', sans-serif;
            font-style: italic; font-weight: 900; font-size: 28px; padding: 15px 20px;
            text-transform: uppercase; letter-spacing: 1px; display: flex; justify-content: space-between;
        }}
        /* 패널 타이틀 아래 쨍한 컬러 포인트 */
        .panel-title.give {{ border-bottom: 6px solid #ff4d00; }}
        .panel-title.recv {{ border-bottom: 6px solid #00a8ff; }}
        .panel-title span {{ font-size: 16px; color: rgba(255,255,255,0.5); }}

        .list-box {{ max-height: 550px; overflow-y: auto; padding: 10px 15px; }}
        .list-box::-webkit-scrollbar {{ width: 8px; }}
        .list-box::-webkit-scrollbar-thumb {{ background: #2b1a5a; border-radius: 0; }}

        .dj-row {{
            display: flex; align-items: center; padding: 14px 10px; margin-bottom: 6px;
            border-bottom: 2px solid #f4f2f7; transition: all 0.2s; font-weight: 700;
        }}
        .dj-row:hover {{
            background: #f4f2f7; transform: translateX(8px); border-left: 6px solid #ffc107;
        }}

        .col-r {{ width: 25%; font-size: 16px; font-family: 'Montserrat', sans-serif; font-style: italic; font-weight: 900; color: #999; }}
        .col-n {{ width: 40%; font-size: 16px; }}
        .col-m {{ width: 35%; text-align: right; font-weight: 900; font-size: 18px; font-family: 'Montserrat', sans-serif; }}

        .rank-num {{ display: inline-block; width: 28px; }}
        .rank-num.gold {{ color: #ffc107; font-size: 24px; text-shadow: 2px 2px 0px #2b1a5a; }}
        .rank-num.silver {{ color: #a0aeb5; font-size: 22px; text-shadow: 1px 1px 0px #2b1a5a; }}
        .rank-num.bronze {{ color: #cd7f32; font-size: 20px; }}

        .min-give {{ color: #ff4d00; }}
        .min-recv {{ color: #00a8ff; }}

        .chg {{ font-size: 12px; margin-left: 5px; font-weight: 900; font-style: normal; font-family: 'Noto Sans KR'; }}
        .chg.up {{ color: #ff4d00; }} .chg.down {{ color: #00a8ff; }} .chg.none {{ color: #ccc; }}
        .chg.new {{ color: #2b1a5a; background: #ffc107; padding: 2px 6px; font-size: 11px; }}

        .col-n a {{ color: #2b1a5a; text-decoration: none; transition: color 0.2s; }}
        .col-n a:hover {{ color: #ff4d00; }}

        .bgm-area {{ text-align: center; margin-top: 30px; border: 4px solid #2b1a5a; padding: 5px; background: #fff; }}
    </style>
</head>
<body>

<div class="dashboard-container">
    <div class="deco-line"></div>
    
    <div class="header">
        <p class="sub">V EXTENSION / BOO BOARD</p>
        <h1>RANKING DATA</h1>
        <p>기부왕 및 일퀘왕 통합 명예의 전당 (Top 50)</p>
    </div>

    <div class="board-wrapper">
        <div class="panel">
            <div class="panel-title give">GIVE <span>[+]</span></div>
            <div class="list-box">
                {make_table_html(df_give, first_give, 'give')}
            </div>
        </div>

        <div class="panel">
            <div class="panel-title recv">TAKE <span>[-]</span></div>
            <div class="list-box">
                {make_table_html(df_recv, first_recv, 'recv')}
            </div>
        </div>
    </div>
    
    <div class="bgm-area">
        <iframe width="100%" height="100" src="" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>
    </div>
</div>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
print("✅ 리듬게임(DJMAX) 감성 대시보드 갱신 완료!")
