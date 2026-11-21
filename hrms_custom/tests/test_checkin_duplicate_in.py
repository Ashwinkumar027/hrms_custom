from datetime import datetime, timedelta
import frappe
from frappe.tests.classes.integration_test_case import IntegrationTestCase
from frappe.utils import now_datetime, getdate

TEST_COMPANY = "_Test Limit Company"
TEST_HOLIDAY_LIST = "_Test G3 Holiday List"
SHIFT_STRICT = "_Test G3 Strict Shift"
SHIFT_ALT = "_Test G3 Alternating Shift"
SHIFT_OFF_HOURS = "_Test G3 Off Hours Shift"

EMP_PWA_USER = "test_g3_pwa_emp@example.com"
EMP_ALT_USER = "test_g3_alt_emp@example.com"
EMP_NOSHIFT_USER = "test_g3_noshift_emp@example.com"
HR_USER = "test_g3_hr_user@example.com"


class TestCheckinDuplicateIn(IntegrationTestCase):
    """
    Unit/Integration tests for Issue 5: Duplicate IN check-ins from mobile PWA.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        # 1. Company
        if not frappe.db.exists("Company", TEST_COMPANY):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": TEST_COMPANY,
                "abbr": "_TLC2",
                "default_currency": "INR",
                "country": "India",
            }).insert(ignore_permissions=True)

        # 2. Holiday List
        if not frappe.db.exists("Holiday List", TEST_HOLIDAY_LIST):
            frappe.get_doc({
                "doctype": "Holiday List",
                "holiday_list_name": TEST_HOLIDAY_LIST,
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "country": "India",
            }).insert(ignore_permissions=True)

        # 3. Shifts
        # Shift Strict: 01:00 to 23:00 so test timestamp relative to now_datetime falls within shift
        if not frappe.db.exists("Shift Type", SHIFT_STRICT):
            frappe.get_doc({
                "doctype": "Shift Type",
                "name": SHIFT_STRICT,
                "shift_type_name": SHIFT_STRICT,
                "start_time": "01:00:00",
                "end_time": "23:00:00",
                "begin_check_in_before_shift_start_time": 0,
                "allow_check_out_after_shift_end_time": 0,
                "determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
                "holiday_list": TEST_HOLIDAY_LIST,
                "enable_auto_attendance": 0,
            }).insert(ignore_permissions=True)

        # Shift Alternating
        if not frappe.db.exists("Shift Type", SHIFT_ALT):
            frappe.get_doc({
                "doctype": "Shift Type",
                "name": SHIFT_ALT,
                "shift_type_name": SHIFT_ALT,
                "start_time": "01:00:00",
                "end_time": "23:00:00",
                "begin_check_in_before_shift_start_time": 0,
                "allow_check_out_after_shift_end_time": 0,
                "determine_check_in_and_check_out": "Alternating entries as IN and OUT during the same shift",
                "holiday_list": TEST_HOLIDAY_LIST,
                "enable_auto_attendance": 0,
            }).insert(ignore_permissions=True)

        # Shift Off Hours (fixed 02:00 to 03:00, will not resolve for now_datetime during daytime)
        if not frappe.db.exists("Shift Type", SHIFT_OFF_HOURS):
            frappe.get_doc({
                "doctype": "Shift Type",
                "name": SHIFT_OFF_HOURS,
                "shift_type_name": SHIFT_OFF_HOURS,
                "start_time": "02:00:00",
                "end_time": "03:00:00",
                "begin_check_in_before_shift_start_time": 0,
                "allow_check_out_after_shift_end_time": 0,
                "determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
                "holiday_list": TEST_HOLIDAY_LIST,
                "enable_auto_attendance": 0,
            }).insert(ignore_permissions=True)

        # 4. Users
        cls._create_user(EMP_PWA_USER, ["Employee", "Employee Self Service"])
        cls._create_user(EMP_ALT_USER, ["Employee", "Employee Self Service"])
        cls._create_user(EMP_NOSHIFT_USER, ["Employee", "Employee Self Service"])
        cls._create_user(HR_USER, ["Employee", "HR User", "Employee Self Service"])

        # 5. Employees
        cls.emp_pwa = cls._create_employee("EMP-G3-PWA-001", "PWA", "Employee", EMP_PWA_USER)
        cls.emp_alt = cls._create_employee("EMP-G3-ALT-001", "Alt", "Employee", EMP_ALT_USER)
        cls.emp_noshift = cls._create_employee("EMP-G3-NOSHIFT-001", "NoShift", "Employee", EMP_NOSHIFT_USER)

        # 6. Shift Assignments
        cls._create_shift_assignment(cls.emp_pwa, SHIFT_STRICT)
        cls._create_shift_assignment(cls.emp_alt, SHIFT_ALT)
        # Shift assignment for emp_noshift is with SHIFT_OFF_HOURS (active SA exists so validate_shift_assigned passes, but fetch_shift returns None at current hour)
        cls._create_shift_assignment(cls.emp_noshift, SHIFT_OFF_HOURS)

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        # Clean checkins
        frappe.db.delete("Employee Checkin", {"employee": ["in", [cls.emp_pwa, cls.emp_alt, cls.emp_noshift]]})
        # Clean shift assignments
        frappe.db.delete("Shift Assignment", {"employee": ["in", [cls.emp_pwa, cls.emp_alt, cls.emp_noshift]]})
        # Clean employees
        for emp_id in [cls.emp_pwa, cls.emp_alt, cls.emp_noshift]:
            if emp_id and frappe.db.exists("Employee", emp_id):
                frappe.db.delete("Employee", emp_id)
        # Clean users
        for u in [EMP_PWA_USER, EMP_ALT_USER, EMP_NOSHIFT_USER, HR_USER]:
            if frappe.db.exists("User", u):
                frappe.db.delete("User", u)
        # Clean shifts
        for s in [SHIFT_STRICT, SHIFT_ALT, SHIFT_OFF_HOURS]:
            if frappe.db.exists("Shift Type", s):
                frappe.db.delete("Shift Type", s)
        frappe.db.commit()

    @classmethod
    def _create_user(cls, email, roles):
        if not frappe.db.exists("User", email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "enabled": 1,
                "user_type": "System User",
            })
            user.insert(ignore_permissions=True)
            for r in roles:
                user.add_roles(r)
        else:
            u = frappe.get_doc("User", email)
            for r in roles:
                u.add_roles(r)

    @classmethod
    def _create_employee(cls, emp_id, first_name, last_name, user_id):
        existing = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
        if existing:
            return existing
        emp = frappe.get_doc({
            "doctype": "Employee",
            "employee": emp_id,
            "first_name": first_name,
            "last_name": last_name,
            "company": TEST_COMPANY,
            "status": "Active",
            "date_of_joining": "2026-01-01",
            "date_of_birth": "1990-01-01",
            "gender": "Female",
            "employee_number": emp_id,
            "custom_roles_responsibilities": "Test Roles",
            "ctc": 500000,
            "user_id": user_id,
        }).insert(ignore_permissions=True, ignore_mandatory=True)
        return emp.name

    @classmethod
    def _create_shift_assignment(cls, employee, shift_type):
        frappe.db.delete("Shift Assignment", {"employee": employee})
        doc = frappe.get_doc({
            "doctype": "Shift Assignment",
            "employee": employee,
            "shift_type": shift_type,
            "start_date": "2026-01-01",
            "status": "Active",
            "docstatus": 1,
        })
        doc.insert(ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.flags.in_import = False
        frappe.db.delete("Employee Checkin", {"employee": ["in", [self.emp_pwa, self.emp_alt, self.emp_noshift]]})
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.flags.in_import = False
        frappe.db.delete("Employee Checkin", {"employee": ["in", [self.emp_pwa, self.emp_alt, self.emp_noshift]]})
        frappe.db.commit()

    def _create_checkin(self, employee, time_val, log_type="IN", device_id=None, custom_auto_closed=0):
        doc = frappe.new_doc("Employee Checkin")
        doc.employee = employee
        doc.time = time_val
        doc.log_type = log_type
        if device_id:
            doc.device_id = device_id
        if custom_auto_closed:
            doc.custom_auto_closed = custom_auto_closed
        doc.flags.ignore_permissions = True
        doc.insert()
        return doc

    def test_gap_under_5_min_second_in_is_rejected_as_duplicate(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        self._create_checkin(self.emp_pwa, now - timedelta(minutes=4), "IN")
        with self.assertRaises(frappe.ValidationError):
            self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")

    def test_gap_5_min_or_more_second_in_is_converted_to_out_with_comment(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        self._create_checkin(self.emp_pwa, now - timedelta(minutes=8), "IN")
        second_in = self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")
        second_in.reload()

        self.assertEqual(second_in.log_type, "OUT")
        comments = frappe.get_all(
            "Comment",
            filters={"reference_doctype": "Employee Checkin", "reference_name": second_in.name},
            fields=["content"],
        )
        self.assertTrue(len(comments) > 0)
        self.assertIn("log_type changed from IN to OUT", comments[0].content)

    def test_conversion_comment_records_original_value(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        self._create_checkin(self.emp_pwa, now - timedelta(minutes=8), "IN")
        second_in = self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")
        second_in.reload()

        comments = frappe.get_all(
            "Comment",
            filters={"reference_doctype": "Employee Checkin", "reference_name": second_in.name},
            fields=["content"],
        )
        self.assertTrue(len(comments) > 0)
        self.assertIn("original value: IN", comments[0].content)

    def test_device_id_set_is_never_touched(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        doc1 = self._create_checkin(self.emp_pwa, now - timedelta(minutes=4), "IN", device_id="BIO-001")
        doc2 = self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN", device_id="BIO-001")
        doc1.reload()
        doc2.reload()

        self.assertEqual(doc1.log_type, "IN")
        self.assertEqual(doc2.log_type, "IN")

    def test_other_user_session_is_never_touched(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)
        self._create_checkin(self.emp_pwa, now - timedelta(minutes=4), "IN")

        # Administrator inserting on behalf of employee
        frappe.set_user("Administrator")
        doc_admin = self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")
        doc_admin.reload()
        self.assertEqual(doc_admin.log_type, "IN")

        # HR user inserting on behalf of employee
        frappe.set_user(HR_USER)
        doc_hr = self._create_checkin(self.emp_pwa, now - timedelta(minutes=1), "IN")
        doc_hr.reload()
        self.assertEqual(doc_hr.log_type, "IN")

    def test_shift_not_strictly_log_type_is_never_touched(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_ALT_USER)

        doc1 = self._create_checkin(self.emp_alt, now - timedelta(minutes=4), "IN")
        doc2 = self._create_checkin(self.emp_alt, now - timedelta(minutes=2), "IN")
        doc1.reload()
        doc2.reload()

        self.assertEqual(doc1.log_type, "IN")
        self.assertEqual(doc2.log_type, "IN")

    def test_log_older_than_10_minutes_is_never_touched(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        doc1 = self._create_checkin(self.emp_pwa, now - timedelta(minutes=18), "IN")
        doc2 = self._create_checkin(self.emp_pwa, now - timedelta(minutes=12), "IN")
        doc1.reload()
        doc2.reload()

        self.assertEqual(doc1.log_type, "IN")
        self.assertEqual(doc2.log_type, "IN")

    def test_import_insert_is_never_touched(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        self._create_checkin(self.emp_pwa, now - timedelta(minutes=4), "IN")

        frappe.flags.in_import = True
        try:
            doc2 = self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")
            doc2.reload()
            self.assertEqual(doc2.log_type, "IN")
        finally:
            frappe.flags.in_import = False

    def test_auto_closed_previous_out_is_ignored(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        self._create_checkin(self.emp_pwa, now - timedelta(minutes=8), "IN")
        # Auto-closed OUT (created by scheduler)
        self._create_checkin(self.emp_pwa, now - timedelta(minutes=7), "OUT", custom_auto_closed=1)

        # Second human IN 6 min after first IN
        second_in = self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")
        second_in.reload()

        # Because auto-closed OUT is ignored, latest real log is IN, gap >= 5 min -> converted to OUT
        self.assertEqual(second_in.log_type, "OUT")

    def test_previous_log_is_real_out_second_in_is_kept_as_in(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        self._create_checkin(self.emp_pwa, now - timedelta(minutes=8), "IN")
        # Legitimate OUT
        self._create_checkin(self.emp_pwa, now - timedelta(minutes=6), "OUT", custom_auto_closed=0)

        second_in = self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")
        second_in.reload()

        self.assertEqual(second_in.log_type, "IN")

    def test_shift_not_resolvable_is_never_touched(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_NOSHIFT_USER)

        doc1 = self._create_checkin(self.emp_noshift, now - timedelta(minutes=4), "IN")
        doc2 = self._create_checkin(self.emp_noshift, now - timedelta(minutes=2), "IN")
        doc1.reload()
        doc2.reload()

        self.assertIsNone(doc1.shift)
        self.assertEqual(doc1.log_type, "IN")
        self.assertEqual(doc2.log_type, "IN")

    def test_first_in_of_shift_instance_is_kept_as_in(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        doc = self._create_checkin(self.emp_pwa, now - timedelta(minutes=4), "IN")
        doc.reload()
        self.assertEqual(doc.log_type, "IN")

    def test_second_in_same_second_is_rejected(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_PWA_USER)

        self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")
        with self.assertRaises(frappe.ValidationError):
            self._create_checkin(self.emp_pwa, now - timedelta(minutes=2), "IN")

    def test_four_identical_timestamps_only_first_is_kept(self):
        now = now_datetime().replace(microsecond=0)
        target_time = now - timedelta(minutes=2)
        frappe.set_user(EMP_PWA_USER)

        kept = 0
        rejected = 0
        for _ in range(4):
            try:
                self._create_checkin(self.emp_pwa, target_time, "IN")
                kept += 1
            except frappe.ValidationError:
                rejected += 1

        self.assertEqual(kept, 1)
        self.assertEqual(rejected, 3)
        count = frappe.db.count("Employee Checkin", {"employee": self.emp_pwa, "time": target_time})
        self.assertEqual(count, 1)

    def test_in_one_second_after_real_out_is_kept_as_in(self):
        now = now_datetime().replace(microsecond=0)
        out_time = now - timedelta(minutes=2)
        in_time = out_time + timedelta(seconds=1)
        frappe.set_user(EMP_PWA_USER)

        self._create_checkin(self.emp_pwa, out_time, "OUT", custom_auto_closed=0)
        # deliberate known gap pending an HR decision
        second_in = self._create_checkin(self.emp_pwa, in_time, "IN")
        second_in.reload()

        self.assertEqual(second_in.log_type, "IN")

    def test_in_after_auto_closed_out_with_no_shift_is_never_touched(self):
        now = now_datetime().replace(microsecond=0)
        frappe.set_user(EMP_NOSHIFT_USER)

        self._create_checkin(self.emp_noshift, now - timedelta(minutes=6), "OUT", custom_auto_closed=1)
        second_in = self._create_checkin(self.emp_noshift, now - timedelta(minutes=2), "IN")
        second_in.reload()

        self.assertEqual(second_in.log_type, "IN")
