# 파일명 기반 새 사진 그룹화 및 새 이름 변경 도구 v1.0


> 탐조 사진을 효율적으로 정리하고 아름다운 관찰 보고서를 생성하는 GUI 프로그램

## 📸 주요 기능

### 🔄 지능적인 파일명 변경
- **자동 종 인식**: 파일명에서 한글 조류명 자동 추출
- **표준화된 명명**: `날짜시간_국명_영명.확장자` 형식으로 일관성 있게 정리
- **실시간 미리보기**: 변경될 파일명을 미리 확인

### 🐦 포괄적인 조류 정보 관리
- **CSV 데이터베이스**: 새와생명의터 조류목록 2022 기반 (591종)
- **Wikipedia 연동**: 부족한 정보를 실시간으로 보완
- **다국어 지원**: 국명, 영명, 학명, 분류 정보 (목/과) 자동 수집

### 🖼️ 직관적인 사진 관리
- **종별 그룹핑**: 같은 종의 사진들을 자동으로 그룹화
- **정사각형 썸네일**: 일관된 크기의 미리보기 이미지
- **원본 보기**: 썸네일 클릭으로 원본 이미지 팝업

### 📊 아름다운 관찰 보고서
- **HTML 리포트**: 웹 브라우저에서 볼 수 있는 시각적 보고서
- **Word 문서**: 편집 가능한 DOCX 형식 리포트
- **통계 요약**: 관찰 건수, 종수, 과수, 목수 자동 집계
- **시간 정보**: EXIF 데이터 기반 촬영 시간 분석

## 🚀 빠른 시작

### 설치 방법

#### 방법 1: 실행파일 다운로드 (권장)
1. [Releases](../../releases) 페이지에서 최신 버전 다운로드
2. `조류사진편집기.exe` 실행
3. 별도 설치 없이 바로 사용 가능

#### 방법 2: 소스 코드 실행
```bash
# 저장소 클론
git clone https://github.com/username/bird-photo-editor.git
cd bird-photo-editor

# 의존성 설치
pip install -r requirements.txt

# 프로그램 실행
python bird_name_editor_app.py
```

### 사용법

1. **사진 폴더 열기** 버튼으로 정리할 사진들이 있는 폴더 선택
2. 왼쪽 목록에서 편집할 종 선택
3. 종 이름을 정확히 입력하고 **이름 확정 및 정보 업데이트** 클릭
4. 모든 종 편집 완료 후 **변경된 이름으로 저장 및 리포트 생성** 클릭
5. 저장 위치와 탐조 장소 입력, 리포트 형식 선택
6. 완료!

## 📋 시스템 요구사항

- **운영체제**: Windows 10/11, macOS 10.14+, Linux
- **Python**: 3.8 이상 (소스 코드 실행 시)
- **메모리**: 4GB RAM 권장
- **저장공간**: 100MB 이상
- **인터넷**: Wikipedia 정보 검색 시 필요


### 지원하는 이미지 형식
- JPEG (.jpg, .jpeg)
- PNG (.png)
- TIFF (.tif, .tiff)
- BMP (.bmp)
- GIF (.gif)

### 자동완성 기능
- 조류명 입력 시 자동완성 제안
- 유사도 기반 지능적 검색
- 591종 조류 데이터베이스 기반 (출처: 새와 생명의 터)


## 🔧 개발자 정보

### 의존성 라이브러리
- `customtkinter`: 모던한 GUI 인터페이스
- `wikipediaapi`: Wikipedia 데이터 연동
- `pandas`: 데이터 처리 및 분석
- `Pillow (PIL)`: 이미지 처리 및 EXIF 데이터
- `python-docx`: Word 문서 생성 (선택적)

### 빌드 방법
```bash
# PyInstaller로 단일 실행파일 생성
pip install pyinstaller
pyinstaller --onefile --windowed --name="조류사진편집기" bird_name_editor_app.py
```

## 📈 업데이트 내역

### v1.0.0 (2025-06-17)
- 🎉 **첫 번째 릴리즈**
- ✨ 지능적인 파일명 변경 시스템
- 🐦 Wikipedia 기반 조류 정보 자동 수집
- 📊 HTML/Word 시각적 리포트 생성
- 🖼️ 정사각형 썸네일 및 원본 이미지 팝업
- 🔄 실시간 파일명 미리보기
- 📝 CSV 전처리기로 영명 사전 보완
- 💾 안전한 프로세스 종료 및 리소스 관리

## 🤝 기여하기

1. 이 저장소를 포크하세요
2. 새 기능 브랜치를 만드세요 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋하세요 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시하세요 (`git push origin feature/amazing-feature`)
5. Pull Request를 열어주세요

## 🐛 문제 신고

버그나 기능 요청은 [Issues](../../issues) 페이지에서 신고해 주세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

## 🙏 감사의 말

- **새와생명의터**: 조류목록 데이터 제공
- **Wikipedia**: 조류 정보 및 다국어 연동
- **CustomTkinter**: 아름다운 GUI 프레임워크

## 📞 연락처

- 문의사항: [이메일](mailto:developer@example.com)
- 프로젝트 링크: [GitHub](https://github.com/username/bird-photo-editor)

---

**🐦 즐거운 탐조 기록 정리되세요! 🐦**