# 파일 이름: name_check.py (정보 조회 로직 개선)
import re
from typing import Dict, List, Optional
import pandas as pd
import wikipediaapi

def sanitize_filename(name: str) -> str:
    """파일명에 사용할 수 없는 문자 제거 및 공백을 언더스코어로 변경"""
    if not isinstance(name, str):
        return ""
    name = name.strip()
    name = name.replace('*', '')
    name = re.sub(r'[\\/:"*?<>|]', '', name)
    return re.sub(r"\s+", "_", name)

def extract_korean_bird_names_from_filename(filename: str) -> List[str]:
    """파일명에서 한글 새 이름 후보들을 추출"""
    basename = re.sub(r'\.[^.]+$', '', filename)
    basename = re.sub(r'\d{8}_\d{6}_?', '', basename)
    basename = re.sub(r'\d{4}-\d{2}-\d{2}[\s_-]\d{2}[\s_:-]\d{2}[\s_:-]\d{2}', '', basename)
    basename = basename.replace('_', ' ').replace('-', ' ')
    basename = re.sub(r'\s+', ' ', basename).strip()
    korean_words = re.findall(r'[\uac00-\ud7a3]+', basename)
    return [" ".join(korean_words)] if korean_words else []

def search_csv_by_korean_name(df: Optional[pd.DataFrame], name: str) -> Optional[Dict]:
    """CSV 데이터프레임에서 국명으로 새 정보 검색"""
    if df is None or not isinstance(name, str) or name.strip() == "": 
        return None
    try:
        result = df[df['국명'] == name.strip()]
        if not result.empty:
            bird_info = result.iloc[0].to_dict()
            return {
                "korean_name": bird_info.get("국명", name),
                "common_name": bird_info.get("영명", ""),
                "scientific_name": bird_info.get("학명", ""),
                "order": bird_info.get("목", ""), 
                "family": bird_info.get("과", ""),
            }
    except Exception: 
        pass
    return None

def get_info_from_wikipedia(wiki, korean_name: str, log_callback=None) -> Dict:
    """위키피디아에서 정보(영문명, 학명 등)를 가져오는 함수 - 다국어 링크 활용"""
    info = {"common_name": "", "scientific_name": "", "order": "", "family": ""}
    if not wiki or not korean_name: 
        return info
    
    try:
        # 1. 한국어 페이지에서 기본 정보 추출
        ko_page = wiki.page(korean_name)
        if not ko_page.exists():
            if log_callback: 
                log_callback(f"  - Wiki 한국어 페이지 '{korean_name}' 없음.")
            return info
            
        ko_summary = ko_page.summary
        
        # 한국어 페이지에서 학명 추출
        sci_name_patterns = [
            r'\((?:학명:)?\s*([A-Z][a-z]+\s+[a-z]+)\)',  # 기본 패턴
            r'학명은?\s*([A-Z][a-z]+\s+[a-z]+)',  # 학명은/학명:
            r'([A-Z][a-z]+\s+[a-z]+)\s*\)',  # 괄호 앞 학명
            r'《([A-Z][a-z]+\s+[a-z]+)》',  # 《학명》 패턴
        ]
        
        for pattern in sci_name_patterns:
            sci_match = re.search(pattern, ko_summary)
            if sci_match:
                info["scientific_name"] = sci_match.group(1).strip()
                break
        
        # 한국어 페이지에서 분류 정보 추출
        order_patterns = [
            r'목[은:]?\s*([가-힣]+목)',
            r'([가-힣]+목)\s*에\s*속',
            r'속하는\s*([가-힣]+목)',
        ]
        
        for pattern in order_patterns:
            order_match = re.search(pattern, ko_summary)
            if order_match:
                info["order"] = order_match.group(1).strip()
                break
        
        family_patterns = [
            r'과[은:]?\s*([가-힣]+과)',
            r'([가-힣]+과)\s*에\s*속',
            r'속하는\s*([가-힣]+과)',
        ]
        
        for pattern in family_patterns:
            family_match = re.search(pattern, ko_summary)
            if family_match:
                info["family"] = family_match.group(1).strip()
                break
        
        # 2. 영어 페이지에서 영명 가져오기
        try:
            # 다국어 링크에서 영어 페이지 찾기
            if hasattr(ko_page, 'langlinks') and 'en' in ko_page.langlinks:
                english_title = ko_page.langlinks['en']
                if log_callback:
                    log_callback(f"  - 영어 Wiki 페이지 발견: {english_title}")
                
                # 영어 위키백과 인스턴스 생성
                en_wiki = wikipediaapi.Wikipedia(
                    user_agent='BirdRenamerApp/1.0',
                    language='en',
                    extract_format=wikipediaapi.ExtractFormat.WIKI
                )
                
                en_page = en_wiki.page(english_title)
                if en_page.exists():
                    # 영어 제목이 곧 영명
                    english_title_clean = english_title.strip()
                    
                    # 괄호 안의 내용 제거 (disambiguation 등)
                    english_title_clean = re.sub(r'\s*\([^)]*\)', '', english_title_clean)
                    
                    if english_title_clean and len(english_title_clean) < 50:
                        info["common_name"] = english_title_clean
                        if log_callback:
                            log_callback(f"  - 영명 발견: {english_title_clean}")
                    
                    # 영어 페이지에서 추가 학명 확인 (더 정확할 수 있음)
                    if not info["scientific_name"]:
                        en_summary = en_page.summary
                        en_sci_patterns = [
                            r'\(([A-Z][a-z]+\s+[a-z]+)\)',  # (Scientific name)
                            r'scientifically known as ([A-Z][a-z]+\s+[a-z]+)',
                            r'binomial name ([A-Z][a-z]+\s+[a-z]+)',
                        ]
                        
                        for pattern in en_sci_patterns:
                            en_sci_match = re.search(pattern, en_summary)
                            if en_sci_match:
                                info["scientific_name"] = en_sci_match.group(1).strip()
                                break
            else:
                if log_callback:
                    log_callback(f"  - 영어 Wiki 페이지 링크 없음.")
                    
        except Exception as e:
            if log_callback:
                log_callback(f"  - 영어 Wiki 조회 중 오류: {e}")
        
        # 3. 한국어 페이지에서 영명 찾기 (fallback)
        if not info["common_name"]:
            eng_name_patterns = [
                r'영명[은:]?\s*([A-Za-z][A-Za-z\s-]+[A-Za-z])',  # 영명: 패턴
                r'영어[로는]?\s*([A-Za-z][A-Za-z\s-]+[A-Za-z])',  # 영어로는 패턴
                r'\(영어:\s*([A-Za-z][A-Za-z\s-]+[A-Za-z])\)',  # (영어: ) 패턴
            ]
            
            for pattern in eng_name_patterns:
                eng_match = re.search(pattern, ko_summary)
                if eng_match:
                    candidate = eng_match.group(1).strip()
                    # 학명과 다르고, 적절한 길이인 경우만
                    if (candidate.lower() != info.get("scientific_name", "").lower() and 
                        5 < len(candidate) < 50 and 
                        not any(char in candidate for char in '()[]{}/')):
                        info["common_name"] = candidate
                        if log_callback:
                            log_callback(f"  - 한국어 페이지에서 영명 발견: {candidate}")
                        break
        
        if log_callback: 
            found_info = []
            if info["scientific_name"]: found_info.append("학명")
            if info["common_name"]: found_info.append("영명")
            if info["order"]: found_info.append("목")
            if info["family"]: found_info.append("과")
            
            if found_info:
                log_callback(f"  - Wiki에서 '{korean_name}' {', '.join(found_info)} 정보 발견.")
            else:
                log_callback(f"  - Wiki에서 '{korean_name}' 추가 정보 없음.")
                    
    except Exception as e:
        if log_callback: 
            log_callback(f"  - Wiki 조회 중 오류: {e}")
    
    return info


def resolve_bird_info(korean_name: str, csv_df: pd.DataFrame, wiki, log_callback=None) -> Dict:
    """한글 새 이름으로부터 CSV와 Wikipedia를 종합하여 완전한 새 정보 조회 - 개선된 버전"""
    # 기본 정보 구조
    result = {
        "korean_name": korean_name, 
        "common_name": "", 
        "scientific_name": "",
        "order": "", 
        "family": "", 
        "source": "사용자 입력"
    }
    
    if korean_name == "미분류": 
        return result

    # 1차: CSV에서 검색
    csv_info = search_csv_by_korean_name(csv_df, korean_name)
    if csv_info:
        result.update(csv_info)
        result["source"] = "CSV"
        if log_callback: 
            csv_fields = []
            if csv_info.get("common_name"): csv_fields.append("영명")
            if csv_info.get("scientific_name"): csv_fields.append("학명") 
            if csv_info.get("order"): csv_fields.append("목")
            if csv_info.get("family"): csv_fields.append("과")
            
            if csv_fields:
                log_callback(f"  - CSV에서 '{korean_name}' {', '.join(csv_fields)} 찾음.")
            else:
                log_callback(f"  - CSV에서 '{korean_name}' 국명만 있음 (다른 정보 비어있음).")
    else:
        if log_callback: 
            log_callback(f"  - CSV에서 '{korean_name}' 정보 없음.")

    # 2차: Wikipedia에서 검색 (항상 실행하여 부족한 정보 보완)
    missing_fields = []
    if not result.get("common_name"): missing_fields.append("영명")
    if not result.get("scientific_name"): missing_fields.append("학명")
    if not result.get("order"): missing_fields.append("목")
    if not result.get("family"): missing_fields.append("과")
    
    if missing_fields or not csv_info:
        if log_callback:
            if missing_fields:
                log_callback(f"  - Wiki에서 '{korean_name}' {', '.join(missing_fields)} 검색 중...")
            else:
                log_callback(f"  - Wiki에서 '{korean_name}' 추가 정보 확인 중...")
        
        wiki_info = get_info_from_wikipedia(wiki, korean_name, log_callback)
        
        if any(wiki_info.values()):  # Wiki에서 뭔가 찾은 경우
            updated_fields = []
            
            # 비어있는 정보만 Wiki로 보완
            if not result.get("common_name") and wiki_info.get("common_name"):
                result["common_name"] = wiki_info["common_name"]
                updated_fields.append("영명")
                
            if not result.get("scientific_name") and wiki_info.get("scientific_name"):
                result["scientific_name"] = wiki_info["scientific_name"]
                updated_fields.append("학명")
                
            if not result.get("order") and wiki_info.get("order"):
                result["order"] = wiki_info["order"]
                updated_fields.append("목")
                
            if not result.get("family") and wiki_info.get("family"):
                result["family"] = wiki_info["family"]
                updated_fields.append("과")
            
            # 소스 정보 업데이트
            if updated_fields:
                if result["source"] == "CSV":
                    result["source"] = f"CSV+Wiki({', '.join(updated_fields)})"
                else:
                    result["source"] = f"Wiki({', '.join(updated_fields)})"
                    
                if log_callback:
                    log_callback(f"  - Wiki에서 {', '.join(updated_fields)} 보완 완료.")
            elif log_callback:
                log_callback(f"  - Wiki에서 유용한 추가 정보 없음.")
        else:
            if log_callback:
                log_callback(f"  - Wiki에서 '{korean_name}' 정보 없음.")
    else:
        if log_callback:
            log_callback(f"  - CSV에서 모든 정보 완전함, Wiki 검색 생략.")
            
    # 최종적으로 비어있는 필드는 'N/A'로 채움
    for key in ["common_name", "scientific_name", "order", "family"]:
        if not result[key]: 
            result[key] = "N/A"
            
    return result

def fuzzy_search_kor_name(query: str, all_names: List[str], limit: int = 10) -> List[str]:
    """자동완성용 한글 이름 유사도 검색"""
    if not query: 
        return []
    query = query.lower()
    exact_matches = [name for name in all_names if query == name.lower()]
    starts_with = [name for name in all_names if name.lower().startswith(query) and name not in exact_matches]
    contains = [name for name in all_names if query in name.lower() and name not in exact_matches + starts_with]
    return (exact_matches + starts_with + contains)[:limit]