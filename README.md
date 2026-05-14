# handwrite2350

Docker 기반 손글씨 폰트 엔진 프로젝트입니다.

14장의 손글씨 표 이미지를 입력받아 Basic Latin 94 glyphs와 KS X 1001 Hangul 2,350 glyphs, 총 2,444자의 TTF 폰트를 생성합니다.

## Pipeline

최종 파이프라인은 품질, 속도, 안정성의 균형을 기준으로 구성되어 있습니다.

1. 원본 입력 이미지는 JPG/PNG 등 일반 이미지 형식을 허용합니다.
2. 4개 마커를 검출하고 원근 보정을 수행합니다.
3. 원근 보정 결과를 큰 PNG 이미지로 저장합니다: `4960 x 7016`.
4. 원근 보정된 grayscale page에서 11열 x 17행 셀을 crop합니다.
5. 각 glyph 셀에서 threshold는 bbox 탐지에만 사용합니다.
6. grayscale crop을 기본 `512 x 512` 흰색 캔버스에 비율 유지하여 정규화합니다.
7. resize 이후 마지막 단계에서 binary화합니다.
8. 최종 binary bitmap을 raw PBM으로 만들어 Potrace stdin에 전달하고 SVG stdout을 저장합니다.
9. Potrace SVG 생성은 glyph 단위로 병렬 처리합니다.
10. FontForge는 마지막에 단일 프로세스로 SVG를 TTF에 등록합니다.

중간 처리용 이미지는 PNG/PBM 기반으로 처리합니다. Contact sheet는 검수용이며 파이프라인 입력으로 사용하지 않습니다.

품질 메모: 계단현상은 너무 이른 binary화 이후 crop/resize를 수행하면 생길 수 있습니다. 현재 기본 구조는 page 전체를 먼저 binary화하지 않고 grayscale cell을 crop한 뒤 resize하고, 마지막에만 threshold해서 Potrace stdin으로 전달합니다.

Punctuation 메모: 온점, 쉼표, 따옴표 등 Basic Latin punctuation은 bbox를 캔버스에 꽉 채우지 않습니다. 셀 전체 기준으로 정규화해서 사용자가 쓴 상대 크기와 위치를 보존하고, FontForge 단계에서도 punctuation bbox 확대를 건너뜁니다.

FontForge 메모: 기본 TTF 생성은 `--font-quality fast`입니다. Fast mode는 `importOutlines`, width 설정, 필요한 bbox fit만 수행해서 전체 실행 시간을 줄입니다. `--font-quality high`를 사용하면 `correctDirection()`, `removeOverlap()`, 더 강한 bbox 보정을 수행하므로 품질 확인용으로 적합하지만 시간이 더 오래 걸릴 수 있습니다.

## Outputs

- 환경 체크: `outputs/env_check.txt`
- font metadata preview: `outputs/font_info_preview.txt`
- 매핑 샘플: `outputs/mapping_sample.txt`
- 원근 보정 이미지: `outputs/warped/page01.png`
- 마커 디버그 이미지: `outputs/debug/page01_markers.jpg`
- 셀 이미지: `outputs/cells/page01/r00_c00.png`
- contact sheet: `outputs/contact_sheets/page01_contact.jpg`
- 정규화 glyph debug 이미지: `outputs/normalized/uniXXXX.png`
- SVG glyph: `outputs/svg/uniXXXX.svg`
- SVG tracing 리포트: `outputs/trace_report.txt`
- TTF 폰트: `outputs/fonts/{postscript_name}.ttf`
- TTF 생성 리포트: `outputs/font_build_report.txt`
- 성능 리포트: `outputs/performance_report.txt`

검수용 debug marker, contact sheet, cell PNG, normalized glyph PNG는 기본 실행에서 저장하지 않습니다. 기본 서비스 흐름은 원근 보정된 grayscale page를 메모리로 넘기고, 동시에 검수용 warped PNG는 낮은 압축률로 저장합니다. 이후 cell split은 warped PNG를 다시 읽지 않고 메모리의 grayscale page에서 cell crop을 만들어 tracing으로 넘기는 direct trace mode입니다. `--save-debug-artifacts` 또는 `--save-normalized` 옵션을 사용할 때만 검수용 파일을 생성/갱신합니다.

## Font Metadata

사용자는 `family_name`과 `designer`만 입력합니다. 나머지 값은 코드에서 자동 생성합니다.

입력 우선순위:

1. CLI 옵션 `--family-name`, `--designer`
2. `--interactive` 입력
3. `config/font_info.json`
4. 기본값

기본값:

- `family_name`: `Handwrite2350`
- `designer`: 빈 문자열

## Docker Build

```bash
docker build -t handwrite2350 .
```

## Docker Run

Windows PowerShell:

```powershell
docker run --rm -v "${PWD}/samples:/app/samples" -v "${PWD}/outputs:/app/outputs" handwrite2350
```

macOS/Linux:

```bash
docker run --rm -v "$(pwd)/samples:/app/samples" -v "$(pwd)/outputs:/app/outputs" handwrite2350
```

Interactive metadata 입력:

```bash
docker run --rm -it -v "$(pwd)/samples:/app/samples" -v "$(pwd)/outputs:/app/outputs" handwrite2350 --interactive
```

Worker 수 지정:

```bash
docker run --rm -v "$(pwd)/samples:/app/samples" -v "$(pwd)/outputs:/app/outputs" handwrite2350 --workers 8
```

## Options

- `--family-name`: 폰트 family name 지정
- `--designer`: designer 이름 지정
- `--interactive`: 터미널에서 metadata 입력
- `--workers`: page preprocess와 Potrace 병렬 처리 worker 수 지정
- `--glyph-size`: glyph 정규화 canvas 크기, 기본 `512`
- `--glyph-padding`: glyph 정규화 padding, 기본 `48`
- `--font-quality`: FontForge cleanup 모드, `fast` 또는 `high`, 기본 `fast`
- `--save-normalized`: `outputs/normalized/uniXXXX.png` 저장
- `--save-debug-artifacts`: marker debug 이미지, cell PNG, contact sheet 저장
- `--cell-margin`: 셀 crop margin 비율, 기본 `0.08`

정규화 glyph를 확인하며 전체 파이프라인을 실행하는 예시:

```bash
docker run --rm -v "$(pwd)/samples:/app/samples" -v "$(pwd)/outputs:/app/outputs" handwrite2350 --glyph-size 512 --glyph-padding 48 --workers 8 --save-normalized
```

## Reports

SVG 변환 결과는 `outputs/trace_report.txt`에서 확인합니다. 여기에는 glyph 수, 성공/실패 수, worker 수, glyph size, padding, normalized 저장 여부, direct trace mode, elapsed time, 실패 glyph 목록이 기록됩니다.

TTF 생성 결과는 `outputs/font_build_report.txt`에서 확인합니다. 여기에는 charset 수, import된 SVG 수, 누락 SVG 수, 생성된 TTF 경로, font quality, create font time, import SVG total time, glyph cleanup time, metadata time, generate TTF time, 실패 glyph 목록이 기록됩니다.

전체 실행 성능은 `outputs/performance_report.txt`에서 확인합니다. 여기에는 preprocessing, cell split, trace, font build, total time, cell PNG saving, direct trace mode, page binary mode, in-memory warped input이 기록됩니다.

## Fast Mode

`--fast` keeps the same font-generation pipeline, but skips review/debug work that is not required to build the TTF.

Fast mode changes:

- skips writing `outputs/warped/*.png`; warped pages are still passed in memory
- uses `--warp-interpolation linear` unless `--warp-interpolation cubic` is explicitly set
- skips the detailed glyph metrics CSV
- skips font info preview and charset mapping sample output
- keeps fatal checks for input images, marker detection, charset/cell mismatch, Potrace, SVG output, FontForge, and TTF generation

Windows PowerShell:

```powershell
docker run --rm `
  -v "${PWD}/samples:/app/samples" `
  -v "${PWD}/outputs:/app/outputs" `
  -v "${PWD}/charsets:/app/charsets" `
  -v "${PWD}/config:/app/config" `
  handwrite2350 --fast --workers 8 --family-name "test-fast" --designer "ccomet"
```

`outputs/performance_report.txt` records `fast mode`, `save warped PNG`, `warp interpolation`, `trace metrics`, preprocessing time, trace time, font build time, and total time so normal and fast runs can be compared.

## Adaptive Glyph Layout

The default layout mode is `fixed`, which keeps the existing `trace_glyphs.py` layout behavior for compatibility.

`--layout-mode adaptive` enables the experimental adaptive glyph layout system. It measures each glyph ink bbox, classifies glyphs into Latin, Hangul, digit, punctuation, and symbol groups, computes group median statistics, then applies the zone/anchor/scale policy rules from `config/glyph_layout.json`.

`config/glyph_layout.json` is not a per-character coordinate table. It is a tunable rule table for:

- zones and anchors, such as Latin cap/x-height/ascender/descender, Hangul ideographic face, top/bottom/middle punctuation
- group scale policies
- reference groups
- conservative outlier correction limits
- small overrides that map exceptional characters to groups

Basic fast run:

```powershell
docker run --rm `
  -v "${PWD}/samples:/app/samples" `
  -v "${PWD}/outputs:/app/outputs" `
  -v "${PWD}/charsets:/app/charsets" `
  -v "${PWD}/config:/app/config" `
  handwrite2350 --fast --workers 8 --family-name "test-fast" --designer "ccomet"
```

Adaptive layout experiment:

```powershell
docker run --rm `
  -v "${PWD}/samples:/app/samples" `
  -v "${PWD}/outputs:/app/outputs" `
  -v "${PWD}/charsets:/app/charsets" `
  -v "${PWD}/config:/app/config" `
  handwrite2350 --fast --workers 8 --layout-mode adaptive --report-glyph-layout --family-name "test-adaptive" --designer "ccomet"
```

When `--report-glyph-layout` is set, adaptive layout writes `outputs/glyph_layout_report.csv` and `outputs/glyph_layout_summary.txt`. Use these reports to inspect group assignment, zone selection, median dimensions, outliers, and corrections before tuning the JSON numbers by hand.
