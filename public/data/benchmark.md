# ReplayBench benchmark results

Snapshot `2026-11-24-90e589f5b7ff` · 40 archived Runs

Compare scores within the same track, exact Task and input, and matching verifier identity and revision.
An em dash marks unavailable data. Execution status and strict pass are recorded independently.
Adapter errors and self-tests are excluded from public releases. Retained execution failures are not model scores.
Hardware values may include operator-confirmed annotations; see the Run details for field provenance.

## Direct Model

| Run | Model | Quantization | Backend / GPU | Task | Verifier | Execution | Score | Strict pass |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| 20260923T150201Z-b5dd48c619a7 | Qwen3.5-9B | Q8\_0 | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 1.0.0 (4db7d3e5) | structured-evidence-v1 | completed | 0.418813 | No |
| 20260923T161608Z-e845a5873d8e | Qwen3.5-9B | Q8\_0 | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | structured-evidence-v2 2.0.0 | completed | 0.684154 | No |
| 20260923T164144Z-c439115af61d | Ornith-1.5-9B | Q6\_K\_L | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | — | incomplete | — | — |
| 20260923T165616Z-e1cbcbc43c91 | Ornith-1.5-9B | Q6\_K\_L | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | — | timeout | — | — |
| 20260923T172534Z-737c796f192f | Ornith-1.5-9B | Q6\_K\_L | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | structured-evidence-v2 2.0.0 | completed | 0.615657 | No |
| 20260923T181435Z-27e8f6d20d14 | Qwen3.6-35B | Q5\_K\_M | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | structured-evidence-v2 2.0.0 | completed | 0.708018 | No |
| 20260924T123802Z-d3c1fa12c2ee | Qwen3.8-27B | Q4\_K\_M | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | — | timeout | — | — |
| 20260924T125101Z-f6836db93b9f | Qwen3.8-27B | Q4\_K\_M | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | — | timeout | — | — |
| 20260924T134625Z-0a9836132a56 | hauhau-Qwen3.6-35B | Q5\_K\_P | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | structured-evidence-v2 2.0.0 | completed | 0.733523 | No |
| 20260924T135904Z-564b620d5780 | Qwen3.8-27B-ridge | ridge | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | structured-evidence-v2 2.0.0 | completed | 0.798611 | No |
| 20260925T103419Z-7495c704411e | Qwen3.6-35B-A3B-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | structured-evidence-v2 2.0.0 | completed | 0.0 | No |
| 20260925T105016Z-48cf467667dd | Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | structured-evidence-v2 2.0.0 | completed | 0.694129 | No |
| 20260925T110637Z-22ab7e84d815 | Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 2.0.0 (e7dc5435) | structured-evidence-v2 2.0.0 | completed | 0.694129 | No |
| 20260925T123620Z-be0f6feffd7e | Ornith-1.5-35B-A3B-APEX-MTP-I-Quality | APEX-MTP-I-Quality | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | structured-evidence-v3 3.0.0 | completed | 0.693182 | No |
| 20260925T130645Z-05ad5676ba5a | Ornith-1.5-35B-A3B-APEX-MTP-I-Quality | APEX-MTP-I-Quality | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | structured-evidence-v3 3.0.0 | completed | 0.796717 | No |
| 20260925T135410Z-7cb3f3099a23 | Ornith-1.5-35B-A3B-Heretic-MTP-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | structured-evidence-v3 3.0.0 | completed | 0.675 | No |
| 20260925T151348Z-fb9931b08b54 | Occamy-1.0-Q4\_K\_M | Q4\_K\_M | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | structured-evidence-v3 3.0.0 | completed | 0.0 | No |
| 20260925T173611Z-46639aa274cd | hauhau-Qwen3.6-35B | Q5\_K\_P | llama.cpp / RTX 4070 | bilibili-comment-parser-001 0.1.0-candidate (468e24f7) | comment-parser-candidate 0.1.0-candidate | completed | 0.222222 | No |
| 20260926T110054Z-43c1a92e33e2 | Ornith-1.5-35B-A3B-APEX-MTP-I-Quality | APEX-MTP-I-Quality | llama.cpp / RTX 4070 | bilibili-comment-parser-001 0.2.0-candidate (dfb67779) | comment-parser-candidate-v2 0.2.0-candidate | completed | 0.934343 | No |
| 20261116T175519Z-1eba8a394547 | Ornith-1.5-35B-A3B-APEX-MTP-I-Quality | APEX-MTP-I-Quality | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | structured-evidence-v3 3.0.0 | completed | 0.715909 | No |
| 20261116T175927Z-df0496a00b2f | Ornith-1.5-35B-A3B-APEX-MTP-I-Quality | APEX-MTP-I-Quality | llama.cpp / RTX 4070 | bilibili-comment-parser-001 0.2.0-candidate (dfb67779) | — | incomplete | — | — |
| 20261116T180301Z-ce638fce2456 | Ornith-1.5-35B-A3B-APEX-MTP-I-Quality | APEX-MTP-I-Quality | llama.cpp / RTX 4070 | article-review-score-count-001 0.2.0-candidate (18c657f3) | engineering-candidate-v2 0.2.0-candidate | completed | 0.0 | No |
| 20261116T180517Z-ac344fe2963e | Ornith-1.5-35B-A3B-APEX-MTP-I-Quality | APEX-MTP-I-Quality | llama.cpp / RTX 4070 | article-csv-atomic-import-001 0.2.0-candidate (fb641640) | — | incomplete | — | — |
| 20261116T181746Z-87fbd2166b77 | Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | structured-evidence-v3 3.0.0 | completed | 0.662689 | No |
| 20261116T182211Z-7dac11c47b22 | Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | bilibili-comment-parser-001 0.2.0-candidate (dfb67779) | comment-parser-candidate-v2 0.2.0-candidate | completed | 0.279125 | No |
| 20261116T182503Z-caef18f0577b | Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | article-review-score-count-001 0.2.0-candidate (18c657f3) | engineering-candidate-v2 0.2.0-candidate | completed | 1.0 | Yes |
| 20261116T182739Z-d34e1871b468 | Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | article-csv-atomic-import-001 0.2.0-candidate (fb641640) | engineering-candidate-v2 0.2.0-candidate | completed | 0.0 | No |
| 20261116T183021Z-2380825cdf61 | Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q5\_K\_P | Q5\_K\_P | llama.cpp / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | structured-evidence-v3 3.0.0 | completed | 0.663636 | No |
| 20261116T183532Z-60899e756cc5 | Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q5\_K\_P | Q5\_K\_P | llama.cpp / RTX 4070 | bilibili-comment-parser-001 0.2.0-candidate (dfb67779) | comment-parser-candidate-v2 0.2.0-candidate | completed | 0.887205 | No |
| 20261116T183818Z-f22aab1db4c2 | Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q5\_K\_P | Q5\_K\_P | llama.cpp / RTX 4070 | article-review-score-count-001 0.2.0-candidate (18c657f3) | engineering-candidate-v2 0.2.0-candidate | completed | 1.0 | Yes |
| 20261116T184107Z-fa659fe7fca9 | Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q5\_K\_P | Q5\_K\_P | llama.cpp / RTX 4070 | article-csv-atomic-import-001 0.2.0-candidate (fb641640) | engineering-candidate-v2 0.2.0-candidate | completed | 0.74841 | No |
| 20261121T171512Z-823aa46fbd58 | Qwen3.8-Flash-Next-GSQ-RCO q8g | IQ3\_S | Strata / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | — | incomplete | — | — |
| 20261121T172917Z-43422a360c00 | Qwen3.8-Flash-Next-GSQ-RCO q8g | IQ3\_S | Strata / RTX 4070 | homelab-windows-s3-ssh-reset-001 3.0.0 (2ae0265a) | structured-evidence-v3 3.0.0 | completed | 0.863636 | No |

## Pi Agent

| Run | Model | Quantization | Backend / GPU | Task | Verifier | Execution | Score | Strict pass |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| 20261117T151647Z-8e5c4a2e5bf3 | Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q5\_K\_P | Q5\_K\_P | llama.cpp / RTX 4070 | article-review-score-count-001 0.2.0-candidate (18c657f3) | engineering-candidate-v2 0.2.0-candidate | completed | 1.0 | Yes |
| 20261117T152011Z-fce73be7e032 | Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q5\_K\_P | Q5\_K\_P | llama.cpp / RTX 4070 | article-csv-atomic-import-001 0.2.0-candidate (fb641640) | — | output\_limit | — | — |
| 20261118T163047Z-298035fad14f | Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q5\_K\_P | Q5\_K\_P | llama.cpp / RTX 4070 | article-review-score-count-001 0.2.0-candidate (18c657f3) | engineering-candidate-v2 0.2.0-candidate | completed | 1.0 | Yes |
| 20261118T163412Z-1c4c3cd020ff | Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q5\_K\_P | Q5\_K\_P | llama.cpp / RTX 4070 | article-csv-atomic-import-001 0.2.0-candidate (fb641640) | engineering-candidate-v2 0.2.0-candidate | completed | 0.958923 | No |
| 20261118T163826Z-63c6075406cd | Ornith-1.5-35B-A3B-APEX-MTP-I-Quality | APEX-MTP-I-Quality | llama.cpp / RTX 4070 | article-csv-atomic-import-001 0.2.0-candidate (fb641640) | — | output\_limit | — | — |
| 20261118T164401Z-a59526ca51a0 | Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | article-review-score-count-001 0.2.0-candidate (18c657f3) | engineering-candidate-v2 0.2.0-candidate | completed | 1.0 | Yes |
| 20261118T164601Z-ef5a2c131fb9 | Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-APEX-I-Quality | APEX-I-Quality | llama.cpp / RTX 4070 | article-csv-atomic-import-001 0.2.0-candidate (fb641640) | — | output\_limit | — | — |
