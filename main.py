import requests
from bs4 import BeautifulSoup
from supabase import create_client
import os

# 1. 환경 설정 (깃허브 Secret에 등록된 키를 사용합니다)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_data_from_ygosu():
    # 데이터를 수집하는 기존 로직을 여기에 구현하세요
    # 예: data_list = [ {'nickname': 'XOXA', 'give_mineral': 100, 'recv_mineral': 50}, ... ]
    return data_list

def apply_custom_rule(data_list):
    # 'XOXA'의 기부량을 찾아 '초우코송이'에게 덮어씌우는 로직
    target_value = 0
    
    # 1. XOXA의 기부량 가져오기
    for user in data_list:
        if user['nickname'] == 'XOXA':
            target_value = user['give_mineral']
            break
            
    # 2. 초우코송이의 기부량을 XOXA의 값으로 덮어씌우기
    for user in data_list:
        if user['nickname'] == '초우코송이':
            user['give_mineral'] = target_value
            break
            
    return data_list

def upload_to_supabase(data_list):
    # 기존 데이터 삭제 (id가 0이 아닌 모든 데이터 삭제)
    supabase.table("ygosu_rank").delete().neq("id", 0).execute()
    # 보정된 새 데이터 삽입
    supabase.table("ygosu_rank").insert(data_list).execute()

# 메인 실행부
if __name__ == "__main__":
    raw_data = get_data_from_ygosu()
    # raw_data가 비어있지 않은지 확인 후 로직 수행
    if raw_data:
        refined_data = apply_custom_rule(raw_data)
        upload_to_supabase(refined_data)
        print("데이터 업데이트 완료!")
    else:
        print("수집된 데이터가 없습니다.")
