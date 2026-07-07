import requests
from bs4 import BeautifulSoup
import re
import datetime
import os

# 💡 여기에 아까 복사해둔 수파베이스 URL과 API KEY를 넣으세요! 
SUPABASE_URL = "https://vhxiziitdsegofwdwpqa.supabase.co/rest/v1/"
SUPABASE_KEY = "sb_publishable_2W1zP9xviLmOdzkg2DkQgQ_nVIsIe7r"

base_url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage&page="
headers = {"User-Agent": "Mozilla/5.0"}

# 오늘 날짜 계산 (예: 2026-07-07)
now = datetime.datetime.now()
today_str = now.strftime("%Y-%m-%d")
ygosu_date_prefix = now.strftime("%y-%m-%d") # 와이고수 표기 (26-07-07)

print(f"[{today_str}] 데이터 수집 및 DB 저장 시작...")

give_data = {}
recv_data = {}
member_ids = {}

pattern_give = r'(\d{2}-\d{2}-\d{2})\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
pattern_recv = r'(\d{2}-\d{2}-\d{2})\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'

for page in range(1, 15): # 속도를 위해 15페이지만 스캔
    try:
        res = requests.get(f"{base_url}{page}", headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all('tr')
        if len(rows) < 2: break

        for row in rows:
            text = " ".join(row.stripped_strings)
            
            # 1. 기부 데이터 (+)
            m_give = re.search(pattern_give, text)
            if m_give:
                date_val, mid_text, min_val = m_give.groups()
                if date_val == ygosu_date_prefix: # 오늘 날짜만 DB에 기록
                    sys_kws = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]
                    if not any(kw in mid_text for kw in sys_kws):
                        nick = mid_text.split()[0]
                        if nick not in ["운영자", "시스템", ""]:
                            if nick == "XOXA": nick = "초우코송이" # XOXA 변환 로직
                            give_data[nick] = give_data.get(nick, 0) + int(min_val.replace(',', ''))
                            for a_tag in row.find_all('a'):
                                if nick in a_tag.get_text() or "XOXA" in a_tag.get_text():
                                    m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(a_tag))
                                    if m: member_ids[nick] = m.group(1) or m.group(2)
                            if nick == "초우코송이": member_ids[nick] = "705225"

            # 2. 일퀘 데이터 (-)
            m_recv = re.search(pattern_recv, text)
            if m_recv:
                date_val, mid_text, min_val = m_recv.groups()
                if date_val == ygosu_date_prefix:
                    if "에게" in mid_text:
                        nick = mid_text.split('에게')[0].split()[-1]
                        if nick not in ["운영자", "시스템", ""]:
                            if nick == "XOXA": nick = "초우코송이"
                            recv_data[nick] = recv_data.get(nick, 0) + int(min_val.replace(',', ''))
                            for a_tag in row.find_all(['a', 'span']):
                                if nick in a_tag.get_text() or "XOXA" in a_tag.get_text():
                                    m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(a_tag))
                                    if m: member_ids[nick] = m.group(1) or m.group(2)
                            if nick == "초우코송이": member_ids[nick] = "705225"
    except Exception as e:
        print(f"에러: {e}")
        break

# DB에 올릴 데이터로 정리
all_nicks = set(give_data.keys()).union(set(recv_data.keys()))
insert_payload = []
for nick in all_nicks:
    insert_payload.append({
        "record_date": today_str,
        "nickname": nick,
        "member_id": member_ids.get(nick, ""),
        "give_mineral": give_data.get(nick, 0),
        "recv_mineral": recv_data.get(nick, 0)
    })

# 수파베이스 DB에 데이터 전송
if insert_payload:
    db_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # 중복 방지를 위해 오늘 날짜 기록을 싹 지우고 다시 최신본으로 기록함
    delete_url = f"{SUPABASE_URL}/rest/v1/ygosu_rank?record_date=eq.{today_str}"
    requests.delete(delete_url, headers=db_headers)
    
    insert_url = f"{SUPABASE_URL}/rest/v1/ygosu_rank"
    res = requests.post(insert_url, headers=db_headers, json=insert_payload)
    
    if res.status_code in [200, 201]:
        print(f"✅ 성공! 오늘자 {len(insert_payload)}명의 데이터가 DB에 저장되었습니다!")
    else:
        print(f"❌ DB 에러: {res.text}")
else:
    print("오늘은 아직 기부/일퀘 기록이 없습니다.")
