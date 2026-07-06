import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import os

# 부우 게시판 미네랄 창고 주소
base_url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage&page="
save_give = "ygosu_prev_rank.csv" 
save_recv = "ygosu_prev_rank_receive.csv" 

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("🚀 부우 게시판 데이터 수집 시작...")
give_data = {}
recv_data = {}
page = 1

# 1. 무한 루프지만 데이터 없으면 바로 종료
while True:
    try:
        res = requests.get(f"{base_url}{page}", headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all('tr')
        
        found_any = False
        for row in rows:
            text = " ".join(row.stripped_strings)
            # 기부(+) 및 수령(-) 패턴
            g_match = re.search(r'\d{2}-\d{2}-\d{2}\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)', text)
            r_match = re.search(r'\d{2}-\d{2}-\d{2}\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)', text)
            
            if g_match:
                found_any = True
                nick = g_match.group(1).split()[0]
                val = int(g_match.group(2).replace(',', ''))
                if nick not in ["운영자", "시스템"]: give_data[nick] = give_data.get(nick, 0) + val
            
            if r_match:
                found_any = True
                mid = r_match.group(1)
                if "에게" in mid:
                    nick = mid.split('에게')[0].split()[-1]
                    val = int(r_match.group(2).replace(',', ''))
                    if nick not in ["운영자", "시스템"]: recv_data[nick] = recv_data.get(nick, 0) + val
        
        if not found_any: break
        page += 1
        time.sleep(0.1)
    except: break

# 2. 데이터 처리 함수
def get_top50(data_dict, save_file):
    df = pd.DataFrame(list(data_dict.items()), columns=['Nickname', 'Mineral'])
    df = df.sort_values(by='Mineral', ascending=False).head(50).reset_index(drop=True)
    
    # 순위 변동 계산용 저장
    if os.path.exists(save_file):
        prev = pd.read_csv(save_file)
        df['PrevRank'] = df['Nickname'].map(dict(zip(prev['Nickname'], prev.index + 1)))
    else:
        df['PrevRank'] = None
    
    df['Rank'] = df.index + 1
    df.to_csv(save_file, index=False)
    return df

df_give = get_top50(give_data, save_give)
df_recv = get_top50(recv_data, save_recv)

# 3. HTML 생성 (링크 없는 깔끔한 버전)
def make_html(df, title, color):
    rows_html = ""
    for _, row in df.iterrows():
        change = "-"
        if pd.notna(row['PrevRank']):
            diff = int(row['PrevRank'] - row['Rank'])
            if diff > 0: change = f"▲{diff}"
            elif diff < 0: change = f"▼{abs(diff)}"
        else: change = "NEW"
        
        rows_html += f"<tr><td>{row['Rank']} ({change})</td><td><b>{row['Nickname']}</b></td><td>{format(row['Mineral'], ',')}</td></tr>"
    
    return f"""
    <div style="background:#fff; border:1px solid #ddd; padding:20px; border-radius:10px;">
        <h3 style="color:{color}">{title}</h3>
        <table width="100%" style="text-align:center;">
            {rows_html}
        </table>
    </div>
    """

with open("index.html", "w", encoding="utf-8") as f:
    f.write(f"<html><body>{make_html(df_give, '기부왕 Top 50', 'red')}{make_html(df_recv, '일퀘왕 Top 50', 'blue')}</body></html>")

print("✅ 성공! index.html이 생성되었습니다.")
