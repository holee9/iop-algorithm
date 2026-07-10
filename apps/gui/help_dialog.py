"""Usage help dialog (Help menu) -- explains the 3 tabs and core concepts.

@MX:NOTE: [AUTO] Kept separate from `app.py` so the usage text (which needs
updating independently of widget wiring) doesn't bloat the main wiring
module. Pure content + a small `QDialog` -- no dependency on the rest of
`apps/gui` beyond Qt widgets.
"""

from __future__ import annotations

from qtpy.QtWidgets import QDialog, QPushButton, QTextBrowser, QVBoxLayout, QWidget

HELP_HTML = """
<h2>XDET Verification GUI -- 사용법</h2>
<p>이 앱은 XDET 골든 모델(<code>common/</code>·<code>modules/</code>·<code>pipeline/</code>·
<code>metrics/</code>)을 <b>읽기-실행 전용</b>으로 소비하는 검증 도구입니다. 지표는 항상
<code>metrics/</code> 엔진 호출 결과만 사용하며(GUI 자체 계산 0), <code>data/</code> 폴더에는
절대 쓰지 않습니다.</p>

<h3>1. Module Verifier 탭</h3>
<ol>
<li><b>Open raw...</b>로 16-bit raw + JSON 메타데이터를 로드합니다(<code>resolution</code> 필드 필수).</li>
<li>드롭다운에서 모듈(스테이지) 하나를 선택합니다.</li>
<li>선택한 모듈이 특정 Params를 요구하면(예: offset의 <code>raw_saturation_threshold</code>),
    파라미터 이름 필드에 정확한 키 이름을 입력하고 <b>Add param field</b>를 눌러 입력 칸을 추가한 뒤
    값을 입력합니다(정확한 키 이름은 <code>modules/&lt;stage&gt;.py</code>의 <code>P_*</code> 상수
    주석 참고).</li>
<li><b>Run module</b> 클릭 -- 백그라운드 스레드에서 실행됩니다(진행률 표시, <b>Cancel</b>로
    최선노력 취소 가능).</li>
<li>결과: 입력/출력/차이(diff) 3개 뷰, 마스크 오버레이(체크박스로 종류별 토글, 슬라이더로 공유
    불투명도), W/L(대비) 스핀박스, <b>Blink toggle</b>(전/후 전환), Output 뷰에 마우스를 올리면
    정확한 float32 원본 값 표시, 처리 이력 테이블.</li>
<li><b>Load expected (optional)...</b>로 이전에 내보낸 XFrame을 "정답"으로 불러오면, 다음
    실행부터 상태 표시줄에 <b>[PASS]</b>/<b>[FAIL]</b> 배지가 함께 표시됩니다(run_harness 기반
    fixture 검증).</li>
<li><b>Export output...</b>로 결과를 npz+JSON으로 저장합니다(<code>data/</code> 폴더 하위는
    저장 거부).</li>
</ol>

<h3>2. Pipeline Viewer 탭</h3>
<ol>
<li>Module Verifier와 동일하게 프레임을 로드합니다.</li>
<li>실행할 스테이지를 체크박스로 선택합니다(체크한 순서와 무관하게 항상 CANONICAL_ORDER 순서로
    실행됩니다).</li>
<li><b>Run pipeline</b> 클릭 -- 부분 또는 전체 파이프라인을 실행하고 마지막 스테이지의 전/후를
    표시합니다.</li>
<li>실측 캘리브레이션 데이터가 필요한 스테이지(offset/gain/denoise 등)는 합성 CalibSet만으로는
    끝까지 성공하지 못할 수 있습니다 -- 이는 정상이며, 오류 메시지로 어떤 데이터가 없는지 확인할
    수 있습니다.</li>
</ol>

<h3>3. Metrics 탭</h3>
<ol>
<li><b>Use Module Verifier output</b> 또는 <b>Use Pipeline Viewer output</b>으로 앞서 실행한
    결과를 지표 계산 소스로 불러옵니다.</li>
<li>Pixel pitch(mm)를 확인/수정합니다(기본 0.14mm = 140um CsI 패널 피치).</li>
<li><b>Compute MTF</b>로 전체 프레임에 대한 MTF를 계산합니다(<code>metrics/mtf.py</code> 엔진
    호출 결과만 표시, GUI는 계산하지 않음).</li>
<li>노란색 ROI 사각형을 드래그로 옮기거나 크기를 조절한 뒤 <b>Recompute MTF for ROI</b>를
    클릭하면 같은 경계로 두 번 재계산해 완전히 동일한 결과(bit-identical)인지 확인합니다
    (재현성 round-trip).</li>
</ol>

<h3>핵심 원칙</h3>
<ul>
<li><b>읽기-실행 전용</b>: <code>data/</code> 골든 fixture나 CalibSet 파일에 절대 쓰지 않습니다.
    모든 내보내기는 사용자가 지정한 경로로만 저장됩니다.</li>
<li><b>지표 위임</b>: MTF 등 모든 지표는 <code>metrics/</code> 엔진의 실제 계산 결과만
    표시합니다.</li>
<li><b>단방향 소비</b>: 이 앱은 알고리즘 코드(<code>common/modules/pipeline/metrics</code>)를
    읽기만 하며, 알고리즘 코드는 이 앱을 참조하지 않습니다(import-linter로 강제).</li>
</ul>

<p>자세한 사양: <code>.moai/specs/SPEC-VIEWER-001/</code></p>
"""

ABOUT_TEXT = (
    "XDET Verification GUI\n"
    "SPEC-VIEWER-001 -- apps/gui/ (pyqtgraph + PySide6)\n\n"
    "코어(common/modules/pipeline/metrics)를 단방향으로만 소비하는 읽기-실행 전용 검증 도구입니다.\n"
    "자세한 사양: .moai/specs/SPEC-VIEWER-001/"
)


class HelpDialog(QDialog):
    """Modal usage-help dialog shown from the Help menu ('How to use...')."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("How to use -- XDET Verification GUI")
        self.resize(640, 560)
        self.browser = QTextBrowser(self)
        self.browser.setHtml(HELP_HTML)
        self.browser.setOpenExternalLinks(False)
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.browser)
        layout.addWidget(self.close_button)
