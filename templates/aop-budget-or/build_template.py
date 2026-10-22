"""Sinh file Excel template AOP - Budget - OR (Outlook Revision).

Chạy:  python build_template.py [output.xlsx]
Sau khi sinh, mở bằng Excel (hoặc chạy recalc LibreOffice) để tính lại công thức.

Bước 1 sinh toàn bộ công thức + dữ liệu mẫu đầu vào.
Bước 2 (tùy chọn, cần LibreOffice) đọc kết quả Budget để điền số liệu mẫu
cho Thực tế 6 tháng, TH năm trước và mục tiêu AOP.
"""
import random
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

FONT = "Arial"
NUM = '#,##0;(#,##0);"-"'
NUM1 = '#,##0.0;(#,##0.0);"-"'
PCT = '0.0%;(0.0%);"-"'
MONTH_FMT = '"T"0'

F_BASE = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_INPUT = Font(name=FONT, size=10, color="0000FF")
F_LINK = Font(name=FONT, size=10, color="008000")
F_HEAD = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_TITLE = Font(name=FONT, size=14, bold=True, color="1F4E78")
F_NOTE = Font(name=FONT, size=9, italic=True, color="595959")

FILL_HEAD = PatternFill("solid", fgColor="1F4E78")
FILL_SEC = PatternFill("solid", fgColor="DDEBF7")
FILL_KEY = PatternFill("solid", fgColor="FFFF00")
FILL_TOTAL = PatternFill("solid", fgColor="F2F2F2")
THIN = Side(style="thin", color="A6A6A6")
B_TOP = Border(top=THIN)
B_ALL = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

# Cột tháng: sheet chi tiết dùng G..R, sheet P&L dùng D..O
def mc(i):  # sheet chi tiết
    return get_column_letter(6 + i)


def mp(i):  # sheet P&L
    return get_column_letter(3 + i)


MONTHS = range(1, 13)

SKUS = ["Sữa tươi tiệt trùng", "Sữa tươi thanh trùng", "Sữa chua", "Sữa hạt", "Nước giải khát"]
CHANNELS = ["Kênh truyền thống (GT)", "Kênh hiện đại (MT)", "Chuỗi cửa hàng & Online"]
DEPTS = ["Ban Tổng Giám đốc", "Bán hàng", "Marketing", "Chuỗi cửa hàng", "Kế toán - Tài chính",
         "Hành chính - Nhân sự", "Công nghệ thông tin", "R&D - Chất lượng", "Chuỗi cung ứng"]
PL_GROUPS = ["Bán hàng & Marketing", "Quản lý doanh nghiệp"]
ALLOC = ["Đều", "Mùa vụ"]
SEASON = [0.080, 0.070, 0.075, 0.082, 0.090, 0.092, 0.090, 0.088, 0.082, 0.080, 0.081, 0.090]

# Dữ liệu mẫu doanh thu: (sản lượng năm tấn, giá gộp tr/tấn, %CK) theo SKU x kênh
SALES_SAMPLE = {
    "Sữa tươi tiệt trùng": [(180000, 30.0, 0.08), (90000, 30.0, 0.12), (30000, 31.0, 0.03)],
    "Sữa tươi thanh trùng": [(15000, 38.0, 0.08), (12000, 38.0, 0.12), (8000, 39.0, 0.03)],
    "Sữa chua": [(40000, 45.0, 0.08), (25000, 45.0, 0.12), (10000, 46.0, 0.03)],
    "Sữa hạt": [(12000, 55.0, 0.08), (9000, 55.0, 0.12), (4000, 56.0, 0.03)],
    "Nước giải khát": [(60000, 12.0, 0.10), (30000, 12.0, 0.14), (10000, 12.5, 0.03)],
}
# Giá thành đơn vị mẫu (tr/tấn): sữa NL, bao bì, NVL khác, chi phí chuyển đổi (gồm NC sản xuất)
COST_SAMPLE = {
    "Sữa tươi tiệt trùng": (9.0, 4.0, 1.0, 2.5),
    "Sữa tươi thanh trùng": (11.0, 4.5, 1.0, 3.5),
    "Sữa chua": (12.0, 6.0, 3.0, 4.0),
    "Sữa hạt": (0.0, 7.0, 15.0, 5.0),
    "Nước giải khát": (0.0, 3.0, 2.0, 1.5),
}
OPEX_SAMPLE = [
    ("Marketing", "Quảng cáo & truyền thông", "Bán hàng & Marketing", 600000, "Mùa vụ"),
    ("Bán hàng", "Trade marketing & khuyến mại", "Bán hàng & Marketing", 450000, "Mùa vụ"),
    ("Chuỗi cung ứng", "Vận chuyển & logistics bán hàng", "Bán hàng & Marketing", 400000, "Mùa vụ"),
    ("Chuỗi cửa hàng", "Thuê mặt bằng cửa hàng", "Bán hàng & Marketing", 150000, "Đều"),
    ("Hành chính - Nhân sự", "Thuê văn phòng", "Quản lý doanh nghiệp", 30000, "Đều"),
    ("Công nghệ thông tin", "Bản quyền phần mềm & hạ tầng IT", "Quản lý doanh nghiệp", 40000, "Đều"),
    ("Kế toán - Tài chính", "Kiểm toán, tư vấn thuế", "Quản lý doanh nghiệp", 15000, "Đều"),
    ("Hành chính - Nhân sự", "Điện, nước văn phòng", "Quản lý doanh nghiệp", 10000, "Đều"),
    ("Ban Tổng Giám đốc", "Công tác phí", "Quản lý doanh nghiệp", 12000, "Đều"),
    ("R&D - Chất lượng", "Kiểm nghiệm & phát triển sản phẩm", "Quản lý doanh nghiệp", 20000, "Đều"),
]
# (BP, headcount, lương bq tr/người/tháng)
HC_SAMPLE = [
    ("Ban Tổng Giám đốc", 10, 150), ("Bán hàng", 2500, 15), ("Marketing", 120, 25),
    ("Chuỗi cửa hàng", 1500, 10), ("Kế toán - Tài chính", 80, 22),
    ("Hành chính - Nhân sự", 60, 20), ("Công nghệ thông tin", 50, 30),
    ("R&D - Chất lượng", 40, 28), ("Chuỗi cung ứng", 200, 16),
]
CAPEX_SAMPLE = [
    ("Mở rộng dây chuyền tiệt trùng", "Chuỗi cung ứng", 350000, 4, 10),
    ("Hệ thống kho lạnh miền Nam", "Chuỗi cung ứng", 120000, 7, 15),
    ("Mở mới 50 cửa hàng", "Chuỗi cửa hàng", 60000, 3, 5),
    ("Nâng cấp ERP & BI", "Công nghệ thông tin", 25000, 9, 5),
]

# Các dòng P&L dùng chung cho BG_PL, ThucTe, OR_DuBao (cùng vị trí dòng)
PL_LINES = [
    ("dt_gop", "Doanh thu bán hàng gộp", "in"),
    ("ck", "Chiết khấu thương mại", "in"),
    ("dt_thuan", "Doanh thu thuần", "calc"),
    ("gv", "Giá vốn hàng bán", "in"),
    ("lng", "Lợi nhuận gộp", "calc"),
    ("gm", "  Biên lợi nhuận gộp (%)", "pct"),
    ("bh", "Chi phí bán hàng & marketing", "in"),
    ("ql", "Chi phí quản lý doanh nghiệp", "in"),
    ("ns", "Chi phí nhân sự (khối VP & bán hàng)", "in"),
    ("ebitda", "EBITDA", "calc"),
    ("ebitda_pct", "  Biên EBITDA (%)", "pct"),
    ("kh", "Khấu hao TSCĐ", "in"),
    ("ebit", "EBIT", "calc"),
    ("tc", "Doanh thu / (chi phí) tài chính thuần", "in"),
    ("khac", "Lợi nhuận khác", "in"),
    ("lntt", "Lợi nhuận trước thuế", "calc"),
    ("thue", "Thuế TNDN", "in"),
    ("lnst", "Lợi nhuận sau thuế", "calc"),
    ("sl", "Ghi nhớ: Sản lượng tiêu thụ (tấn)", "in"),
]
PL_START = 6
R = {k: PL_START + i for i, (k, _, _) in enumerate(PL_LINES)}
BOLD_LINES = {"dt_thuan", "lng", "ebitda", "ebit", "lntt", "lnst"}


def calc_formula(key, c):
    r = R
    return {
        "dt_thuan": f"={c}{r['dt_gop']}+{c}{r['ck']}",
        "lng": f"={c}{r['dt_thuan']}+{c}{r['gv']}",
        "gm": f"=IFERROR({c}{r['lng']}/{c}{r['dt_thuan']},0)",
        "ebitda": f"={c}{r['lng']}+{c}{r['bh']}+{c}{r['ql']}+{c}{r['ns']}",
        "ebitda_pct": f"=IFERROR({c}{r['ebitda']}/{c}{r['dt_thuan']},0)",
        "ebit": f"={c}{r['ebitda']}+{c}{r['kh']}",
        "lntt": f"={c}{r['ebit']}+{c}{r['tc']}+{c}{r['khac']}",
        "lnst": f"={c}{r['lntt']}+{c}{r['thue']}",
    }[key]


def style_cell(cell, font=F_BASE, fmt=None, fill=None, bold=False):
    cell.font = Font(name=FONT, size=10, bold=True, color=font.color) if bold else font
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill


def header_row(ws, row, labels, start_col=1):
    for j, lab in enumerate(labels):
        c = ws.cell(row=row, column=start_col + j, value=lab)
        c.font = F_HEAD
        c.fill = FILL_HEAD
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = B_ALL


def month_header(ws, row, colfn, first_labels, last_label="Cả năm", start_col=1):
    header_row(ws, row, first_labels, start_col)
    for i in MONTHS:
        c = ws[f"{colfn(i)}{row}"]
        c.value = i
        c.number_format = MONTH_FMT
        c.font = F_HEAD
        c.fill = FILL_HEAD
        c.alignment = Alignment(horizontal="center")
        c.border = B_ALL
    c = ws[f"{colfn(13)}{row}"]
    c.value = last_label
    c.font = F_HEAD
    c.fill = FILL_HEAD
    c.alignment = Alignment(horizontal="center")
    c.border = B_ALL


def title(ws, text, sub):
    ws["A1"] = text
    ws["A1"].font = F_TITLE
    ws["A2"] = sub
    ws["A2"].font = F_NOTE
    ws["A3"] = '="Năm kế hoạch: "&GiaDinh!$C$5&"   |   Đơn vị: "&GiaDinh!$C$6&"   |   "&GiaDinh!$C$4'
    ws["A3"].font = F_NOTE


def section(ws, row, text, ncols):
    for j in range(1, ncols + 1):
        ws.cell(row=row, column=j).fill = FILL_SEC
    ws.cell(row=row, column=1, value=text).font = F_BOLD


def total_style(ws, row, ncols):
    for j in range(1, ncols + 1):
        c = ws.cell(row=row, column=j)
        c.font = Font(name=FONT, size=10, bold=True, color=c.font.color if c.font else None)
        c.fill = FILL_TOTAL
        c.border = B_TOP


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def note(ws, ref, text):
    ws[ref].comment = Comment(text, "Template")


# ---------------------------------------------------------------- sheets
def build_hdsd(wb):
    ws = wb.create_sheet("HDSD")
    ws["A1"] = "BỘ TEMPLATE LẬP AOP - BUDGET - OR"
    ws["A1"].font = F_TITLE
    ws["A2"] = "Hướng dẫn sử dụng, quy ước và lịch trình lập kế hoạch tài chính năm"
    ws["A2"].font = F_NOTE
    rows = [
        ("1. ĐỊNH NGHĨA", None),
        ("AOP (Annual Operating Plan)", "Kế hoạch hoạt động năm: mục tiêu top-down do HĐQT/Ban TGĐ giao (doanh thu, lợi nhuận, KPI chiến lược, sáng kiến). Sheet AOP_MucTieu."),
        ("Budget (Ngân sách)", "Ngân sách chi tiết bottom-up do các BP lập theo tháng: doanh thu, giá vốn, chi phí, nhân sự, đầu tư. Sheet BG_*. Phải khớp hoặc giải trình chênh lệch với AOP."),
        ("OR (Outlook Revision / Ước thực hiện)", "Dự báo lại cả năm = Thực tế các tháng đã qua + Dự báo các tháng còn lại. Thường lập quý: OR1 (3+9), OR2 (6+6), OR3 (9+3). Sheet ThucTe, OR_DuBao."),
        ("", None),
        ("2. QUY ƯỚC MÀU & DẤU", None),
        ("Chữ xanh dương", "Ô nhập liệu (hardcode) - BP được phép sửa."),
        ("Nền vàng", "Giả định then chốt / ô bắt buộc nhập (vd: số tháng thực tế của OR, điều chỉnh dự báo)."),
        ("Chữ đen", "Công thức - KHÔNG sửa."),
        ("Chữ xanh lá", "Liên kết từ sheet khác - KHÔNG sửa."),
        ("Dấu", "Doanh thu/lợi nhuận mang dấu dương, chi phí mang dấu âm trên P&L. Chênh lệch dương = THUẬN LỢI cho mọi chỉ tiêu."),
        ("Dữ liệu mẫu", "Toàn bộ số liệu trong file là DỮ LIỆU MẪU minh họa định dạng, cần thay bằng số liệu thật của doanh nghiệp."),
        ("", None),
        ("3. LUỒNG DỮ LIỆU & TRÁCH NHIỆM", None),
        ("GiaDinh", "Giả định vĩ mô, thuế, tỷ lệ BH, mùa vụ, khấu hao TS hiện hữu, số tháng thực tế OR. — Kế toán/FP&A"),
        ("DanhMuc", "Danh mục nhóm SP, kênh, BP, nhóm P&L (dùng cho danh sách chọn). — FP&A"),
        ("AOP_MucTieu", "Mục tiêu năm (top-down), so sánh với Budget bottom-up, mục tiêu theo kênh, sáng kiến chiến lược. — Ban TGĐ/FP&A"),
        ("BG_DoanhThu", "Sản lượng năm, giá bán, % chiết khấu theo nhóm SP x kênh → phân bổ tháng theo mùa vụ. — Khối Kinh doanh"),
        ("BG_GiaVon", "Giá thành đơn vị theo cấu phần → giá vốn tháng = sản lượng x giá thành. — Sản xuất/Kế toán giá thành"),
        ("BG_ChiPhi", "Ngân sách chi phí BH&MKT và QLDN theo BP x khoản mục, phân bổ Đều/Mùa vụ. — Các BP"),
        ("BG_NhanSu", "Định biên theo tháng, lương bình quân, tháng tăng lương → chi phí nhân sự. — HC-NS"),
        ("BG_Capex", "Dự án đầu tư: nguyên giá, tháng đưa vào sử dụng, thời gian KH → khấu hao & dòng tiền đầu tư. — Các BP/Đầu tư"),
        ("BG_PL", "P&L ngân sách theo tháng — tự động tổng hợp, không nhập."),
        ("ThucTe", "Số thực tế theo tháng từ sổ sách/ERP (nhập các dòng chữ xanh). — Kế toán tổng hợp"),
        ("OR_DuBao", "OR = Thực tế (tháng ≤ số tháng thực tế) + Budget + Điều chỉnh (các tháng còn lại). — FP&A + BP"),
        ("SoSanh", "So sánh AOP - Budget - OR, lũy kế Thực tế vs Budget, cột giải trình. — FP&A"),
        ("", None),
        ("4. LỊCH TRÌNH THAM KHẢO", None),
        ("Tháng 8 (năm N-1)", "Ban TGĐ ban hành định hướng chiến lược & mục tiêu AOP; FP&A gửi template + giả định."),
        ("Tháng 9", "Các BP lập Budget chi tiết (doanh thu, chi phí, nhân sự, capex)."),
        ("Tháng 10", "FP&A tổng hợp, đối chiếu AOP, review vòng 1 với từng BP; điều chỉnh."),
        ("Tháng 11", "Trình Ban TGĐ/HĐQT phê duyệt Budget."),
        ("Tháng 12", "Ban hành Budget chính thức, khóa phiên bản, phân bổ chỉ tiêu cho BP."),
        ("Tháng 4 / 7 / 10 (năm N)", "Lập OR1 (3+9) / OR2 (6+6) / OR3 (9+3): cập nhật ThucTe, đổi số tháng tại GiaDinh!C15, nhập điều chỉnh, giải trình."),
        ("", None),
        ("5. CÁC BƯỚC LẬP OR", None),
        ("Bước 1", "Khóa file Budget gốc (lưu bản Budget riêng, không sửa BG_* sau khi duyệt)."),
        ("Bước 2", "Nhập số thực tế các tháng đã khóa sổ vào sheet ThucTe."),
        ("Bước 3", "Đổi GiaDinh!C15 = số tháng thực tế (3, 6, 9)."),
        ("Bước 4", "Nhập điều chỉnh dự báo cho tháng còn lại tại OR_DuBao (khối 'Điều chỉnh so với Budget') kèm giả định."),
        ("Bước 5", "Rà soát SoSanh, ghi giải trình cho chênh lệch > 5% hoặc > ngưỡng trọng yếu."),
    ]
    r = 4
    for a, b in rows:
        if b is None and a:
            section(ws, r, a, 2)
        else:
            ws.cell(row=r, column=1, value=a).font = F_BOLD
            c = ws.cell(row=r, column=2, value=b)
            c.font = F_BASE
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if a == "Chữ xanh dương":
                ws.cell(row=r, column=1).font = Font(name=FONT, size=10, bold=True, color="0000FF")
            if a == "Nền vàng":
                ws.cell(row=r, column=1).fill = FILL_KEY
            if a == "Chữ xanh lá":
                ws.cell(row=r, column=1).font = Font(name=FONT, size=10, bold=True, color="008000")
        r += 1
    widths(ws, {"A": 34, "B": 110})
    return ws


def build_giadinh(wb):
    ws = wb.create_sheet("GiaDinh")
    ws["A1"] = "GIẢ ĐỊNH CHUNG"
    ws["A1"].font = F_TITLE
    ws["A2"] = "Các ô nền vàng/chữ xanh là giả định - mọi sheet tham chiếu về đây"
    ws["A2"].font = F_NOTE
    header_row(ws, 3, ["#", "Giả định", "Giá trị", "Ghi chú / nguồn"])
    items = [
        (4, "Tên doanh nghiệp", "Công ty CP ABC", None, "Nhập tên pháp nhân"),
        (5, "Năm kế hoạch", "2027", None, "Năm lập AOP/Budget (dạng text)"),
        (6, "Đơn vị tiền tệ", "Triệu VND", None, "Áp dụng toàn file"),
        (7, "Thuế suất TNDN", 0.20, PCT, "Luật thuế TNDN hiện hành"),
        (8, "BHXH, BHYT, BHTN, KPCĐ (DN đóng)", 0.235, PCT, "17.5% + 3% + 1% + 2% KPCĐ - kiểm tra lại quy định hiện hành"),
        (9, "Tăng lương bình quân", 0.07, PCT, "Áp dụng từ tháng tăng lương tại BG_NhanSu"),
        (10, "Lạm phát (CPI) tham chiếu", 0.04, PCT, "Tham chiếu khi lập giá bán/chi phí"),
        (11, "Tỷ giá USD/VND", 25500, NUM, "Tham chiếu cho NVL nhập khẩu"),
        (12, "Khấu hao TSCĐ hiện hữu (cả năm)", 600000, NUM, "Từ bảng KH TSCĐ hiện tại - Kế toán TSCĐ"),
        (13, "DT/(CP) tài chính thuần (cả năm)", -80000, NUM, "Lãi vay - lãi tiền gửi +/- chênh lệch tỷ giá"),
        (14, "Lợi nhuận khác (cả năm)", 5000, NUM, "Thanh lý TS, thu nhập khác"),
        (15, "Số tháng THỰC TẾ trong OR", 6, "0", "3 = OR1, 6 = OR2, 9 = OR3, 0 = chưa có thực tế"),
    ]
    for r, lab, val, fmt, nt in items:
        ws.cell(row=r, column=1, value=r - 3).font = F_BASE
        ws.cell(row=r, column=2, value=lab).font = F_BASE
        c = ws.cell(row=r, column=3, value=val)
        c.font = F_INPUT
        c.fill = FILL_KEY
        if fmt:
            c.number_format = fmt
        ws.cell(row=r, column=4, value=nt).font = F_NOTE
    ws["A16"] = 13
    ws["A16"].font = F_BASE
    ws["B16"] = "Phiên bản OR"
    ws["B16"].font = F_BASE
    ws["C16"] = '="OR "&C15&"+"&(12-C15)'
    ws["C16"].font = F_BOLD
    dv = DataValidation(type="whole", operator="between", formula1="0", formula2="12", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("C15")

    section(ws, 18, "Tỷ trọng mùa vụ theo tháng (tổng phải = 100%) - dùng phân bổ sản lượng & chi phí 'Mùa vụ'", 16)
    month_header(ws, 19, mp, ["", "Chỉ tiêu", ""], last_label="Tổng")
    ws["B20"] = "Tỷ trọng mùa vụ"
    ws["B20"].font = F_BASE
    for i in MONTHS:
        c = ws[f"{mp(i)}20"]
        c.value = SEASON[i - 1]
        c.font = F_INPUT
        c.fill = FILL_KEY
        c.number_format = PCT
    ws["P20"] = "=SUM(D20:O20)"
    ws["P20"].number_format = PCT
    ws["P20"].font = F_BOLD
    ws["B21"] = "Kiểm tra"
    ws["B21"].font = F_BASE
    ws["P21"] = '=IF(ROUND(P20,4)=1,"OK","LỖI: tổng ≠ 100%")'
    ws["P21"].font = F_BOLD
    note(ws, "D20", "Mùa vụ mẫu ngành sữa: cao điểm hè (T5-T8) và Tết (T12). Thay bằng dữ liệu bán hàng 3 năm gần nhất.")
    widths(ws, {"A": 5, "B": 38, "C": 16, "D": 12})
    for i in MONTHS:
        ws.column_dimensions[mp(i)].width = max(ws.column_dimensions[mp(i)].width or 0, 9)
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["P"].width = 18
    # ghi chú cột D dài cho phần giả định -> đặt lại cột D rộng bằng merge text tràn
    return ws


def build_danhmuc(wb):
    ws = wb.create_sheet("DanhMuc")
    ws["A1"] = "DANH MỤC"
    ws["A1"].font = F_TITLE
    header_row(ws, 3, ["Nhóm sản phẩm", "Kênh bán hàng", "Bộ phận", "Nhóm P&L", "Phân bổ"])
    for j, lst in enumerate([SKUS, CHANNELS, DEPTS, PL_GROUPS, ALLOC]):
        for i, v in enumerate(lst):
            c = ws.cell(row=4 + i, column=1 + j, value=v)
            c.font = F_INPUT
    ws["A20"] = "Thêm mục mới vào cuối mỗi cột (trong vùng dòng 4-18); danh sách chọn ở các sheet BG_* tự cập nhật."
    ws["A20"].font = F_NOTE
    widths(ws, {"A": 26, "B": 28, "C": 26, "D": 24, "E": 12})
    return ws


def add_list_dv(ws, col_letter, rng, first, last):
    dv = DataValidation(type="list", formula1=f"=DanhMuc!${col_letter}$4:${col_letter}$18", allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{rng}{first}:{rng}{last}")


def build_doanhthu(wb):
    ws = wb.create_sheet("BG_DoanhThu")
    title(ws, "NGÂN SÁCH DOANH THU", "Nhập: sản lượng năm (tấn), giá bán gộp bình quân (triệu VND/tấn), % chiết khấu. Sản lượng tháng = Sản lượng năm x Mùa vụ (GiaDinh).")
    labels = ["Mã", "Nhóm sản phẩm", "Kênh", "Sản lượng năm (tấn)", "Giá gộp (tr/tấn)", "% Chiết khấu"]
    month_header(ws, 5, mc, labels, last_label="Cả năm")
    n = len(SKUS) * len(CHANNELS)
    secs = {}
    start = 6
    names = [("vol", "1. SẢN LƯỢNG (tấn)"), ("gross", "2. DOANH THU GỘP"),
             ("disc", "3. CHIẾT KHẤU THƯƠNG MẠI"), ("net", "4. DOANH THU THUẦN")]
    for key, lab in names:
        secs[key] = (start + 1, start + n, start + n + 1)  # first, last, total
        section(ws, start, lab, 19)
        start += n + 3
    vf, vl, vt = secs["vol"]
    idx = 0
    for s in SKUS:
        for k, ch in enumerate(CHANNELS):
            vol, price, disc = SALES_SAMPLE[s][k]
            r = vf + idx
            ws[f"A{r}"] = f"DT{idx + 1:02d}"
            ws[f"B{r}"] = s
            ws[f"C{r}"] = ch
            ws[f"D{r}"] = vol
            ws[f"E{r}"] = price
            ws[f"F{r}"] = disc
            for col, fmt in (("A", None), ("B", None), ("C", None), ("D", NUM), ("E", NUM1), ("F", PCT)):
                style_cell(ws[f"{col}{r}"], F_INPUT, fmt)
            for i in MONTHS:
                c = ws[f"{mc(i)}{r}"]
                c.value = f"=$D{r}*GiaDinh!{mp(i)}$20"
                style_cell(c, F_BASE, NUM)
            ws[f"S{r}"] = f"=SUM(G{r}:R{r})"
            style_cell(ws[f"S{r}"], F_BOLD, NUM)
            # các khối 2-4
            for key in ("gross", "disc", "net"):
                f0 = secs[key][0]
                rr = f0 + idx
                for col in "ABC":
                    ws[f"{col}{rr}"] = f"={col}{r}"
                    style_cell(ws[f"{col}{rr}"], F_BASE)
                for i in MONTHS:
                    m = mc(i)
                    if key == "gross":
                        fml = f"={m}{r}*$E{r}"
                    elif key == "disc":
                        fml = f"={m}{secs['gross'][0] + idx}*$F{r}"
                    else:
                        fml = f"={m}{secs['gross'][0] + idx}-{m}{secs['disc'][0] + idx}"
                    ws[f"{m}{rr}"] = fml
                    style_cell(ws[f"{m}{rr}"], F_BASE, NUM)
                ws[f"S{rr}"] = f"=SUM(G{rr}:R{rr})"
                style_cell(ws[f"S{rr}"], F_BOLD, NUM)
            idx += 1
    for key, lab in names:
        f0, l0, t0 = secs[key]
        ws[f"B{t0}"] = "Tổng cộng"
        for i in list(MONTHS) + [13]:
            col = mc(i)
            ws[f"{col}{t0}"] = f"=SUM({col}{f0}:{col}{l0})"
            ws[f"{col}{t0}"].number_format = NUM
        if key == "vol":
            ws[f"D{t0}"] = f"=SUM(D{f0}:D{l0})"
            ws[f"D{t0}"].number_format = NUM
        total_style(ws, t0, 19)
    note(ws, f"D{vf}", "Dữ liệu mẫu. Thay bằng sản lượng kế hoạch của Khối Kinh doanh. Có thể ghi đè trực tiếp sản lượng tháng (G:R) nếu không dùng mùa vụ chung - khi đó đổi màu chữ thành xanh dương.")
    add_list_dv(ws, "A", "B", vf, vl)
    add_list_dv(ws, "B", "C", vf, vl)
    widths(ws, {"A": 7, "B": 22, "C": 24, "D": 13, "E": 11, "F": 10, "S": 13})
    for i in MONTHS:
        ws.column_dimensions[mc(i)].width = 11
    ws.freeze_panes = "G6"
    return ws, secs


def build_giavon(wb, dt_secs):
    ws = wb.create_sheet("BG_GiaVon")
    title(ws, "NGÂN SÁCH GIÁ VỐN", "Giá thành đơn vị (triệu VND/tấn) theo cấu phần. Giá vốn tháng = Sản lượng tháng (BG_DoanhThu) x Giá thành đơn vị.")
    section(ws, 5, "1. GIÁ THÀNH ĐƠN VỊ (triệu VND/tấn)", 19)
    header_row(ws, 6, ["Mã", "Nhóm sản phẩm", "Sữa nguyên liệu", "Bao bì", "NVL khác", "Chi phí chuyển đổi", "Tổng giá thành"])
    uf = 7
    for k, s in enumerate(SKUS):
        r = uf + k
        ws[f"A{r}"] = f"GV{k + 1:02d}"
        ws[f"B{r}"] = s
        style_cell(ws[f"A{r}"], F_BASE)
        style_cell(ws[f"B{r}"], F_INPUT)
        for j, v in enumerate(COST_SAMPLE[s]):
            c = ws.cell(row=r, column=3 + j, value=v)
            style_cell(c, F_INPUT, NUM1)
        ws[f"G{r}"] = f"=SUM(C{r}:F{r})"
        style_cell(ws[f"G{r}"], F_BOLD, NUM1)
    ul = uf + len(SKUS) - 1
    note(ws, "F7", "Chi phí chuyển đổi gồm nhân công trực tiếp sản xuất, năng lượng, SXC (không gồm khấu hao - khấu hao trình bày riêng dòng Khấu hao TSCĐ).")
    note(ws, "C7", "Dữ liệu mẫu. Lấy từ định mức BOM x đơn giá NVL kế hoạch (Phòng Kế toán giá thành).")

    s2 = ul + 3
    section(ws, s2, "2. GIÁ VỐN HÀNG BÁN THEO THÁNG", 19)
    month_header(ws, s2 + 1, mc, ["Mã", "Nhóm sản phẩm", "", "", "", "Giá thành/tấn"], last_label="Cả năm")
    cf = s2 + 2
    vf, vl, _ = dt_secs["vol"]
    for k in range(len(SKUS)):
        r = cf + k
        ws[f"A{r}"] = f"=A{uf + k}"
        ws[f"B{r}"] = f"=B{uf + k}"
        ws[f"F{r}"] = f"=G{uf + k}"
        style_cell(ws[f"A{r}"], F_BASE)
        style_cell(ws[f"B{r}"], F_BASE)
        style_cell(ws[f"F{r}"], F_BASE, NUM1)
        for i in MONTHS:
            m = mc(i)
            ws[f"{m}{r}"] = f"=SUMIFS(BG_DoanhThu!{m}${vf}:{m}${vl},BG_DoanhThu!$B${vf}:$B${vl},$B{r})*$F{r}"
            style_cell(ws[f"{m}{r}"], F_LINK, NUM)
        ws[f"S{r}"] = f"=SUM(G{r}:R{r})"
        style_cell(ws[f"S{r}"], F_BOLD, NUM)
    cl = cf + len(SKUS) - 1
    ct = cl + 1
    ws[f"B{ct}"] = "Tổng giá vốn"
    for i in list(MONTHS) + [13]:
        col = mc(i)
        ws[f"{col}{ct}"] = f"=SUM({col}{cf}:{col}{cl})"
        ws[f"{col}{ct}"].number_format = NUM
    total_style(ws, ct, 19)
    widths(ws, {"A": 7, "B": 22, "C": 14, "D": 10, "E": 10, "F": 14, "G": 13, "S": 13})
    for i in MONTHS:
        if mc(i) != "G":
            ws.column_dimensions[mc(i)].width = 11
    ws.freeze_panes = "C7"
    return ws, ct


def build_chiphi(wb):
    ws = wb.create_sheet("BG_ChiPhi")
    title(ws, "NGÂN SÁCH CHI PHÍ HOẠT ĐỘNG (không gồm nhân sự & khấu hao)", "Nhập ngân sách năm theo BP x khoản mục, chọn Nhóm P&L và cách phân bổ (Đều = /12; Mùa vụ = theo GiaDinh dòng 20).")
    month_header(ws, 5, mc, ["Mã", "Bộ phận", "Khoản mục chi phí", "Nhóm P&L", "Ngân sách năm", "Phân bổ"], last_label="Cả năm")
    first = 6
    n_rows = 25  # chừa dòng trống cho BP bổ sung
    for k in range(n_rows):
        r = first + k
        ws[f"A{r}"] = f"CP{k + 1:02d}"
        style_cell(ws[f"A{r}"], F_BASE)
        if k < len(OPEX_SAMPLE):
            d, item, grp, amt, alloc = OPEX_SAMPLE[k]
            ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"], ws[f"F{r}"] = d, item, grp, amt, alloc
        for col in "BCDEF":
            style_cell(ws[f"{col}{r}"], F_INPUT, NUM if col == "E" else None)
        for i in MONTHS:
            m = mc(i)
            ws[f"{m}{r}"] = f'=IF($F{r}="Mùa vụ",$E{r}*GiaDinh!{mp(i)}$20,$E{r}/12)'
            style_cell(ws[f"{m}{r}"], F_BASE, NUM)
        ws[f"S{r}"] = f"=SUM(G{r}:R{r})"
        style_cell(ws[f"S{r}"], F_BOLD, NUM)
    last = first + n_rows - 1
    t = last + 1
    ws[f"B{t}"] = "Tổng chi phí hoạt động"
    ws[f"E{t}"] = f"=SUM(E{first}:E{last})"
    ws[f"E{t}"].number_format = NUM
    for i in list(MONTHS) + [13]:
        col = mc(i)
        ws[f"{col}{t}"] = f"=SUM({col}{first}:{col}{last})"
        ws[f"{col}{t}"].number_format = NUM
    total_style(ws, t, 19)
    for g_i, g in enumerate(PL_GROUPS):
        r = t + 1 + g_i
        ws[f"B{r}"] = f"  Trong đó: {g}"
        ws[f"D{r}"] = g
        for i in list(MONTHS) + [13]:
            col = mc(i)
            ws[f"{col}{r}"] = f"=SUMIFS({col}${first}:{col}${last},$D${first}:$D${last},$D{r})"
            ws[f"{col}{r}"].number_format = NUM
            ws[f"{col}{r}"].font = F_BASE
    add_list_dv(ws, "C", "B", first, last)
    add_list_dv(ws, "D", "D", first, last)
    add_list_dv(ws, "E", "F", first, last)
    note(ws, "E6", "Dữ liệu mẫu. Các BP nhập ngân sách năm; số âm không dùng (chi phí nhập số dương, P&L tự đổi dấu).")
    widths(ws, {"A": 7, "B": 22, "C": 34, "D": 22, "E": 14, "F": 9, "S": 13})
    for i in MONTHS:
        ws.column_dimensions[mc(i)].width = 11
    ws.freeze_panes = "G6"
    return ws, first, last


def build_nhansu(wb):
    ws = wb.create_sheet("BG_NhanSu")
    title(ws, "NGÂN SÁCH NHÂN SỰ (khối văn phòng & bán hàng)", "Nhập định biên từng tháng, lương bình quân hiện tại và tháng tăng lương. NC sản xuất đã nằm trong giá thành (BG_GiaVon).")
    month_header(ws, 5, mc, ["Mã", "Bộ phận", "Lương bq (tr/người/tháng)", "Tháng tăng lương", "", ""], last_label="Cuối năm")
    section(ws, 6, "1. ĐỊNH BIÊN (người)", 19)
    hf = 7
    n = len(HC_SAMPLE)
    for k, (d, hc, sal) in enumerate(HC_SAMPLE):
        r = hf + k
        ws[f"A{r}"] = f"NS{k + 1:02d}"
        ws[f"B{r}"] = d
        ws[f"C{r}"] = sal
        ws[f"D{r}"] = 4
        style_cell(ws[f"A{r}"], F_BASE)
        style_cell(ws[f"B{r}"], F_INPUT)
        style_cell(ws[f"C{r}"], F_INPUT, NUM1)
        style_cell(ws[f"D{r}"], F_INPUT, "0")
        for i in MONTHS:
            # tăng nhẹ định biên bán hàng/chuỗi cửa hàng để minh họa
            v = hc + (int(hc * 0.01) * (i - 1) if d in ("Bán hàng", "Chuỗi cửa hàng") else 0)
            style_cell(ws.cell(row=r, column=6 + i, value=v), F_INPUT, NUM)
        ws[f"S{r}"] = f"=R{r}"
        style_cell(ws[f"S{r}"], F_BOLD, NUM)
    hl = hf + n - 1
    ht = hl + 1
    ws[f"B{ht}"] = "Tổng định biên"
    for i in list(MONTHS) + [13]:
        col = mc(i)
        ws[f"{col}{ht}"] = f"=SUM({col}{hf}:{col}{hl})"
        ws[f"{col}{ht}"].number_format = NUM
    total_style(ws, ht, 19)

    s2 = ht + 2
    section(ws, s2, "2. CHI PHÍ NHÂN SỰ (lương + BH DN đóng)", 19)
    cf = s2 + 1
    for k in range(n):
        r = cf + k
        src = hf + k
        ws[f"A{r}"] = f"=A{src}"
        ws[f"B{r}"] = f"=B{src}"
        style_cell(ws[f"A{r}"], F_BASE)
        style_cell(ws[f"B{r}"], F_BASE)
        for i in MONTHS:
            m = mc(i)
            ws[f"{m}{r}"] = (f"={m}{src}*$C{src}*IF({m}$5>=$D{src},1+GiaDinh!$C$9,1)"
                             f"*(1+GiaDinh!$C$8)")
            style_cell(ws[f"{m}{r}"], F_BASE, NUM)
        ws[f"S{r}"] = f"=SUM(G{r}:R{r})"
        style_cell(ws[f"S{r}"], F_BOLD, NUM)
    cl = cf + n - 1
    ct = cl + 1
    ws[f"B{ct}"] = "Tổng chi phí nhân sự"
    for i in list(MONTHS) + [13]:
        col = mc(i)
        ws[f"{col}{ct}"] = f"=SUM({col}{cf}:{col}{cl})"
        ws[f"{col}{ct}"].number_format = NUM
    total_style(ws, ct, 19)
    ws.cell(row=ct + 1, column=2, value="Cột 'Cuối năm' của khối 1 = định biên tháng 12; khối 2 = tổng chi phí cả năm. Thưởng/13th salary: thêm dòng hoặc đưa vào lương bq.").font = F_NOTE
    note(ws, "C7", "Dữ liệu mẫu. Lương bq gồm lương cứng + phụ cấp + thưởng bình quân tháng.")
    add_list_dv(ws, "C", "B", hf, hl)
    widths(ws, {"A": 7, "B": 24, "C": 14, "D": 11, "E": 2, "F": 2, "S": 13})
    for i in MONTHS:
        ws.column_dimensions[mc(i)].width = 11
    ws.freeze_panes = "G6"
    return ws, ht, ct


def build_capex(wb):
    ws = wb.create_sheet("BG_Capex")
    title(ws, "NGÂN SÁCH ĐẦU TƯ (CAPEX) & KHẤU HAO", "Nhập dự án: nguyên giá, tháng đưa vào sử dụng (1-12), thời gian khấu hao (năm). Khấu hao đường thẳng từ tháng đưa vào sử dụng.")
    month_header(ws, 5, mc, ["Mã", "Dự án đầu tư", "Bộ phận", "Nguyên giá", "Tháng SD", "Số năm KH"], last_label="Cả năm")
    section(ws, 6, "1. KHẤU HAO", 19)
    ws["A7"] = "KH00"
    ws["B7"] = "Khấu hao TSCĐ hiện hữu"
    style_cell(ws["A7"], F_BASE)
    style_cell(ws["B7"], F_BASE)
    for i in MONTHS:
        ws[f"{mc(i)}7"] = "=GiaDinh!$C$12/12"
        style_cell(ws[f"{mc(i)}7"], F_LINK, NUM)
    ws["S7"] = "=SUM(G7:R7)"
    style_cell(ws["S7"], F_BOLD, NUM)
    pf = 8
    n = 15
    for k in range(n):
        r = pf + k
        ws[f"A{r}"] = f"DA{k + 1:02d}"
        style_cell(ws[f"A{r}"], F_BASE)
        if k < len(CAPEX_SAMPLE):
            p, d, amt, mon, life = CAPEX_SAMPLE[k]
            ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"], ws[f"F{r}"] = p, d, amt, mon, life
        for col, fmt in (("B", None), ("C", None), ("D", NUM), ("E", "0"), ("F", "0")):
            style_cell(ws[f"{col}{r}"], F_INPUT, fmt)
        for i in MONTHS:
            m = mc(i)
            ws[f"{m}{r}"] = f"=IF(AND($D{r}>0,$F{r}>0,{m}$5>=$E{r}),$D{r}/($F{r}*12),0)"
            style_cell(ws[f"{m}{r}"], F_BASE, NUM)
        ws[f"S{r}"] = f"=SUM(G{r}:R{r})"
        style_cell(ws[f"S{r}"], F_BOLD, NUM)
    pl = pf + n - 1
    dt = pl + 1
    ws[f"B{dt}"] = "Tổng khấu hao"
    for i in list(MONTHS) + [13]:
        col = mc(i)
        ws[f"{col}{dt}"] = f"=SUM({col}7:{col}{pl})"
        ws[f"{col}{dt}"].number_format = NUM
    total_style(ws, dt, 19)

    s2 = dt + 2
    section(ws, s2, "2. DÒNG TIỀN ĐẦU TƯ (giải ngân tại tháng đưa vào sử dụng - điều chỉnh nếu giải ngân theo tiến độ)", 19)
    cf = s2 + 1
    for k in range(n):
        r = cf + k
        src = pf + k
        ws[f"A{r}"] = f"=A{src}"
        ws[f"B{r}"] = f'=IF(B{src}="","",B{src})'
        style_cell(ws[f"A{r}"], F_BASE)
        style_cell(ws[f"B{r}"], F_BASE)
        for i in MONTHS:
            m = mc(i)
            ws[f"{m}{r}"] = f"=IF({m}$5=$E{src},$D{src},0)"
            style_cell(ws[f"{m}{r}"], F_BASE, NUM)
        ws[f"S{r}"] = f"=SUM(G{r}:R{r})"
        style_cell(ws[f"S{r}"], F_BOLD, NUM)
    cl = cf + n - 1
    ct = cl + 1
    ws[f"B{ct}"] = "Tổng Capex"
    for i in list(MONTHS) + [13]:
        col = mc(i)
        ws[f"{col}{ct}"] = f"=SUM({col}{cf}:{col}{cl})"
        ws[f"{col}{ct}"].number_format = NUM
    total_style(ws, ct, 19)
    note(ws, "D8", "Dữ liệu mẫu. Nguyên giá chưa VAT. Thời gian KH theo khung TT45/2013 (hoặc văn bản thay thế hiện hành).")
    add_list_dv(ws, "C", "C", pf, pl)
    widths(ws, {"A": 7, "B": 32, "C": 20, "D": 12, "E": 9, "F": 10, "S": 13})
    for i in MONTHS:
        ws.column_dimensions[mc(i)].width = 11
    ws.freeze_panes = "G6"
    return ws, dt, ct


def pl_frame(ws, title_text, sub):
    title(ws, title_text, sub)
    month_header(ws, 5, mp, ["#", "Chỉ tiêu", "ĐVT"], last_label="Cả năm")
    for i, (key, lab, kind) in enumerate(PL_LINES):
        r = R[key]
        ws[f"A{r}"] = i + 1
        ws[f"B{r}"] = lab
        ws[f"C{r}"] = "%" if kind == "pct" else ("tấn" if key == "sl" else "tr.VND")
        for col in "ABC":
            ws[f"{col}{r}"].font = F_BOLD if key in BOLD_LINES else F_BASE
        # cột cả năm
        if kind == "pct":
            ws[f"P{r}"] = calc_formula(key, "P")
            ws[f"P{r}"].number_format = PCT
        else:
            ws[f"P{r}"] = f"=SUM(D{r}:O{r})"
            ws[f"P{r}"].number_format = NUM
        ws[f"P{r}"].font = F_BOLD
        if key in BOLD_LINES:
            total_style(ws, r, 16)
    widths(ws, {"A": 4, "B": 38, "C": 7, "P": 14})
    for i in MONTHS:
        ws.column_dimensions[mp(i)].width = 11
    ws.freeze_panes = "D6"


def fill_month(ws, key, i, formula, font=F_BASE):
    c = ws[f"{mp(i)}{R[key]}"]
    c.value = formula
    c.number_format = PCT if key in ("gm", "ebitda_pct") else NUM
    c.font = Font(name=FONT, size=10, bold=key in BOLD_LINES, color=font.color)


def build_bg_pl(wb, dt_secs, gv_total, cp_rng, ns_total, kh_total):
    ws = wb.create_sheet("BG_PL")
    pl_frame(ws, "BÁO CÁO KẾT QUẢ KINH DOANH - NGÂN SÁCH (BUDGET)",
             "Tự động tổng hợp từ các sheet BG_*. Không nhập liệu tại đây. Chi phí mang dấu âm.")
    cf, cl = cp_rng
    for i in MONTHS:
        y = mc(i)
        src = {
            "dt_gop": f"=BG_DoanhThu!{y}{dt_secs['gross'][2]}",
            "ck": f"=-BG_DoanhThu!{y}{dt_secs['disc'][2]}",
            "gv": f"=-BG_GiaVon!{y}{gv_total}",
            "bh": f'=-SUMIFS(BG_ChiPhi!{y}${cf}:{y}${cl},BG_ChiPhi!$D${cf}:$D${cl},"Bán hàng & Marketing")',
            "ql": f'=-SUMIFS(BG_ChiPhi!{y}${cf}:{y}${cl},BG_ChiPhi!$D${cf}:$D${cl},"Quản lý doanh nghiệp")',
            "ns": f"=-BG_NhanSu!{y}{ns_total}",
            "kh": f"=-BG_Capex!{y}{kh_total}",
            "tc": "=GiaDinh!$C$13/12",
            "khac": "=GiaDinh!$C$14/12",
            "thue": f"=-MAX(0,{mp(i)}{R['lntt']})*GiaDinh!$C$7",
            "sl": f"=BG_DoanhThu!{y}{dt_secs['vol'][2]}",
        }
        for key, _, kind in PL_LINES:
            if kind == "in":
                fill_month(ws, key, i, src[key], F_BASE if key == "thue" else F_LINK)
            else:
                fill_month(ws, key, i, calc_formula(key, mp(i)))
    r = R["sl"] + 2
    ws[f"B{r}"] = "Ghi chú: Thuế TNDN tạm tính theo tháng = MAX(0, LNTT tháng) x thuế suất; quyết toán theo năm có thể khác."
    ws[f"B{r}"].font = F_NOTE
    return ws


def build_thucte(wb):
    ws = wb.create_sheet("ThucTe")
    pl_frame(ws, "SỐ LIỆU THỰC TẾ THEO THÁNG",
             "Kế toán tổng hợp nhập số đã khóa sổ (dòng chữ xanh). Chi phí nhập số ÂM. Dòng tổng là công thức.")
    for i in MONTHS:
        for key, _, kind in PL_LINES:
            if kind == "in":
                c = ws[f"{mp(i)}{R[key]}"]
                c.number_format = NUM
                c.font = F_INPUT
            else:
                fill_month(ws, key, i, calc_formula(key, mp(i)))
    ws["D4"] = "Nguồn: Sổ cái / ERP sau khóa sổ. Mapping tài khoản: 511→DT gộp; 521→CK TM; 632→GVHB; 641→BH&MKT; 642→QLDN; 334,338→nhân sự; 214→KH; 515-635→TC; 711-811→khác; 821→thuế."
    ws["D4"].font = F_NOTE
    return ws


def build_or(wb):
    ws = wb.create_sheet("OR_DuBao")
    pl_frame(ws, "OUTLOOK REVISION (OR) - ƯỚC THỰC HIỆN CẢ NĂM",
             "Tháng ≤ GiaDinh!C15: lấy Thực tế. Tháng còn lại: Budget + Điều chỉnh (khối bên dưới). Thuế tháng dự báo tính lại theo LNTT.")
    ws["B4"] = '="Phiên bản: "&GiaDinh!$C$16'
    ws["B4"].font = F_BOLD
    for i in MONTHS:
        c = ws[f"{mp(i)}4"]
        c.value = f'=IF({mp(i)}$5<=GiaDinh!$C$15,"Thực tế","Dự báo")'
        c.font = F_BOLD
        c.alignment = Alignment(horizontal="center")

    adj_title = R["sl"] + 3
    section(ws, adj_title, "ĐIỀU CHỈNH DỰ BÁO SO VỚI BUDGET (chỉ có hiệu lực ở tháng 'Dự báo'; doanh thu +, chi phí - nếu tăng chi phí)", 17)
    month_header(ws, adj_title + 1, mp, ["#", "Chỉ tiêu", "ĐVT"], last_label="Cả năm")
    ws[f"Q{adj_title + 1}"] = "Giả định / lý do điều chỉnh"
    ws[f"Q{adj_title + 1}"].font = F_HEAD
    ws[f"Q{adj_title + 1}"].fill = FILL_HEAD
    adj = {}
    r = adj_title + 2
    for key, lab, kind in PL_LINES:
        if kind != "in" or key == "thue":
            continue
        adj[key] = r
        ws[f"A{r}"] = len(adj)
        ws[f"B{r}"] = lab
        ws[f"C{r}"] = "tấn" if key == "sl" else "tr.VND"
        for col in "ABC":
            ws[f"{col}{r}"].font = F_BASE
        for i in MONTHS:
            c = ws[f"{mp(i)}{r}"]
            c.font = F_INPUT
            c.fill = FILL_KEY
            c.number_format = NUM
        ws[f"P{r}"] = f"=SUM(D{r}:O{r})"
        ws[f"P{r}"].number_format = NUM
        ws[f"P{r}"].font = F_BOLD
        ws[f"Q{r}"].font = F_INPUT
        r += 1
    # ví dụ điều chỉnh
    ws[f"L{adj['dt_gop']}"] = -15000
    ws[f"L{adj['dt_gop']}"].font = F_INPUT
    ws[f"Q{adj['dt_gop']}"] = "VD: T9 giảm 15 tỷ do đối thủ khuyến mại mạnh kênh MT"
    ws[f"Q{adj['dt_gop']}"].font = F_INPUT
    ws.column_dimensions["Q"].width = 50

    for i in MONTHS:
        c = mp(i)
        for key, _, kind in PL_LINES:
            if kind == "in":
                rr = R[key]
                if key == "thue":
                    fml = (f"=IF({c}$5<=GiaDinh!$C$15,ThucTe!{c}{rr},"
                           f"-MAX(0,{c}{R['lntt']})*GiaDinh!$C$7)")
                else:
                    fml = (f"=IF({c}$5<=GiaDinh!$C$15,ThucTe!{c}{rr},"
                           f"BG_PL!{c}{rr}+{c}{adj[key]})")
                fill_month(ws, key, i, fml, F_LINK)
            else:
                fill_month(ws, key, i, calc_formula(key, c))
    return ws


def build_aop(wb, dt_secs, ns_hc_total, capex_total):
    ws = wb.create_sheet("AOP_MucTieu")
    title(ws, "AOP - MỤC TIÊU KẾ HOẠCH HOẠT ĐỘNG NĂM",
          "Nhập TH năm trước và mục tiêu AOP (top-down). Budget bottom-up tự liên kết để kiểm tra độ khớp.")
    section(ws, 5, "1. KPI TÀI CHÍNH & HOẠT ĐỘNG CHỦ CHỐT", 10)
    header_row(ws, 6, ["#", "Chỉ tiêu", "ĐVT", "TH năm trước", "Mục tiêu AOP", "Tăng trưởng AOP",
                       "Budget (bottom-up)", "Budget - AOP", "% Budget/AOP", "Đánh giá"])
    kpis = [
        ("sl", "Sản lượng tiêu thụ", "tấn", f"=BG_PL!P{R['sl']}", "up"),
        ("dt_thuan", "Doanh thu thuần", "tr.VND", f"=BG_PL!P{R['dt_thuan']}", "up"),
        ("lng", "Lợi nhuận gộp", "tr.VND", f"=BG_PL!P{R['lng']}", "up"),
        ("gm", "Biên lợi nhuận gộp", "%", f"=BG_PL!P{R['gm']}", "pct"),
        ("ebitda", "EBITDA", "tr.VND", f"=BG_PL!P{R['ebitda']}", "up"),
        ("ebitda_pct", "Biên EBITDA", "%", f"=BG_PL!P{R['ebitda_pct']}", "pct"),
        ("lnst", "Lợi nhuận sau thuế", "tr.VND", f"=BG_PL!P{R['lnst']}", "up"),
        ("hc", "Định biên cuối năm (khối VP & BH)", "người", f"=BG_NhanSu!S{ns_hc_total}", "down"),
        ("capex", "Tổng vốn đầu tư (Capex)", "tr.VND", f"=BG_Capex!S{capex_total}", "down"),
    ]
    aop_rows = {}
    for k, (key, lab, unit, link, kind) in enumerate(kpis):
        r = 7 + k
        aop_rows[key] = r
        fmt = PCT if kind == "pct" else NUM
        ws[f"A{r}"] = k + 1
        ws[f"B{r}"] = lab
        ws[f"C{r}"] = unit
        for col in "ABC":
            ws[f"{col}{r}"].font = F_BASE
        for col in "DE":
            style_cell(ws[f"{col}{r}"], F_INPUT, fmt, FILL_KEY if col == "E" else None)
        if kind == "pct":
            ws[f"F{r}"] = f"=E{r}-D{r}"
            ws[f"H{r}"] = f"=G{r}-E{r}"
            ws[f"I{r}"] = ""
            ws[f"J{r}"] = f'=IF(G{r}>=E{r},"Đạt","Cần rà soát")'
        else:
            ws[f"F{r}"] = f"=IFERROR(E{r}/D{r}-1,0)"
            ws[f"H{r}"] = f"=G{r}-E{r}"
            ws[f"I{r}"] = f"=IFERROR(G{r}/E{r},0)"
            ws[f"J{r}"] = (f'=IF(G{r}>=E{r},"Đạt","Cần rà soát")' if kind == "up"
                           else f'=IF(G{r}<=E{r},"Trong hạn mức","Vượt hạn mức")')
        ws[f"G{r}"] = link
        style_cell(ws[f"F{r}"], F_BASE, PCT)
        style_cell(ws[f"G{r}"], F_LINK, fmt)
        style_cell(ws[f"H{r}"], F_BASE, fmt)
        style_cell(ws[f"I{r}"], F_BASE, PCT)
        style_cell(ws[f"J{r}"], F_BOLD)
    note(ws, "F10", "Với chỉ tiêu %, tăng trưởng và chênh lệch tính theo điểm % (pp).")

    s2 = 7 + len(kpis) + 2
    section(ws, s2, "2. MỤC TIÊU DOANH THU THUẦN THEO KÊNH", 10)
    header_row(ws, s2 + 1, ["#", "Kênh", "ĐVT", "TH năm trước", "Mục tiêu AOP", "Tăng trưởng AOP",
                            "Budget (bottom-up)", "Budget - AOP", "% Budget/AOP", "Đánh giá"])
    ch_rows = []
    for k, ch in enumerate(CHANNELS):
        r = s2 + 2 + k
        ch_rows.append(r)
        ws[f"A{r}"] = k + 1
        ws[f"B{r}"] = ch
        ws[f"C{r}"] = "tr.VND"
        for col in "ABC":
            ws[f"{col}{r}"].font = F_BASE
        style_cell(ws[f"D{r}"], F_INPUT, NUM)
        style_cell(ws[f"E{r}"], F_INPUT, NUM, FILL_KEY)
        ws[f"F{r}"] = f"=IFERROR(E{r}/D{r}-1,0)"
        nf, nl, _ = dt_secs["net"]
        ws[f"G{r}"] = f"=SUMIFS(BG_DoanhThu!$S${nf}:$S${nl},BG_DoanhThu!$C${nf}:$C${nl},$B{r})"
        ws[f"H{r}"] = f"=G{r}-E{r}"
        ws[f"I{r}"] = f"=IFERROR(G{r}/E{r},0)"
        ws[f"J{r}"] = f'=IF(G{r}>=E{r},"Đạt","Cần rà soát")'
        style_cell(ws[f"F{r}"], F_BASE, PCT)
        style_cell(ws[f"G{r}"], F_LINK, NUM)
        style_cell(ws[f"H{r}"], F_BASE, NUM)
        style_cell(ws[f"I{r}"], F_BASE, PCT)
        style_cell(ws[f"J{r}"], F_BOLD)
    t = ch_rows[-1] + 1
    ws[f"B{t}"] = "Tổng"
    for col in "DEGH":
        ws[f"{col}{t}"] = f"=SUM({col}{ch_rows[0]}:{col}{ch_rows[-1]})"
        ws[f"{col}{t}"].number_format = NUM
    ws[f"F{t}"] = f"=IFERROR(E{t}/D{t}-1,0)"
    ws[f"F{t}"].number_format = PCT
    ws[f"I{t}"] = f"=IFERROR(G{t}/E{t},0)"
    ws[f"I{t}"].number_format = PCT
    ws[f"J{t}"] = f'=IF(ROUND(G{t}-G{aop_rows["dt_thuan"]},0)=0,"Khớp P&L","Lệch P&L")'
    total_style(ws, t, 10)

    s3 = t + 2
    section(ws, s3, "3. SÁNG KIẾN CHIẾN LƯỢC (Strategic Initiatives)", 10)
    header_row(ws, s3 + 1, ["#", "Sáng kiến", "BP chủ trì", "KPI đo lường", "Mục tiêu", "Thời hạn",
                            "Ngân sách (tr.VND)", "Liên kết Budget", "Rủi ro chính", "Trạng thái"])
    examples = [
        ("Mở rộng độ phủ kênh GT nông thôn", "Bán hàng", "Số điểm bán", "+15.000 điểm", "Q4", 45000,
         "BG_ChiPhi CP02", "Chi phí trưng bày tăng", "Đang lập"),
        ("Ra mắt dòng sữa hạt mới", "R&D - Chất lượng", "DT SP mới", "300 tỷ", "Q3", 20000,
         "BG_DoanhThu Sữa hạt", "Chậm cấp phép", "Đang lập"),
    ]
    for k in range(8):
        r = s3 + 2 + k
        ws[f"A{r}"] = k + 1
        ws[f"A{r}"].font = F_BASE
        vals = examples[k] if k < len(examples) else [None] * 9
        for j, v in enumerate(vals):
            c = ws.cell(row=r, column=2 + j, value=v)
            style_cell(c, F_INPUT, NUM if j == 5 else None)
    widths(ws, {"A": 4, "B": 36, "C": 18, "D": 15, "E": 15, "F": 13, "G": 17, "H": 18, "I": 20, "J": 15})
    ws.freeze_panes = "C7"
    return ws, aop_rows, ch_rows


def build_sosanh(wb, aop_rows):
    ws = wb.create_sheet("SoSanh")
    title(ws, "SO SÁNH AOP - BUDGET - OR & GIẢI TRÌNH",
          "Chênh lệch dương = thuận lợi (chi phí mang dấu âm). Ghi giải trình cho chênh lệch trọng yếu (vd > 5%).")
    ws["B4"] = '="Phiên bản OR: "&GiaDinh!$C$16&"   |   Lũy kế "&GiaDinh!$C$15&" tháng"'
    ws["B4"].font = F_BOLD
    header_row(ws, 5, ["#", "Chỉ tiêu", "AOP", "Budget cả năm", "OR cả năm", "OR - Budget", "%",
                       "OR - AOP", "%", "LK Thực tế", "LK Budget", "LK TT - BG", "%", "Giải trình / hành động"])
    cutoff = "GiaDinh!$C$15"
    for i, (key, lab, kind) in enumerate(PL_LINES):
        r = R[key]
        ws[f"A{r}"] = i + 1
        ws[f"B{r}"] = lab
        fmt = PCT if kind == "pct" else NUM
        if key in aop_rows:
            ws[f"C{r}"] = f"=AOP_MucTieu!E{aop_rows[key]}"
            style_cell(ws[f"C{r}"], F_LINK, fmt)
        ws[f"D{r}"] = f"=BG_PL!P{r}"
        ws[f"E{r}"] = f"=OR_DuBao!P{r}"
        style_cell(ws[f"D{r}"], F_LINK, fmt)
        style_cell(ws[f"E{r}"], F_LINK, fmt)
        ws[f"F{r}"] = f"=E{r}-D{r}"
        style_cell(ws[f"F{r}"], F_BASE, fmt)
        if key in aop_rows:
            ws[f"H{r}"] = f"=E{r}-C{r}"
            style_cell(ws[f"H{r}"], F_BASE, fmt)
        if kind == "pct":
            ws[f"J{r}"] = calc_formula(key, "J")
            ws[f"K{r}"] = calc_formula(key, "K")
        else:
            ws[f"G{r}"] = f"=IFERROR(F{r}/ABS(D{r}),0)"
            style_cell(ws[f"G{r}"], F_BASE, PCT)
            if key in aop_rows:
                ws[f"I{r}"] = f"=IFERROR(H{r}/ABS(C{r}),0)"
                style_cell(ws[f"I{r}"], F_BASE, PCT)
            ws[f"J{r}"] = f"=SUMPRODUCT((ThucTe!$D$5:$O$5<={cutoff})*ThucTe!D{r}:O{r})"
            ws[f"K{r}"] = f"=SUMPRODUCT((BG_PL!$D$5:$O$5<={cutoff})*BG_PL!D{r}:O{r})"
            ws[f"M{r}"] = f"=IFERROR(L{r}/ABS(K{r}),0)"
            style_cell(ws[f"M{r}"], F_BASE, PCT)
        style_cell(ws[f"J{r}"], F_LINK, fmt)
        style_cell(ws[f"K{r}"], F_LINK, fmt)
        ws[f"L{r}"] = f"=J{r}-K{r}"
        style_cell(ws[f"L{r}"], F_BASE, fmt)
        style_cell(ws[f"N{r}"], F_INPUT)
        if key in BOLD_LINES:
            total_style(ws, r, 14)
        else:
            ws[f"A{r}"].font = F_BASE
            ws[f"B{r}"].font = F_BASE
    ws[f"N{R['dt_gop']}"] = "VD: Lũy kế thấp hơn BG do kênh MT chậm; OR điều chỉnh T9."
    ws[f"N{R['dt_gop']}"].font = F_INPUT
    widths(ws, {"A": 4, "B": 38, "C": 13, "D": 14, "E": 14, "F": 12, "G": 8, "H": 12, "I": 8,
                "J": 13, "K": 13, "L": 12, "M": 8, "N": 50})
    ws.freeze_panes = "C6"
    return ws


def build(path):
    wb = Workbook()
    wb.remove(wb.active)
    build_hdsd(wb)
    build_giadinh(wb)
    build_danhmuc(wb)
    _, dt_secs = build_doanhthu(wb)
    _, gv_total = build_giavon(wb, dt_secs)
    _, cf, cl = build_chiphi(wb)
    _, ns_hc_total, ns_cost_total = build_nhansu(wb)
    _, kh_total, capex_total = build_capex(wb)
    build_bg_pl(wb, dt_secs, gv_total, (cf, cl), ns_cost_total, kh_total)
    build_thucte(wb)
    build_or(wb)
    _, aop_rows, ch_rows = build_aop(wb, dt_secs, ns_hc_total, capex_total)
    wb.move_sheet("AOP_MucTieu", offset=-(len(wb.sheetnames) - 4))
    build_sosanh(wb, aop_rows)
    tabs = {"HDSD": "808080", "GiaDinh": "FFC000", "DanhMuc": "FFC000", "AOP_MucTieu": "C00000",
            "ThucTe": "7030A0", "OR_DuBao": "7030A0", "SoSanh": "00B050"}
    for ws in wb.worksheets:
        ws.sheet_properties.tabColor = tabs.get(ws.title, "1F4E78")
        ws.sheet_view.showGridLines = False
    wb.save(path)
    return aop_rows, ch_rows


def fill_samples(path, calc_path, aop_rows, ch_rows):
    """Điền số mẫu (hardcode) cho Thực tế T1-T6, TH năm trước và mục tiêu AOP từ Budget đã tính."""
    vals = load_workbook(calc_path, data_only=True)
    wb = load_workbook(path)
    rnd = random.Random(2027)
    bg = vals["BG_PL"]
    tt = wb["ThucTe"]
    for i in range(1, 7):
        for key, _, kind in PL_LINES:
            if kind != "in":
                continue
            c = mp(i)
            v = bg[f"{c}{R[key]}"].value or 0
            factor = 1 + rnd.uniform(-0.06, 0.04)
            if key == "thue":
                continue
            tt[f"{c}{R[key]}"] = round(v * factor)
        # thuế thực tế: tạm tính từ LNTT thực tế ước lượng
    for i in range(1, 7):
        c = mp(i)
        lntt = sum((tt[f"{c}{R[k]}"].value or 0) for k in ("dt_gop", "ck", "gv", "bh", "ql", "ns", "kh", "tc", "khac"))
        tt[f"{c}{R['thue']}"] = -round(max(0, lntt) * 0.2)
    aop = wb["AOP_MucTieu"]
    av = vals["AOP_MucTieu"]
    for key, r in aop_rows.items():
        g = av[f"G{r}"].value or 0
        if key in ("gm", "ebitda_pct"):
            aop[f"D{r}"] = round(g - 0.01, 4)
            aop[f"E{r}"] = round(g + 0.005, 4)
        else:
            aop[f"D{r}"] = round(g / 1.10)
            aop[f"E{r}"] = round(g * (1.02 if key not in ("hc", "capex") else 1.0))
    for r in ch_rows:
        g = av[f"G{r}"].value or 0
        aop[f"D{r}"] = round(g / 1.12)
        aop[f"E{r}"] = round(g * 1.02)
    wb.save(path)


if __name__ == "__main__":
    import subprocess
    out = sys.argv[1] if len(sys.argv) > 1 else "Template_AOP_Budget_OR.xlsx"
    recalc = sys.argv[2] if len(sys.argv) > 2 else None
    aop_rows, ch_rows = build(out)
    if recalc:
        import os, shutil, tempfile
        tmp = os.path.join(tempfile.mkdtemp(), "calc.xlsx")
        shutil.copy(out, tmp)
        subprocess.run([sys.executable, recalc, tmp, "90"], check=True)
        fill_samples(out, tmp, aop_rows, ch_rows)
        subprocess.run([sys.executable, recalc, out, "90"], check=True)
    print("Đã tạo", out)
