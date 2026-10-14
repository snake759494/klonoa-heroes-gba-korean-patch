# 검증 범위

- validation/compact_hooks.log: ARM 훅·버퍼·BPE·포인터·효과 배열 등 74개 통과.
- validation/layout_final.log: 시나리오 263개, 22셀×3줄, 넘침·제어 경고 0.
- validation/native_graphics_applied.json: 추가 네이티브 이미지 패치 171개. 전체 게임 이미지 개수나 실제 플레이 검사 수가 아닙니다.
- release_manifest.json: 파일·폰트 해시와 확인 범위.

현재 빌드: 백그라운드 VBA 새 부팅 타이틀. 이전 C9746464… 빌드: 맵/메뉴/저장/첫 비전/전투. 이전 711FDAB1… 빌드: 새 게임/대화/옵션. 다른 빌드의 화면을 같은 빌드의 증거로 합산하지 않습니다.

엔딩은 원본 ARM BPE 해제, 타일 범위, 한글 마스크, 문구 밖 픽셀 보존을 검사했습니다. 전체 완주·실제 엔딩 도달·모든 상점/캐릭터/이벤트·실기는 미검증입니다.
