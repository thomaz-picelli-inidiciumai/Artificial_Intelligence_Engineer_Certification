from srag_agent.report.diagram import build_diagram, save


def test_no_text_overflows_its_box():
    assert build_diagram().overflows() == []


def test_save_writes_pdf_and_png(tmp_path):
    pdf, png = save(tmp_path)
    assert pdf.read_bytes().startswith(b"%PDF")
    assert png.read_bytes().startswith(b"\x89PNG")
