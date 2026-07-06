import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import os
import urllib.parse

base_url = "https://ygosu.com/board/pan_bora/?mode=mineral_storage&page="
save_give = "ygosu_prev_rank.csv" 
save_recv = "ygosu_prev_rank_receive.csv" 
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

give_list, recv_list = [], []

# ★ 무한 루프 대신 1~30페이지까지만 딱 돌려서 속도 확보!
print("🚀 수집 시작 (1~30페이지 스캔)")
for page in range(1, 31):
    try:
        res = requests.get(f"{base_url}{page}", headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all('tr')
        if not rows: break 
        
        for row in rows:
            text = " ".join(row.stripped_strings)
            g_match = re.search(r'\d{2}-\d{2}-\d{2}\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)', text)
            r_match = re.search(r'\d{2}-\d{2}-\d{2}\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)', text)
            
            if g_match:
                nick = g_match.group(1).split()[0]
                if nick not in ["운영자", "시스템"]:
                    give_list.append({'Nickname': nick, 'Mineral': int(g_match.group(2).replace(',', '')), 'MemberID': ''})
            if r_match:
                mid = r_match.group(1)
                if "에게" in mid:
                    nick = mid.split('에게')[0].split()[-1]
                    if nick not in ["운영자", "시스템"]:
                        recv_list.append({'Nickname': nick, 'Mineral': int(r_match.group(2).replace(',', '')), 'MemberID': ''})
    except: break
    time.sleep(0.1)

def get_valid_id(series): return next((x for x in series if x), "")

def process_data(data_list, save_file):
    if not data_list: return pd.DataFrame()
    df = pd.DataFrame(data_list)
    ranking_df = df.groupby('Nickname', as_index=False).agg({'Mineral': 'sum', 'MemberID': get_valid_id})
    ranking_df = ranking_df.sort_values(by='Mineral', ascending=False).head(50).reset_index(drop=True)
    
    # 랭킹 1~3위만 미니로그 번호 복구 (속도 위해 50명 전체 검색 자제)
    for idx, row in ranking_df.head(10).iterrows():
        try:
            s_res = requests.get(f"https://ygosu.com/all_search/?keyword={urllib.parse.quote(row['Nickname'])}&search_field=w", headers=headers)
            m = re.search(r"member=([0-9]{4,8})", s_res.text)
            if m: ranking_df.at[idx, 'MemberID'] = m.group(1)
        except: pass
            
    prev_ranks = {}
    is_first = not os.path.exists(save_file)
    if not is_first:
        prev_df = pd.read_csv(save_file)
        prev_ranks = dict(zip(prev_df['Nickname'], prev_df['Rank']))
        
    ranking_df['PrevRank'] = ranking_df['Nickname'].map(prev_ranks)
    ranking_df['IsFirst'] = is_first
    ranking_df.to_csv(save_file, index=False)
    return ranking_df

df_give = process_data(give_list, save_give)
df_recv = process_data(recv_list, save_recv)

# [HTML 생성 로직은 이전과 동일하므로 생략 - 이전 main.py의 make_rows, html_template 그대로 사용하세요]
# (코드 길이가 길어 핵심 로직 위주로 드렸습니다. 나머지 html 저장 부분은 이전 main.py 복사하세요)
