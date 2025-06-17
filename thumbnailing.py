# 파일 이름: thumbnailing.py (파일명 생성 로직 및 썸네일 처리 개선)
import os
import shutil
import re
from typing import Dict, List
from PIL import Image
from datetime import datetime
import name_check # sanitize_filename 함수 사용을 위해 임포트

def get_photo_datetime(img: Image.Image) -> datetime | None:
    """EXIF에서 촬영 시간 추출"""
    try:
        exif = img._getexif()
        if not exif: return None
        ds = exif.get(36867) or exif.get(306)
        return datetime.strptime(ds, "%Y:%m:%d %H:%M:%S") if ds else None
    except (AttributeError, KeyError, IndexError, TypeError):
        return None

def create_single_thumbnail(image_path: str, thumbnail_path: str, size: tuple = (200, 200)) -> bool:
    """단일 이미지의 썸네일 생성 - 정사각형 크롭 버전"""
    try:
        with Image.open(image_path) as img:
            # EXIF orientation 처리
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif and 274 in exif:
                    orientation = exif[274]
                    if orientation == 3: img = img.rotate(180, expand=True)
                    elif orientation == 6: img = img.rotate(270, expand=True)
                    elif orientation == 8: img = img.rotate(90, expand=True)
            
            # RGB 변환
            if img.mode != 'RGB': img = img.convert('RGB')
            
            # 정사각형으로 크롭
            width, height = img.size
            size_crop = min(width, height)
            left = (width - size_crop) // 2
            top = (height - size_crop) // 2
            right = left + size_crop
            bottom = top + size_crop
            img_cropped = img.crop((left, top, right, bottom))
            
            # 리사이즈
            img_cropped = img_cropped.resize(size, Image.Resampling.LANCZOS)
            
            os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
            img_cropped.save(thumbnail_path, "JPEG", quality=85)
            return True
    except Exception as e:
        print(f"썸네일 생성 실패 ({image_path}): {e}")
        return False

def copy_and_rename_files(source_folder: str, bird_name_map: Dict[str, str], 
                          species_photo_map: Dict[str, List[Dict]], 
                          bird_info_map: Dict[str, Dict], # 상세 정보 맵 추가
                          output_folder: str, log_callback=None) -> List[Dict]:
    """편집된 이름으로 원본 파일 복사 및 이름 변경 ('시각_국명_영명' 형식)"""
    copied_files = []
    if log_callback: log_callback("원본 파일 복사 및 이름 변경 시작...")

    for original_filename, new_bird_name in bird_name_map.items():
        if new_bird_name == "미분류": continue
        source_path = os.path.join(source_folder, original_filename)
        if not os.path.exists(source_path): continue

        try:
            # bird_info_map에서 국명, 영문명 가져오기
            info = bird_info_map.get(new_bird_name, {})
            kor_name_clean = name_check.sanitize_filename(new_bird_name)
            eng_name_clean = name_check.sanitize_filename(info.get("common_name", ""))
            
            # 촬영 시간 정보 찾기
            dt = None
            for photos in species_photo_map.values():
                for p in photos:
                    if p['original_filename'] == original_filename:
                        dt = p.get('datetime')
                        break
                if dt: break
            
            # 새 파일명 생성 ('시각_국명_영명' 형식)
            if dt:
                timestamp = dt.strftime("%Y%m%d_%H%M%S")
                if eng_name_clean and eng_name_clean not in ["N_A", ""]:
                    new_base = f"{timestamp}_{kor_name_clean}_{eng_name_clean}"
                else:
                    new_base = f"{timestamp}_{kor_name_clean}"
            else: # 날짜 없을 경우
                if eng_name_clean and eng_name_clean not in ["N_A", ""]:
                    new_base = f"{kor_name_clean}_{eng_name_clean}"
                else:
                    new_base = kor_name_clean

            ext = os.path.splitext(original_filename)[1]
            new_filename = f"{new_base}{ext}"
            
            # 중복 파일명 처리
            counter = 1
            final_filename = new_filename
            while os.path.exists(os.path.join(output_folder, final_filename)):
                final_filename = f"{new_base}_{counter}{ext}"
                counter += 1
            
            # 원본 파일 복사 (썸네일이 아닌 원본!)
            dest_path = os.path.join(output_folder, final_filename)
            os.makedirs(output_folder, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            
            copied_info = {
                "original_path": source_path, 
                "new_path": dest_path, 
                "new_filename": final_filename, 
                "bird_name": new_bird_name, 
                "datetime": dt
            }
            copied_files.append(copied_info)
            if log_callback: log_callback(f"  - 복사: {final_filename}")
                
        except Exception as e:
            if log_callback: log_callback(f"  - 복사 실패 ({original_filename}): {e}")
            continue
    return copied_files

def update_thumbnails_for_copied_files(copied_files: List[Dict], thumbnail_folder: str, 
                                     size: tuple = (200, 200), log_callback=None):
    """복사된 파일들의 새로운 썸네일 생성 (정사각형 크롭)"""
    if log_callback: log_callback(f"🖼️ 새 썸네일 생성 중 (정사각형 크롭)...")
    os.makedirs(thumbnail_folder, exist_ok=True)
    
    success_count = 0
    for file_info in copied_files:
        new_path = file_info['new_path']
        name_without_ext = os.path.splitext(file_info['new_filename'])[0]
        new_thumbnail_path = os.path.join(thumbnail_folder, f"{name_without_ext}_thumb.jpg")
        
        if create_single_thumbnail(new_path, new_thumbnail_path, size):
            file_info['new_thumbnail_path'] = new_thumbnail_path
            success_count += 1
        else:
            file_info['new_thumbnail_path'] = None
            
    if log_callback: log_callback(f"  - {success_count}/{len(copied_files)}개 썸네일 생성 완료")