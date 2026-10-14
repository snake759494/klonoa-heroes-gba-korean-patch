# 크로노아 히어로즈: 전설의 스타 메달 — GBA 한글패치

일본판 **Klonoa Heroes - Densetsu no Star Medal**용 비공식 한글패치 **v1.0.0 (2026-10-14)**입니다.

[다운로드](https://github.com/snake759494/klonoa-heroes-gba-korean-patch/releases/latest) · [빌드](docs/BUILD.md) · [기술 설명](docs/TECHNICAL.md) · [검증](docs/VALIDATION.md) · [권리 안내](RIGHTS.md)

## 적용 방법

1. 직접 준비한 일본판 ROM의 SHA-256을 아래 값과 비교합니다.
2. 릴리즈에서 `Klonoa_Heroes_KR.xdelta`를 받습니다.
3. xdelta UI의 Apply Patch에서 패치, 원본 ROM, 새 출력 파일을 지정합니다.
4. 결과를 새로 부팅합니다. 이전 세이브 스테이트에는 옛 코드와 그래픽이 남을 수 있습니다.

```powershell
Get-FileHash -Algorithm SHA256 "Klonoa Heroes - Densetsu no Star Medal (Japan).gba"
./xdelta3.exe -d -s "Klonoa Heroes - Densetsu no Star Medal (Japan).gba" Klonoa_Heroes_KR.xdelta "Klonoa Heroes - Densetsu no Star Medal (Korean).gba"
```

| 파일 | 바이트 | SHA-256 |
| --- | ---: | --- |
| 원본 | 16,777,216 | `cb3ff23fc56440efa97321a2cb93a87aacf05ae4214527972af3ce0f29834e63` |
| 결과 | 33,554,432 | `149bdff2e8a97204f5bb0f63543a9326696f5f12003b69ca60c02f875c2ff03d` |
| xdelta | 202,803 | `a24131670e05c518a8ddfe278eb8c834448cbb635d8d453455ed5d9a2e5e362e` |

릴리즈에는 xdelta `-0`으로 만든 패치만 첨부합니다. ROM, 추출된 게임 리소스, 폰트 원본, 외부 실행 파일은 배포하지 않습니다.

## 한글화 내용

- 직접 번역한 시나리오·메뉴·시스템·도감·튜토리얼.
- 타이틀·화자명·지역명·집 간판·전투 효과·메뉴 하단·START 안내·엔딩 이미지.
- 본문 갈무리11 Condensed의 원래 7×11 픽셀, 8픽셀 간격. 작은 안내 갈무리7, 엔딩 갈무리14. 확대·축소 없음.
- 페이지 초기화와 메뉴 소스 포인터 수정으로 겹침과 둘째 줄 원문 잔류 교정.

번역 자료에는 **전개 스포일러**가 있습니다. 일부 사전에는 런타임 문자열을 식별하는 원문 키가 포함됩니다. 원문 대사 추출본 전체는 배포하지 않습니다.

## 검증과 한계

자동 검사 74개 통과, 실패 0. 시나리오 263개 정적 배치에서 넘침과 제어 경고 0. xdelta 복원 결과가 수정 ROM과 일치합니다.

현재 빌드는 백그라운드 VBA 새 부팅으로 타이틀을 확인했습니다. 앞선 빌드에서는 맵·메뉴·저장·오프닝·NPC 대화·첫 비전 대사와 전투를 확인했습니다. 엔딩 두 장은 원본 게임 압축 해제 함수와 픽셀 검사로 검증했습니다.

**전체 완주, 실제 엔딩 도달, 모든 상점·캐릭터·이벤트, 실기 구동은 미검증입니다.** 정식 릴리즈가 전 장면 검증을 뜻하지 않습니다. 문제 제보에는 재현 순서, ROM 해시, 스크린샷을 첨부해 주세요.
