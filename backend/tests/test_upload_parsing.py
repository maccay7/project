import sys
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.upload_details import parse_upload_file


class FakeFileStorage:
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content

    def read(self):
        return self._content


def test_parse_upload_file_returns_sheet_metadata_for_excel_workbooks():
    workbook = Workbook()
    first_sheet = workbook.active
    first_sheet.title = "Summary"
    first_sheet.append(["Instrument", "Principal"])
    first_sheet.append(["Bond A", 1000])

    second_sheet = workbook.create_sheet("Details")
    second_sheet.append(["Name", "Rate"])
    second_sheet.append(["Bond B", 0.07])

    buffer = BytesIO()
    workbook.save(buffer)

    result = parse_upload_file(FakeFileStorage("sample.xlsx", buffer.getvalue()))

    assert result["success"] is True
    assert result["sheet_names"] == ["Summary", "Details"]
    assert result["sheets"][0]["name"] == "Summary"
    assert result["sheets"][0]["headers"] == ["Instrument", "Principal"]
    assert result["sheets"][1]["rows"] == 1
