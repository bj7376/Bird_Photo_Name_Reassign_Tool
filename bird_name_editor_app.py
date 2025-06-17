# 파일 이름: bird_name_editor_app.py (v1.0)
import tkinter as tk
import tkinter.messagebox
import tkinter.simpledialog
from tkinter import filedialog
import customtkinter
import threading
import os
import sys
import re
from typing import Dict, List, Optional
from functools import partial

# 모듈 임포트
import name_check
import thumbnailing
import main_visualizer

# 라이브러리들
import pandas as pd
from PIL import Image, ImageTk
import wikipediaapi

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# --- 원본 이미지 팝업 창 ---
class ImagePopup(customtkinter.CTkToplevel):
    def __init__(self, parent, image_path: str, title: str):
        super().__init__(parent)
        self.title(f"원본 이미지: {title}")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()
        
        try:
            # 원본 이미지 로드 및 크기 조정
            with Image.open(image_path) as img:
                # EXIF orientation 처리
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif and 274 in exif:
                        orientation = exif[274]
                        if orientation == 3:
                            img = img.rotate(180, expand=True)
                        elif orientation == 6:
                            img = img.rotate(270, expand=True)
                        elif orientation == 8:
                            img = img.rotate(90, expand=True)
                
                # 창 크기에 맞게 리사이즈 (비율 유지)
                img.thumbnail((750, 550), Image.Resampling.LANCZOS)
                
                # CustomTkinter 이미지로 변환
                ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=img.size)
                
                # 이미지 라벨
                img_label = customtkinter.CTkLabel(self, image=ctk_img, text="")
                img_label.pack(expand=True, fill="both", padx=10, pady=10)
                
        except Exception as e:
            error_label = customtkinter.CTkLabel(self, text=f"이미지 로드 실패: {e}")
            error_label.pack(expand=True, fill="both")
        
        # 닫기 버튼
        close_btn = customtkinter.CTkButton(self, text="닫기", command=self.destroy)
        close_btn.pack(pady=10)

# --- 리포트 선택을 위한 커스텀 대화상자 ---
class ReportDialog(customtkinter.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("리포트 형식 선택")
        self.geometry("450x300")
        self.transient(parent) # 부모 창 위에 표시
        self.grab_set() # 이 창에만 포커스

        self.choice = None
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        main_frame = customtkinter.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        title_label = customtkinter.CTkLabel(main_frame, text="탐조 리포트 생성 형식", font=customtkinter.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=(0, 10))
        
        desc_label = customtkinter.CTkLabel(
            main_frame, 
            text="편집된 사진 목록과 새 정보를 바탕으로\n깔끔하게 정리된 요약 문서를 생성합니다.",
            justify="center",
            text_color="gray60"
        )
        desc_label.pack(pady=(0, 20))

        self.radio_var = tk.StringVar(value="html")
        options = {
            "HTML (웹 브라우저로 열기)": "html",
            "Word (DOCX 문서 파일)": "docx",
            "HTML과 Word 모두 생성": "both",
            "리포트 생성 안함": "none"
        }

        for text, value in options.items():
            radio = customtkinter.CTkRadioButton(main_frame, text=text, variable=self.radio_var, value=value)
            radio.pack(anchor="w", padx=30, pady=5)
            
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(20, 0))

        ok_button = customtkinter.CTkButton(button_frame, text="확인", command=self._on_ok)
        ok_button.pack(side="left", padx=10)
        
        cancel_button = customtkinter.CTkButton(button_frame, text="취소", command=self._on_cancel, fg_color="gray50")
        cancel_button.pack(side="left", padx=10)
        
    def _on_ok(self):
        self.choice = self.radio_var.get()
        self.destroy()

    def _on_cancel(self):
        self.choice = None
        self.destroy()

    def get_choice(self):
        # 창이 닫힐 때까지 기다림
        self.wait_window()
        return self.choice


class BirdNameEditor(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("파일명 기반 새 사진 그룹화 및 새 이름 변경 도구 v1.0")
        self.geometry("1600x1000")
        
        # 데이터 저장소
        self.source_folder = ""
        self.thumbnail_folder = ""
        self.species_photo_map: Dict[str, List[Dict]] = {}
        self.bird_name_map: Dict[str, str] = {}
        self.bird_info_map: Dict[str, Dict] = {}
        self.korean_names_list: List[str] = []
        self.csv_db: Optional[pd.DataFrame] = None
        self.active_entry: Optional[customtkinter.CTkEntry] = None
        self.autocomplete_listbox: Optional[tk.Listbox] = None

        self.wiki = wikipediaapi.Wikipedia(
            user_agent='BirdRenamerApp/1.0',
            language='ko',
            extract_format=wikipediaapi.ExtractFormat.WIKI
        )
        
        # --- UI 구성 ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.top_frame = customtkinter.CTkFrame(self, height=50)
        self.top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.btn_load = customtkinter.CTkButton(self.top_frame, text="사진 폴더 열기", command=self.select_folder_and_load)
        self.btn_load.pack(side="left", padx=10, pady=10)
        
        self.folder_label = customtkinter.CTkLabel(self.top_frame, text="불러온 폴더가 없습니다.", anchor="w")
        self.folder_label.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        self.btn_save = customtkinter.CTkButton(self.top_frame, text="변경된 이름으로 저장 및 리포트 생성", command=self.save_changes, state="disabled")
        self.btn_save.pack(side="right", padx=10, pady=10)

        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.species_list_frame = customtkinter.CTkScrollableFrame(self.main_frame, width=300)
        self.species_list_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")
        self.species_list_label = customtkinter.CTkLabel(self.species_list_frame, text="탐지된 조류 목록", font=customtkinter.CTkFont(size=15, weight="bold"))
        self.species_list_label.pack(pady=5, padx=10, fill="x")

        self.photo_view_frame = customtkinter.CTkScrollableFrame(self.main_frame)
        self.photo_view_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.photo_view_intro_label = customtkinter.CTkLabel(self.photo_view_frame, text="\n\n\n\n폴더를 열면 이곳에 사진이 표시됩니다.", font=customtkinter.CTkFont(size=20))
        self.photo_view_intro_label.pack(expand=True, fill="both")

        self.status_bar = customtkinter.CTkFrame(self, height=30)
        self.status_bar.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.status_label = customtkinter.CTkLabel(self.status_bar, text="준비 완료.", anchor="w")
        self.status_label.pack(side="left", padx=10)
        
        self.load_db()

    def load_db(self):
        try:
            # 먼저 영명이 보완된 CSV 파일을 찾아보기
            enhanced_csv_path = get_resource_path(os.path.join('renamer_data', '새와생명의터_조류목록_2022_영명보완.csv'))
            if not os.path.exists(enhanced_csv_path):
                enhanced_csv_path = get_resource_path('새와생명의터_조류목록_2022_영명보완.csv')
            
            # 영명 보완된 파일이 있으면 우선 사용
            if os.path.exists(enhanced_csv_path):
                csv_path = enhanced_csv_path
                self.update_status("영명 보완된 조류 DB 발견, 로드 중...")
            else:
                # 없으면 원본 파일 사용
                csv_path = get_resource_path(os.path.join('renamer_data', '새와생명의터_조류목록_2022.csv'))
                if not os.path.exists(csv_path):
                    csv_path = get_resource_path('새와생명의터_조류목록_2022.csv')
                
                if not os.path.exists(csv_path):
                    raise FileNotFoundError("CSV 파일을 'renamer_data' 폴더 또는 프로그램 폴더에서 찾을 수 없습니다.")
                
                self.update_status("원본 조류 DB 로드 중... (csv_preprocessor.py로 영명을 미리 보완하는 것을 권장합니다)")

            self.csv_db = pd.read_csv(csv_path)
            
            # 컬럼 정리 (영명 컬럼이 있을 수도 없을 수도 있음)
            for col in ['국명', '영명', '학명', '목', '과', 'Wiki목', 'Wiki과']:
                if col in self.csv_db.columns:
                    self.csv_db[col] = self.csv_db[col].fillna('')
            
            self.korean_names_list = sorted(list(self.csv_db['국명'].dropna().unique()))
            
            # 영명 보완된 파일인지 확인
            if '영명' in self.csv_db.columns:
                filled_english = self.csv_db['영명'].notna() & (self.csv_db['영명'] != '') & (self.csv_db['영명'] != 'nan')
                english_count = filled_english.sum()
                total_count = len(self.csv_db)
                
                if english_count > 0:
                    self.update_status(f"조류 DB 로드 완료. (영명 {english_count}/{total_count}개 보완됨)")
                else:
                    self.update_status("조류 DB 로드 완료. (영명 정보 없음 - csv_preprocessor.py 실행 권장)")
            else:
                self.update_status("조류 DB 로드 완료. (영명 컬럼 없음 - csv_preprocessor.py 실행 권장)")
                
        except Exception as e:
            tkinter.messagebox.showwarning(
                "DB 로드 실패", 
                f"조류 목록 CSV 파일을 불러오는 데 실패했습니다: {e}\n\n"
                f"해결 방법:\n"
                f"1. csv_preprocessor.py를 먼저 실행하여 영명을 보완하세요\n"
                f"2. 원본 CSV 파일이 올바른 위치에 있는지 확인하세요\n\n"
                f"자동완성 기능이 제한됩니다."
            )
            self.korean_names_list = []

    def update_status(self, msg: str):
        self.status_label.configure(text=msg)
        self.update_idletasks()

    def select_folder_and_load(self):
        folder = filedialog.askdirectory()
        if not folder: return
        
        self.source_folder = folder
        self.folder_label.configure(text=f"현재 폴더: {self.source_folder}")
        self.btn_save.configure(state="disabled")

        self.species_photo_map.clear()
        self.bird_name_map.clear()
        self.bird_info_map.clear()
        
        for widget in self.species_list_frame.winfo_children(): widget.destroy()
        for widget in self.photo_view_frame.winfo_children(): widget.destroy()
        
        self.species_list_label = customtkinter.CTkLabel(self.species_list_frame, text="탐지된 조류 목록", font=customtkinter.CTkFont(size=15, weight="bold"))
        self.species_list_label.pack(pady=5, padx=10, fill="x")
        
        self.photo_view_intro_label = customtkinter.CTkLabel(self.photo_view_frame, text="\n\n\n\n사진을 불러오는 중입니다...", font=customtkinter.CTkFont(size=20))
        self.photo_view_intro_label.pack(expand=True, fill="both")

        threading.Thread(target=self.load_photos_thread, daemon=True).start()

    def load_photos_thread(self):
        try:
            self.update_status("사진 파일 목록을 읽는 중...")
            image_extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}
            all_files = [f for f in os.listdir(self.source_folder) if os.path.splitext(f)[1].lower() in image_extensions]
            
            self.thumbnail_folder = os.path.join(self.source_folder, "renamer_thumbnails")
            os.makedirs(self.thumbnail_folder, exist_ok=True)

            for i, filename in enumerate(all_files):
                self.update_status(f"파일 분석 중 ({i+1}/{len(all_files)}): {filename}")
                file_path = os.path.join(self.source_folder, filename)
                
                guessed_names = name_check.extract_korean_bird_names_from_filename(filename)
                initial_bird_name = guessed_names[0] if guessed_names else "미분류"
                
                if initial_bird_name not in self.bird_info_map:
                    self.bird_info_map[initial_bird_name] = name_check.resolve_bird_info(
                        initial_bird_name, self.csv_db, self.wiki
                    )

                thumb_path = os.path.join(self.thumbnail_folder, f"{os.path.splitext(filename)[0]}_thumb.jpg")
                if not os.path.exists(thumb_path):
                    thumbnailing.create_single_thumbnail(file_path, thumb_path)

                dt = None
                try:
                    with Image.open(file_path) as img: dt = thumbnailing.get_photo_datetime(img)
                except Exception: pass

                photo_info = {"original_filename": filename, "path": file_path, "thumbnail_path": thumb_path, "datetime": dt}
                
                if initial_bird_name not in self.species_photo_map:
                    self.species_photo_map[initial_bird_name] = []
                self.species_photo_map[initial_bird_name].append(photo_info)
                self.bird_name_map[filename] = initial_bird_name

            self.update_status("종 목록 표시...")
            self.display_species_list()
            self.btn_save.configure(state="normal")
            self.update_status("사진 로딩 완료.")

        except Exception as e:
            self.update_status(f"오류: {e}")
            tkinter.messagebox.showerror("오류", f"사진 로딩 중 오류 발생: {e}")

    def display_species_list(self):
        for widget in self.species_list_frame.winfo_children():
            if isinstance(widget, customtkinter.CTkButton): widget.destroy()
        
        sorted_species = sorted(self.species_photo_map.keys())
        for species_name in sorted_species:
            btn = customtkinter.CTkButton(
                self.species_list_frame,
                text=f"{species_name} ({len(self.species_photo_map[species_name])})",
                command=partial(self.display_photos_for_species, species_name)
            )
            btn.pack(fill="x", padx=5, pady=2)
        
        if self.photo_view_intro_label.winfo_exists():
            self.photo_view_intro_label.configure(text="\n\n\n\n왼쪽 목록에서 편집할 새 종류를 선택하세요.")

    def display_photos_for_species(self, species_name: str):
        for widget in self.photo_view_frame.winfo_children(): widget.destroy()
        photo_list = self.species_photo_map[species_name]
        
        control_frame = customtkinter.CTkFrame(self.photo_view_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        control_frame.grid_columnconfigure(1, weight=1)

        name_label = customtkinter.CTkLabel(control_frame, text=f"'{species_name}' 그룹 이름 변경:", font=customtkinter.CTkFont(size=14, weight="bold"))
        name_label.grid(row=0, column=0, padx=10, pady=10)

        entry = customtkinter.CTkEntry(control_frame, font=customtkinter.CTkFont(size=14))
        entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        entry.insert(0, species_name if species_name != "미분류" else "")
        
        entry.bind("<KeyRelease>", self.on_key_release)
        entry.bind("<FocusIn>", lambda e, en=entry: self.on_entry_focus(en))
        entry.bind("<FocusOut>", self.on_entry_focus_out)
        entry.bind("<KeyRelease>", lambda e, s=species_name, en=entry: self.update_filename_previews(s, en.get()), add="+")

        rename_btn = customtkinter.CTkButton(control_frame, text="이름 확정 및 정보 업데이트", command=lambda: self.update_group_name(species_name, entry.get()))
        rename_btn.grid(row=0, column=2, padx=10, pady=10)
        
        # 종 정보 표시 영역 추가
        info_frame = customtkinter.CTkFrame(self.photo_view_frame)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        info_label = customtkinter.CTkLabel(info_frame, text="종 정보", font=customtkinter.CTkFont(size=14, weight="bold"))
        info_label.pack(pady=(10, 5))
        
        bird_info = self.bird_info_map.get(species_name, {})
        info_text = f"국명: {bird_info.get('korean_name', species_name)}\n"
        info_text += f"영명: {bird_info.get('common_name', 'N/A')}\n"
        info_text += f"학명: {bird_info.get('scientific_name', 'N/A')}\n"
        info_text += f"분류: 목 {bird_info.get('order', 'N/A')}, 과 {bird_info.get('family', 'N/A')}"
        
        info_display = customtkinter.CTkLabel(info_frame, text=info_text, justify="left", 
                                            font=customtkinter.CTkFont(size=12))
        info_display.pack(pady=(0, 10), padx=10)
        
        # 미리보기와 정보를 업데이트하는 함수 저장
        self.current_info_display = info_display
        
        thumb_grid_frame = customtkinter.CTkFrame(self.photo_view_frame, fg_color="transparent")
        thumb_grid_frame.pack(fill="both", expand=True)
        
        cols = 5
        for i, photo_info in enumerate(photo_list):
            row, col = divmod(i, cols)
            thumb_frame = customtkinter.CTkFrame(thumb_grid_frame)
            thumb_frame.grid(row=row, column=col, padx=5, pady=5)
            
            try:
                # 썸네일을 정사각형으로 크롭하여 표시
                img = Image.open(photo_info["thumbnail_path"])
                
                # 정사각형으로 크롭
                width, height = img.size
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                right = left + size
                bottom = top + size
                img_cropped = img.crop((left, top, right, bottom))
                img_cropped = img_cropped.resize((200, 200), Image.Resampling.LANCZOS)
                
                ctk_img = customtkinter.CTkImage(light_image=img_cropped, dark_image=img_cropped, size=(200, 200))
                
                # 클릭 가능한 이미지 라벨 (원본 보기용)
                img_label = customtkinter.CTkLabel(thumb_frame, image=ctk_img, text="", cursor="hand2")
                img_label.pack(pady=(5,0))
                img_label.bind("<Button-1>", lambda e, path=photo_info["path"], name=photo_info["original_filename"]: self.show_original_image(path, name))
                
                original_name_label = customtkinter.CTkLabel(thumb_frame, text=photo_info["original_filename"], wraplength=190, font=customtkinter.CTkFont(size=12))
                original_name_label.pack(padx=5)

                preview_label = customtkinter.CTkLabel(thumb_frame, text="", wraplength=190, font=customtkinter.CTkFont(size=12, weight="bold"), text_color="#3498db")
                preview_label.pack(padx=5, pady=(0,5))
                photo_info['preview_label'] = preview_label
            except Exception as e:
                error_label = customtkinter.CTkLabel(thumb_frame, text=f"썸네일 로드 실패\n{e}")
                error_label.pack(padx=5, pady=5)
        
        self.update_filename_previews(species_name, entry.get())

    def show_original_image(self, image_path: str, filename: str):
        """원본 이미지를 팝업으로 표시"""
        ImagePopup(self, image_path, filename)

    def update_filename_previews(self, species_name: str, new_bird_name: str):
        photo_list = self.species_photo_map.get(species_name, [])
        
        # 실시간으로 종 정보 업데이트 (입력 중일 때)
        if hasattr(self, 'current_info_display') and self.current_info_display.winfo_exists():
            if new_bird_name and new_bird_name != species_name:
                # 임시로 CSV에서 정보 검색해서 미리보기
                temp_info = name_check.search_csv_by_korean_name(self.csv_db, new_bird_name)
                if temp_info:
                    info_text = f"국명: {temp_info['korean_name']}\n"
                    info_text += f"영명: {temp_info['common_name']}\n"
                    info_text += f"학명: {temp_info['scientific_name']}\n"
                    info_text += f"분류: 목 {temp_info['order']}, 과 {temp_info['family']}"
                    self.current_info_display.configure(text=info_text)
                else:
                    info_text = f"국명: {new_bird_name}\n영명: 검색 중...\n학명: 검색 중...\n분류: 검색 중..."
                    self.current_info_display.configure(text=info_text)
            else:
                # 기존 정보 표시
                bird_info = self.bird_info_map.get(species_name, {})
                info_text = f"국명: {bird_info.get('korean_name', species_name)}\n"
                info_text += f"영명: {bird_info.get('common_name', 'N/A')}\n"
                info_text += f"학명: {bird_info.get('scientific_name', 'N/A')}\n"
                info_text += f"분류: 목 {bird_info.get('order', 'N/A')}, 과 {bird_info.get('family', 'N/A')}"
                self.current_info_display.configure(text=info_text)
        
        # 파일명 미리보기 업데이트
        eng_name = ""
        if self.csv_db is not None and new_bird_name:
            result = self.csv_db[self.csv_db['국명'] == new_bird_name]
            if not result.empty:
                eng_name = result.iloc[0].get('영명', '')

        for photo_info in photo_list:
            if 'preview_label' in photo_info and photo_info['preview_label'].winfo_exists():
                kor_name_clean = name_check.sanitize_filename(new_bird_name)
                eng_name_clean = name_check.sanitize_filename(eng_name)
                
                new_base = ""
                if photo_info["datetime"]:
                    timestamp = photo_info["datetime"].strftime("%Y%m%d_%H%M%S")
                    if eng_name_clean and eng_name_clean != "N_A": 
                        new_base = f"{timestamp}_{kor_name_clean}_{eng_name_clean}"
                    else: 
                        new_base = f"{timestamp}_{kor_name_clean}"
                else:
                    if eng_name_clean and eng_name_clean != "N_A": 
                        new_base = f"{kor_name_clean}_{eng_name_clean}"
                    else: 
                        new_base = kor_name_clean

                ext = os.path.splitext(photo_info["original_filename"])[1]
                new_filename = f"{new_base}{ext}" if kor_name_clean else "이름을 입력하세요"
                photo_info['preview_label'].configure(text=f"-> {new_filename}")

    def update_group_name(self, old_species_name: str, new_species_name: str):
        if not new_species_name or new_species_name == old_species_name:
            tkinter.messagebox.showwarning("이름 오류", "변경할 새 이름이 비어있거나 기존 이름과 동일합니다.")
            return

        self.update_status(f"'{new_species_name}' 정보 조회 중 (CSV, Wiki)...")
        self.bird_info_map[new_species_name] = name_check.resolve_bird_info(
            new_species_name, self.csv_db, self.wiki, log_callback=self.update_status
        )
        self.update_status("정보 조회 완료.")

        photo_list = self.species_photo_map.get(old_species_name, [])
        for photo_info in photo_list:
            self.bird_name_map[photo_info['original_filename']] = new_species_name

        if new_species_name in self.species_photo_map:
            self.species_photo_map[new_species_name].extend(photo_list)
        else:
            self.species_photo_map[new_species_name] = photo_list
        del self.species_photo_map[old_species_name]

        self.display_species_list()
        self.display_photos_for_species(new_species_name)
        tkinter.messagebox.showinfo("정보 업데이트 완료", f"'{new_species_name}'의 상세 정보가 업데이트되었습니다.\n이제 파일명을 저장할 수 있습니다.")

    def save_changes(self):
        output_folder = filedialog.askdirectory(title="어디에 저장할까요?")
        if not output_folder: return

        location = tkinter.simpledialog.askstring("탐조 장소", "탐조 장소를 입력하세요 (예: 태화강, 순천만):")
        if location is None: location = "장소 미입력"

        # --- 리포트 선택 대화상자 호출 ---
        dialog = ReportDialog(self)
        report_format = dialog.get_choice() # 사용자가 선택할 때까지 대기
        
        # 사용자가 취소(X 버튼 또는 취소 버튼)한 경우
        if report_format is None:
            self.update_status("저장이 취소되었습니다.")
            return
        # --------------------------------

        def save_in_background(chosen_report_format):
            try:
                self.update_status("파일 복사 및 이름 변경 시작...")
                copied_files = thumbnailing.copy_and_rename_files(
                    self.source_folder, self.bird_name_map, self.species_photo_map,
                    self.bird_info_map,
                    output_folder, self.update_status
                )
                
                self.update_status("새로운 썸네일 생성 중...")
                thumbnailing.update_thumbnails_for_copied_files(
                    copied_files, os.path.join(output_folder, "renamer_thumbnails"), log_callback=self.update_status
                )
                
                if chosen_report_format != "none":
                    self.update_status("시각적 리포트 생성 중...")
                    report_options = {'format': chosen_report_format, 'thumbnail_size': 'medium'}
                    main_visualizer.create_visual_reports(
                        copied_files, self.bird_info_map, output_folder, 
                        report_options, location, self.update_status
                    )
                
                unique_bird_names = {name for name in self.bird_name_map.values() if name != "미분류"}
                self.update_status(f"저장 완료! {len(copied_files)}개 파일 저장됨")
                
                msg = (f"편집이 완료되었습니다!\n\n"
                       f"저장 위치: {output_folder}\n"
                       f"처리된 파일: {len(copied_files)}개\n"
                       f"고유 종수: {len(unique_bird_names)}종\n\n")

                if chosen_report_format != "none":
                    msg += f"'편집완료_탐조기록' 폴더에서 생성된 리포트를 확인하세요."

                tkinter.messagebox.showinfo("저장 완료", msg)
                
            except Exception as e:
                self.update_status(f"저장 오류: {e}")
                import traceback
                traceback.print_exc()
                tkinter.messagebox.showerror("오류", f"저장 중 오류가 발생했습니다: {e}")

        threading.Thread(target=save_in_background, args=(report_format,), daemon=True).start()

    def on_entry_focus(self, entry_widget):
        self.active_entry = entry_widget
        if self.autocomplete_listbox:
            self.autocomplete_listbox.destroy()
            self.autocomplete_listbox = None
    
    def on_entry_focus_out(self, event):
        self.after(200, self.hide_autocomplete)

    def hide_autocomplete(self):
        if self.autocomplete_listbox:
            self.autocomplete_listbox.destroy()
            self.autocomplete_listbox = None

    def on_key_release(self, event):
        if not self.active_entry: return
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return

        current_text = self.active_entry.get()
        if self.autocomplete_listbox: self.autocomplete_listbox.destroy()
        if not current_text: return

        suggestions = name_check.fuzzy_search_kor_name(current_text, self.korean_names_list)
        
        if suggestions:
            self.autocomplete_listbox = tk.Listbox(self, height=min(len(suggestions), 5), font=("Malgun Gothic", 12))
            for s in suggestions: self.autocomplete_listbox.insert(tk.END, s)
            
            x = self.active_entry.winfo_rootx()
            y = self.active_entry.winfo_rooty() + self.active_entry.winfo_height()
            self.autocomplete_listbox.place(x=x, y=y)
            self.autocomplete_listbox.bind("<<ListboxSelect>>", self.on_autocomplete_select)

    def on_autocomplete_select(self, event):
        if not self.autocomplete_listbox or not self.active_entry: return
        selection_indices = self.autocomplete_listbox.curselection()
        if not selection_indices: return

        selected_value = self.autocomplete_listbox.get(selection_indices[0])
        self.active_entry.delete(0, tk.END)
        self.active_entry.insert(0, selected_value)
        self.hide_autocomplete()
        self.active_entry.focus()
        self.active_entry.event_generate("<KeyRelease>")


def main():
    app = BirdNameEditor()
    app.mainloop()

if __name__ == "__main__":
    main()