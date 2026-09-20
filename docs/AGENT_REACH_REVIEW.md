# Agent Reach 적용 검토

## 결론

Agent Reach는 VMAX의 상용 수집 런타임에 **직접 통합하지 않는다.** 소스 추가 실험을 빠르게 해 보는 로컬 관리자 도구로는 유용하지만, 현재 VMAX가 필요로 하는 서버 형 안정 API·약관 준수·재현 가능한 구조화 출력을 제공하지 않는다.

## 확인한 사항

- 저장소는 MIT 라이선스이며 현재 Python 패키지가 Beta로 표시된다.
- 자체 수집 API가 아니라 플랫폼별 상위 도구를 설치·진단·선택하는 capability layer이다.
- 일부 경로는 CLI, 로컬 브라우저, 쿠키 또는 로그인 세션을 필요로 한다.
- 프로젝트 문서 자체가 쿠키 방식의 계정 제한·탈취 위험을 고지한다.
- 상위 도구와 플랫폼 방어 정책이 바뀌면 실제 수집 결과가 달라질 수 있다.

근거: [Agent Reach 저장소](https://github.com/Panniantong/Agent-Reach), [영문 설명서](https://github.com/Panniantong/Agent-Reach/blob/main/docs/README_en.md), [MIT 라이선스](https://github.com/Panniantong/Agent-Reach/blob/main/LICENSE), [패키지 메타데이터](https://github.com/Panniantong/Agent-Reach/blob/main/pyproject.toml)

## VMAX에 직접 붙이지 않는 이유

1. VMAX는 Cloudflare Workers 웹 런타임이지만 Agent Reach는 Python·외부 CLI·로컬 세션 실행 환경을 가정한다.
2. 플랫폼별 로그인 쿠키를 배포 서버에 보관하는 구조는 VMAX의 현재 Secret 관리·다중 사용자 격리와 맞지 않다.
3. 무료인 것과 상용 서비스에서 재배포·자동 수집이 허용되는 것은 다른 문제다. 각 플랫폼의 약관·API 정책·저작권·삭제 요청을 별도로 확인해야 한다.
4. 상위 CLI의 출력 포맷과 성공 조건이 동일하지 않아 VMAX의 필수 필드, 원문 URL, 게시 시각, 작성자 근거를 안정적으로 보장하지 못한다.

## 향후 제한적 실험 조건

Agent Reach를 실험하려면 배포 웹앱과 분리된 로컬/배치 worker에서만 실행한다. 로그인 우회, CAPTCHA 우회, 유료벽 우회, 비공개 피드 수집은 허용하지 않는다. 결과는 바로 D1에 넣지 않고 다음 검증을 통과한 JSONL만 기존 `pipeline/index_corpus.py` 경로로 반입한다.

- 승인된 출처와 수집 목적
- 공개 HTTPS 원문 URL
- 표준 시간대가 포함된 게시 시각
- 원문 제목·본문 대조
- 중복·삭제·보존 정책
- 플랫폼별 이용조건 검토 기록

즉, Agent Reach의 “우선 백엔드 + 대체 백엔드 + 건강 검사” 아이디어는 참고할 수 있지만, 현재 코드와 쿠키 기반 수집 경로를 VMAX 운영 런타임에 그대로 넣지 않는 것이 안전하다.
