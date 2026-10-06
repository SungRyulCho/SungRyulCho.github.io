# 조성률 포트폴리오

프로젝트의 담당 역할과 문제 해결 경험을 정리한 개인 포트폴리오입니다.

[포트폴리오 바로가기](https://sungryulcho.github.io/)

## 사용 기술

HTML, CSS, JavaScript로 구성하고 GitHub Pages로 배포합니다.

## 로컬 실행

Python 3가 설치된 환경에서 아래 명령을 실행합니다. 별도 빌드나 패키지 설치는 필요 없습니다.

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

[로컬 페이지](http://127.0.0.1:8080)에서 확인할 수 있습니다.

## 검사

페이지 구조와 콘텐츠, 링크 및 정적 자산을 검사합니다.

```sh
python3 tests/check_site.py
```
