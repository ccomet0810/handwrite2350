# handwrite2350

Docker 기반 손글씨 폰트 엔진 프로젝트입니다.

최종 목표는 손글씨로 작성한 14장의 표 이미지를 입력받아 TTF 폰트를 생성하는 것입니다. 대상 문자는 Basic Latin 94 glyphs와 KS X 1001 Hangul 2,350 glyphs입니다.

현재 단계는 실제 이미지 처리, 마커 검출, 원근 보정, 칸 분리, 벡터화, TTF 생성 로직을 구현하기 전의 Docker 실행환경 검증 단계입니다. 컨테이너 안에서 Python 패키지와 외부 도구인 FontForge, Potrace가 정상 실행되는지만 확인합니다.

FontForge는 폰트 조립 도구이고, Potrace는 이미지 윤곽선을 SVG로 벡터화하는 외부 도구입니다. Windows용 FontForgeBuilds.zip은 사용하지 않고, Linux Docker 이미지 안에서 `fontforge`와 `potrace`를 각각 설치합니다.

## Docker Build

```bash
docker build -t handwrite2350 .
```

## Docker Run

실행 결과는 `outputs/env_check.txt`에 저장됩니다.

### Windows PowerShell

```powershell
docker run --rm -v "${PWD}/samples:/app/samples" -v "${PWD}/outputs:/app/outputs" handwrite2350
```

### macOS/Linux

```bash
docker run --rm -v "$(pwd)/samples:/app/samples" -v "$(pwd)/outputs:/app/outputs" handwrite2350
```
