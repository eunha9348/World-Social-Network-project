# 검증된 수집 가능 호스트

측정: 2026-09-20 · `Probe sources` 워크플로 실행 결과 · 후보 60개 중 **54개 도달 가능**

이 목록은 추정이 아니라 실제 응답을 확인한 값이다. 인스턴스는 공개 타임라인을 닫거나
이전하거나 사라지므로 **주기적으로 다시 확인한다.** 목록을 그대로 믿지 말고 프로브를 다시 돌린다.

## 바로 붙여 쓰는 값

Ingest corpus의 `hosts` 칸에 붙여 넣는다.

**mastodon** (15개)
```
mstdn.jp,mastodon.world,mas.to,fosstodon.org,mastodon.uno,troet.cafe,piaille.fr,ruhr.social,mastodon.gamedev.place,planet.moe,qdon.space,twingyeo.kr,uri.life,pawoo.net,social.vivaldi.net
```

**lemmy** (9개)
```
lemmy.world,sh.itjust.works,feddit.it,jlai.lu,lemmy.ca,lemmy.ml,programming.dev,lemmy.zip,discuss.tchncs.de
```

**stackexchange** (18개)
```
stackoverflow,ja.stackoverflow,ru.stackoverflow,es.stackoverflow,pt.stackoverflow,superuser,serverfault,askubuntu,softwareengineering,workplace,ux,politics,philosophy,skeptics,worldbuilding,money,travel,cooking
```

**discourse** (12개)
```
meta.discourse.org,discuss.python.org,forum.djangoproject.com,users.rust-lang.org,discourse.mozilla.org,forum.obsidian.md,discuss.pytorch.org,forums.swift.org,discuss.elastic.co,community.letsencrypt.org,forum.ghost.org,discourse.nixos.org
```

## 언어 분포

프로브가 각 인스턴스에서 5건만 표본으로 확인한 값이다. 전체 분포가 아니라 **존재 확인**이다.

| 언어 | 확인된 호스트 |
|---|---|
| 한국어 `ko` | **planet.moe, twingyeo.kr, qdon.space, uri.life** — 아래 실측 참고 |
| 일본어 `ja` | mstdn.jp, pawoo.net, planet.moe, qdon.space, uri.life, ja.stackoverflow |
| 독일어 `de` | troet.cafe, ruhr.social, discuss.tchncs.de, mastodon.world, mas.to |
| 프랑스어 `fr` | piaille.fr, jlai.lu |
| 이탈리아어 `it` | mastodon.uno, feddit.it |
| 스페인어 `es` | es.stackoverflow |
| 포르투갈어 `pt` | pt.stackoverflow |
| 러시아어 `ru` | ru.stackoverflow |
| 중국어 `zh-TW` | mstdn.jp, uri.life (표본에 출현) |
| 아랍어 `ar` | mastodon.uno (표본에 출현) |

### 한국어 실측 (2026-09-20)

네 인스턴스를 `languages=ko`로 실제 수집한 결과다.

```
hosts: planet.moe,twingyeo.kr,qdon.space,uri.life
{"collected": 50, "skipped": 338, "per_language": {"ko": 50}, "unreachable": []}
```

- 요청한 50건을 **전부 한국어로 채웠다.** 상한에 걸려 멈춘 것이므로 가용량은 더 크다.
- `unreachable`이 비어 있다. 프로브의 5건 표본에서 `ko`가 안 보였던 qdon.space와 uri.life도
  실제로는 한국어를 낸다. **표본이 조용했던 것이지 한국어가 없던 것이 아니다.**
- 388건을 훑어 50건을 남겼으므로 한국어 비율은 약 13%다. 수집 단계 필터라 모델 비용은 들지 않는다.
- 색인 dry-run에서 20건 처리·거부 0건. 한국어 본문이 `normalize()`를 통과한다.

한국어는 이 경로로 확보 가능하다는 것이 확인되었다.

## 도달 실패 6개

| 호스트 | 응답 | 조치 |
|---|---|---|
| mastodon.social | HTTP 422 | `local=true` 재시도를 추가했다. 다음 프로브에서 재확인 |
| best-friends.chat | HTTP 422 | 동일 |
| feddit.de | HTTP 404 | Lemmy 1.x의 `/api/v4` 재시도를 추가했다. 다음 프로브에서 재확인 |
| mastodon.kr | URLError | 도메인이 응답하지 않는다. 후보에서 제외 |
| lemm.ee | JSONDecodeError | JSON 대신 HTML 응답. 서비스 종료로 보인다 |
| feddit.uk | RemoteDisconnected | 연결이 끊긴다. 나중에 재확인 |

## 주의

- Stack Exchange 무인증 quota는 하루 300회다. 프로브 한 번에 18회를 쓴다.
  대량 수집에는 앱 키를 발급해 `--key`로 넘긴다.
- Discourse 수집기는 주제마다 요청을 한 번 더 보낸다. `collect_limit`을 크게 잡지 않는다.
- 이 호스트들은 **공개 API로 공개 게시물만** 읽는다. 로그인 우회나 비공개 피드 수집은 하지 않는다.
