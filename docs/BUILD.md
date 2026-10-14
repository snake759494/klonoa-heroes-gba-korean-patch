# 재빌드

Python 3.11 이상과 requirements.txt 패키지가 필요합니다. 원본 ROM을 저장소 최상위에 `Klonoa Heroes - Densetsu no Star Medal (Japan).gba`로 놓고 release_manifest.json의 해시를 확인하세요.

https://github.com/quiple/galmuri 에서 BDF를 받아 work/fonts/에 놓습니다. 필요한 파일: Galmuri7, Galmuri9, Galmuri11, Galmuri11-Bold, Galmuri11-Condensed, Galmuri14 (각 .bdf). 정확한 바이트 재현에는 manifest의 폰트 해시와 같아야 합니다.

work/validation/ 디렉터리를 먼저 생성합니다.

```powershell
python -m pip install -r requirements.txt
python tools/compile_tr.py
python tools/build.py
python tools/audit_runtime.py
python tools/utest.py "Klonoa Heroes - Densetsu no Star Medal (Korean).gba"
```

출력은 work/test.gba와 최상위 Korean ROM입니다. xdelta3는 별도 설치합니다.

```powershell
./xdelta3.exe -e -0 -s "Klonoa Heroes - Densetsu no Star Medal (Japan).gba" "Klonoa Heroes - Densetsu no Star Medal (Korean).gba" Klonoa_Heroes_KR.xdelta
```

공개 소스는 일본어 추출 템플릿 대신 ui_addresses.json의 주소와 번역을 같은 순서로 사용합니다. compile_tr.py는 한국어 모듈만 병합합니다.
