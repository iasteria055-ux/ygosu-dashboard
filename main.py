import requests
from bs4 import BeautifulSoup
import re
import datetime

# 💡 여기에 수파베이스 URL과 KEY를 다시 넣어주세요!
SUPABASE_URL = "https://vhxiziitdsegofwdwpqa.supabase.co/rest/v1/"
SUPABASE_KEY = "sb_publishable_2W1zP9xviLmOdzkg2DkQgQ_nVIsIe7r"

base_url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage&page="
headers = {"User-Agent": "Mozilla/5.0"}

print("📚 전체 108페이지 과거 데이터 수집 시작...")

db_data = {}
member_ids = {}

pattern_give = r'(\d{2}-\d{2}-\d{2})\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
pattern_recv = r'(\d{2}-\d{2}-\d{2})\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'

def to_full_date(short_date): return "20" + short_date

for page in range(1, 109): # 1페이지부터 108페이지까지 전부 스캔!
    try:
        res = requests.get(f"{base_url}{page}", headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all('tr')
        if len(rows) < 2: break

        for row in rows:
            text = " ".join(row.stripped_strings)
            
            # 기부
            m_give = re.search(pattern_give, text)
            if m_give:
                d_val, mid_text, min_val = m_give.groups()
                full_date = to_full_date(d_val)
                if not any(kw in mid_text for kw in ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]):
                    nick = mid_text.split()[0]
                    if nick not in ["운영자", "시스템", ""]:
                        if nick == "XOXA": nick = "초우코송이"
                        key = f"{full_date}_{nick}"
                        if key not in db_data: db_data[key] = {"date": full_date, "nick": nick, "give": 0, "recv": 0}
                        db_data[key]["give"] += int(min_val.replace(',', ''))
                        
                        for a in row.find_all('a'):
                            m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(a))
                            if m: member_ids[nick] = m.group(1) or m.group(2)

            # 일퀘
            m_recv = re.search(pattern_recv, text)
            if m_recv:
                d_val, mid_text, min_val = m_recv.groups()
                full_date = to_full_date(d_val)
                if "에게" in mid_text:
                    nick = mid_text.split('에게')[0].split()[-1]
                    if nick not in ["운영자", "시스템", ""]:
                        if nick == "XOXA": nick = "초우코송이"
                        key = f"{full_date}_{nick}"
                        if key not in db_data: db_data[key] = {"date": full_date, "nick": nick, "give": 0, "recv": 0}
                        db_data[key]["recv"] += int(min_val.replace(',', ''))
                        
                        for a in row.find_all(['a', 'span']):
                            m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(a))
                            if m: member_ids[nick] = m.group(1) or m.group(2)
                            
    except Exception as e:
        print(f"에러: {e}")
        break

if "초우코송이" in member_ids: member_ids["초우코송이"] = "705225"

# DB 전송용 데이터 포맷팅
insert_payload = []
for k, v in db_data.items():
    insert_payload.append({
        "record_date": v["date"], "nickname": v["nick"],
        "member_id": member_ids.get(v["nick"], ""),
        "give_mineral": v["give"], "recv_mineral": v["recv"]
    })

db_headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

# 기존 데이터 싹 지우고 전체 동기화 (108페이지 분량)
requests.delete(f"{SUPABASE_URL}/rest/v1/ygosu_rank?id=gt.0", headers=db_headers)

for i in range(0, len(insert_payload), 500):
    chunk = insert_payload[i:i+500]
    res = requests.post(f"{SUPABASE_URL}/rest/v1/ygosu_rank", headers=db_headers, json=chunk)

print(f"✅ 성공! 108페이지 전체({len(insert_payload)}건) 데이터 DB 갱신 완료!")
