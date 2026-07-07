import requests
from bs4 import BeautifulSoup
import re
import datetime

# 💡 여기에 수파베이스 URL과 KEY를 넣어주세요!
SUPABASE_URL = "sb_publishable_2W1zP9xviLmOdzkg2DkQgQ_nVIsIe7r"
SUPABASE_KEY = "https://vhxiziitdsegofwdwpqa.supabase.co/rest/v1/"

base_url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage&page="
headers = {"User-Agent": "Mozilla/5.0"}

now = datetime.datetime.now()
today_str = now.strftime("%Y-%m-%d")
ygosu_today = now.strftime("%y-%m-%d")

print("📡 [프로필 연동 모드] 기존 DB 데이터를 기반으로 회원번호를 매칭합니다...")

# 1. 창고(DB)에 저장된 기존 닉네임-회원번호 장부 모두 불러오기 (일퀘왕 미니로그 구출 작전)
known_members = {}
try:
    db_headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    res_db = requests.get(f"{SUPABASE_URL}/rest/v1/ygosu_rank?select=nickname,member_id", headers=db_headers)
    if res_db.status_code == 200:
        for r in res_db.json():
            if r.get("member_id"): known_members[r["nickname"]] = r["member_id"]
except Exception as e:
    print(f"기존 DB 장부 로드 실패: {e}")

db_data = {}
member_ids = known_members.copy() # 기존에 알고 있는 번호들 기본 탑재

pattern_give = r'(\d{2}-\d{2}-\d{2})\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
pattern_recv = r'(\d{2}-\d{2}-\d{2})\s*\(.\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'

page = 1
keep_going = True

while keep_going:
    try:
        res = requests.get(f"{base_url}{page}", headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all('tr')
        if len(rows) < 2: break

        for row in rows:
            text = " ".join(row.stripped_strings)
            m_give = re.search(pattern_give, text)
            m_recv = re.search(pattern_recv, text)
            
            target_match = m_give or m_recv
            if target_match:
                d_val = target_match.group(1)
                if d_val != ygosu_today:
                    keep_going = False
                    break

            # 기부왕 (+)
            if m_give and d_val == ygosu_today:
                _, mid_text, min_val = m_give.groups()
                if not any(kw in mid_text for kw in ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]):
                    nick = mid_text.split()[0]
                    if nick not in ["운영자", "시스템", ""]:
                        if nick == "XOXA": nick = "초우코송이"
                        if nick not in db_data: db_data[nick] = {"give": 0, "recv": 0}
                        db_data[nick]["give"] += int(min_val.replace(',', ''))
                        
                        for a in row.find_all('a'):
                            m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(a))
                            if m: member_ids[nick] = m.group(1) or m.group(2)

            # 일퀘왕 (-)
            if m_recv and d_val == ygosu_today:
                _, mid_text, min_val = m_recv.groups()
                if "에게" in mid_text:
                    nick = mid_text.split('에게')[0].split()[-1]
                    if nick not in ["운영자", "시스템", ""]:
                        if nick == "XOXA": nick = "초우코송이"
                        if nick not in db_data: db_data[nick] = {"give": 0, "recv": 0}
                        db_data[nick]["recv"] += int(min_val.replace(',', ''))
                        
                        # 혹시라도 로그에 링크가 있다면 수집
                        for a in row.find_all(['a', 'span']):
                            m = re.search(r"['\"]([0-9]{4,8})['\"]|member=([0-9]{4,8})", str(a))
                            if m: member_ids[nick] = m.group(1) or m.group(2)
                            
        page += 1
        if page > 50: break
    except:
        break

member_ids["초우코송이"] = "705225"

insert_payload = []
for nick, vals in db_data.items():
    insert_payload.append({
        "record_date": today_str,
        "nickname": nick,
        "member_id": member_ids.get(nick, ""), # 창고 기억력 덕분에 일퀘왕 번호도 장착 완료!
        "give_mineral": vals["give"],
        "recv_mineral": vals["recv"]
    })

if insert_payload:
    db_headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    requests.delete(f"{SUPABASE_URL}/rest/v1/ygosu_rank?record_date=eq.{today_str}", headers=db_headers)
    requests.post(f"{SUPABASE_URL}/rest/v1/ygosu_rank", headers=db_headers, json=insert_payload)
    print(f"✅ 일퀘왕 미니로그 연동 장부 매칭 및 저장 완료!")
else:
    print("새로운 내역이 없습니다.")
