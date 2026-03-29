# S&P500 Top10 포트폴리오 트래커

컴퓨터를 꺼도 24시간 돌아가는 자동 포트폴리오 모니터링 시스템.
GitHub Actions가 매달 자동으로 데이터를 수집하고, GitHub Pages로 대시보드를 제공합니다.

## 기능

- **매월 자동 실행**: GitHub Actions가 매달 말 시총 순위를 자동으로 가져옴
- **이탈 카운터**: 3개월 연속 Top10 이탈 시에만 매도 신호 생성
- **계층 가중치**: 1~3위 1.5×, 4~7위 1.0×, 8~10위 0.7× 자동 배분 계산
- **매매 신호**: SELL_33 / WATCH / NEW_BUY / REENTRY 신호 자동 분류
- **체크리스트**: 월간/분기 할 일 체크리스트 (브라우저 로컬 저장)
- **완전 무료**: GitHub Free 플랜으로 충분

---

## 설치 방법 (5단계, 10분 소요)

### 1단계 — GitHub 계정 만들기
https://github.com 에서 무료 계정 가입 (이미 있으면 건너뜀)

### 2단계 — 이 폴더를 GitHub에 업로드
1. https://github.com/new 에서 새 저장소 생성
   - Repository name: `portfolio-tracker` (영문)
   - Public 선택 (GitHub Pages 무료 사용)
   - Create repository 클릭

2. 이 `portfolio-tracker` 폴더 전체를 업로드:
   - "uploading an existing file" 링크 클릭
   - 폴더 전체 드래그 앤 드롭
   - Commit changes 클릭

### 3단계 — GitHub Pages 활성화
1. 저장소 → Settings → Pages
2. Source: **GitHub Actions** 선택
3. Save

### 4단계 — 첫 배포 실행
1. 저장소 → Actions 탭
2. **Deploy to GitHub Pages** 워크플로 클릭
3. **Run workflow** → Run workflow

### 5단계 — 대시보드 접속
배포 완료 후 (약 2분):
```
https://[내 GitHub 아이디].github.io/portfolio-tracker/
```

---

## 자동 실행 스케줄

| 작업 | 시기 | 방식 |
|------|------|------|
| 시총 데이터 수집 | 매월 28~31일 09:00 UTC | GitHub Actions |
| 이탈 카운터 업데이트 | 위와 동일 | 자동 |
| 대시보드 갱신 | 데이터 수집 완료 후 | 자동 배포 |

수동으로 즉시 실행하려면: Actions → Monthly Portfolio Update → Run workflow

---

## 월 투자금 변경

대시보드 상단의 "월 투자금 설정"에서 직접 입력.
브라우저에 저장됩니다 (기기마다 별도 설정).

---

## 매매 신호 종류

| 신호 | 의미 | 행동 |
|------|------|------|
| `NEW_BUY` | 신규 Top10 편입 | 이번 달부터 배분표대로 매수 시작 |
| `WATCH` (1~2개월) | 이탈 초기 | 아직 매도 없음, 관찰 |
| `SELL_33` | 3개월 연속 이탈 | 보유 잔량의 33% 매도 (증권사 앱) |
| `REENTRY` | 이탈 후 Top10 복귀 | 매도 중단, 다음 달부터 매수 재개 |

---

## 파일 구조

```
portfolio-tracker/
├── index.html              # 대시보드 웹 앱
├── data/
│   ├── latest.json         # 최신 데이터 (Actions가 자동 갱신)
│   └── state.json          # 이탈 카운터, 히스토리
├── src/
│   └── fetch_data.py       # 데이터 수집 스크립트
└── .github/workflows/
    ├── monthly-update.yml  # 매월 자동 데이터 수집
    └── deploy-pages.yml    # GitHub Pages 자동 배포
```

---

## 주의사항

- 이 시스템은 **매매 신호 생성 전용**입니다. 실제 주문은 직접 증권사 앱에서 실행하세요.
- 데이터는 Yahoo Finance 무료 API를 사용합니다. 지연이 있을 수 있습니다.
- 투자 결정은 본인 판단으로 내리세요. 이 도구는 정보 제공 목적입니다.
