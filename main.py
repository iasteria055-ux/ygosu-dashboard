import requests, re, pandas as pd, os, time
from bs4 import BeautifulSoup

# 보라방송(pan_bora) 데이터
URL = "https://ygosu.com/board/pan_bora/?mode=mineral_storage&page="
def crawl():
    give, recv = {}, {}
    for p in range(1, 21): # 최근 20페이지 스캔
        soup = BeautifulSoup(requests.get(URL+str(p), headers={"User-Agent": "Mozilla/5.0"}).text, 'html.parser')
        for row in soup.find_all('tr'):
            text = " ".join(row.stripped_strings)
            if '+' in text and any(c.isdigit() for c in text.split('+')[-1]):
                m = re.search(r'(.*?)\+\s*([0-9,]+)', text)
                if m: give[m.group(1).split()[0]] = give.get(m.group(1).split()[0], 0) + int(m.group(2).replace(',', ''))
            elif '-' in text and '에게' in text:
                m = re.search(r'(.*?)\s*-\s*([0-9,]+)', text)
                if m:
                    nick = m.group(1).split('에게')[0].split()[-1]
                    recv[nick] = recv.get(nick, 0) + int(m.group(2).replace(',', ''))
    return give, recv

def save_html(give, recv):
    def make_table(d, color):
        df = pd.DataFrame(list(d.items()), columns=['Nick', 'Min']).sort_values('Min', ascending=False).head(50)
        return f"<table style='width:100%; border-collapse:collapse; color:white;'>{''.join([f'<tr><td>{i+1}</td><td>{r.Nick}</td><td>{r.Min:,}</td></tr>' for i, r in df.iterrows()])}</table>"
    
    html = f"""<html><body style="background:#0f172a; color:white; font-family:sans-serif;">
        <h1 style="text-align:center;">부우 게시판 미네랄 랭킹</h1>
        <div style="display:flex; gap:20px;">
            <div style="flex:1; background:#1e293b; padding:20px; border-radius:15px;"><h2>기부왕</h2>{make_table(give, 'red')}</div>
            <div style="flex:1; background:#1e293b; padding:20px; border-radius:15px;"><h2>일퀘왕</h2>{make_table(recv, 'blue')}</div>
        </div>
    </body></html>"""
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

g, r = crawl()
save_html(g, r)
