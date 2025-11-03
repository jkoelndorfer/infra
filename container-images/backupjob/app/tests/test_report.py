"""
Tests backup reporting code.
"""

from typing import Optional

import pytest

from backup.report import (
    BackupReport,
    BackupReportFieldAnnotation as A,
    BackupReportField as F,
)


@pytest.fixture
def backup_report() -> BackupReport:
    """
    Returns a BackupReport for use in testing.
    """
    return BackupReport("Test Report")


class TestBackupReportField:
    """
    Tests the BackupReportField class.
    """

    @pytest.mark.parametrize(
        "f1, f2, eq",
        [
            # Test case 1: two fields with the same constructor definition are equal.
            (F("t1", 0, lambda x: A.OK), F("t1", 0, lambda x: A.OK), True),
            # Test case 2: two fields with the same values, but a different annotation
            # are not equal.
            (F("t1", 0, lambda x: A.OK), F("t1", 0, lambda x: A.ERROR), False),
            # Test case 3: two fields with the same label but different data are not equal.
            (F("t1", 0, None), F("t1", 1, None), False),
        ],
    )
    def test_eq(self, f1: F, f2: F, eq: bool) -> None:
        """
        Tests that backup fields compare equal correctly.
        """

        assert (f1 == f2) is eq

    def test_eq_dissimilar_object_type(self) -> None:
        """
        Tests that a backup field is not equal to a dissimilar object type.
        """
        f = F("dissimilar", "not equal", None)

        assert f != "dissimilar"

    @pytest.mark.parametrize(
        "data, expected_an",
        [
            (0, A.OK),
            (1, A.WARNING),
            (2, A.ERROR),
            (3, None),
        ],
    )
    def test_int_annotation(self, data: int, expected_an: A) -> None:
        """
        Tests that BackupReportField objects are correctly annotated.
        """

        def annotator(data: int) -> Optional[A]:
            match data:
                case 0:
                    return A.OK
                case 1:
                    return A.WARNING
                case 2:
                    return A.ERROR
            return None

        f = F("test int", data, annotator)

        assert f.annotation == expected_an

    def test_no_annotator(self) -> None:
        """
        Tests that BackupReportFields are not annotated if no annotator is provided.
        """
        f = F("test no annotation", 0, None)

        assert f.annotation is None

    @pytest.mark.parametrize("label", ["Backup OK", "# Errors"])
    def test_repr(self, label: str) -> None:
        """
        Tests that the BackupReportField's __repr__ method produces an appropriate string representation.
        """
        f = F(label, "dummy data", None)

        assert f.__repr__() == f"BackupReportField(label={label})"


class TestBackupReport:
    """
    Tests the BackupReport class.
    """

    def test_default_unsuccessful(self) -> None:
        """
        Tests that the backup report defaults to being unsuccessful.
        """
        report = BackupReport("Default State")

        assert not report.successful

    @pytest.mark.parametrize("name", ["TestReport1", "AnotherTestReport"])
    def test_name(self, name: str) -> None:
        """
        Tests that the backup report name set via the constructor is reflected in the name attribute.
        """

        report = BackupReport(name)

        assert report.name == name

    def test_find_one_field_single_report(self, backup_report: BackupReport) -> None:
        """
        Tests that find_one_field can find a backup report field when searching a single report.
        """
        backup_report.new_field("New Files", 1000, lambda x: None)
        backup_report.new_field("Changed Files", 50, lambda x: None)

        f = backup_report.find_one_field(lambda x: x.data == 50)

        assert f is not None
        assert f.label == "Changed Files"
        assert f.data == 50

    def test_find_one_field_one_report_scope(self, backup_report: BackupReport) -> None:
        """
        Tests that find_one_field limits its scope only to the current report when
        include_subreports is False.
        """
        sub_a = backup_report.new_subreport("SubA")
        sub_a.new_field("Files Added", 1000, lambda x: None)

        def flt(f: F):
            return f.label == "Files Added"

        f_main = backup_report.find_one_field(flt, include_subreports=False)
        f_sub = sub_a.find_one_field(flt, include_subreports=False)

        assert f_main is None
        assert f_sub is not None
        assert f_sub.label == "Files Added"
        assert f_sub.data == 1000

    def test_find_one_field_multiple_subreports(
        self, backup_report: BackupReport
    ) -> None:
        """
        Tests that find_one_field can find a backup report field when searching nested subreports.
        """
        sub_a = backup_report.new_subreport("SubA")
        sub_a1 = sub_a.new_subreport("SubA1")

        sub_a1.new_field("Files Added", 1000, lambda x: None)

        f = backup_report.find_one_field(
            lambda x: x.label == "Files Added", include_subreports=True
        )

        assert f is not None
        assert f.label == "Files Added"
        assert f.data == 1000

    @pytest.mark.parametrize(
        "field",
        [
            F("t1", 0, lambda x: A.OK if x == 0 else A.ERROR),
            F("t2", True, lambda x: A.OK if not x else A.WARNING),
        ],
    )
    def test_new_field_returns_expected_field(
        self, backup_report: BackupReport, field: F
    ) -> None:
        """
        Tests that new_field returns a field matching what was specified.
        """

        new_field = backup_report.new_field(field.label, field.data, field.annotator)

        assert field == new_field

    @pytest.mark.parametrize(
        "field",
        [
            F("t1", 0, lambda x: A.OK if x == 0 else A.ERROR),
            F("t2", True, lambda x: A.OK if not x else A.WARNING),
        ],
    )
    def test_new_field_added_to_report_fields(
        self, backup_report: BackupReport, field: F
    ) -> None:
        """
        Tests that new_field returns a field matching what was specified.
        """
        backup_report.new_field(field.label, field.data, field.annotator)

        assert field in backup_report.fields

    def test_new_subreport_in_all_reports(self, backup_report: BackupReport) -> None:
        """
        Tests that backup reports added via new_subreport are reflected in all_reports.
        """
        expected_report_names = [backup_report.name]

        a1 = backup_report.new_subreport("A1")
        expected_report_names.append(a1.name)

        b1 = a1.new_subreport("B1")
        expected_report_names.append(b1.name)

        c1 = a1.new_subreport("C1")
        expected_report_names.append(c1.name)

        a2 = backup_report.new_subreport("A2")
        expected_report_names.append(a2.name)

        actual_report_names = list(map(lambda r: r.name, backup_report.all_reports()))

        assert actual_report_names == expected_report_names
