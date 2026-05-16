# Rule-Based Jamo Mask Lab

이 폴더는 메인 Docker 폰트 생성 파이프라인과 분리된 자모 슬롯 mask 초안 생성 실험 공간입니다.

가장 간단한 실행:

```bash
python3 rule_jamo_mask_lab/run_all.py --font_stem font_stem
```

동작 순서:

1. `outputs/normalized/uniXXXX.png`가 있으면 그대로 사용합니다.
2. 없으면 Docker 폰트 파이프라인을 실행해서 `outputs/normalized`를 먼저 만듭니다.
3. `rule_jamo_mask_lab/work/<font_stem>/00_input_glyphs/`에 입력 glyph를 모읍니다.
4. `rule_jamo_mask_lab/work/<font_stem>/01_rgb_masks/`에 학습용 RGB mask 초안을 만듭니다.
5. `02_overlay_previews`, `03_metadata`, `04_extracted_components`, `05_reports`에 검수/디버깅 산출물을 순서대로 저장합니다.

결과 확인:

```bash
open rule_jamo_mask_lab/work/font_stem
cat rule_jamo_mask_lab/work/font_stem/05_reports/summary.tsv | head
```

옵션 예시:

```bash
python3 rule_jamo_mask_lab/run_all.py \
  --font_stem myfont \
  --threshold 180 \
  --min_area 8 \
  --clean \
  --strict
```

Docker로 normalized 생성을 자동 실행하지 않고, 이미 있는 `outputs/normalized`만 쓰려면:

```bash
python3 rule_jamo_mask_lab/run_all.py --font_stem font_stem --no_auto_normalized
```
