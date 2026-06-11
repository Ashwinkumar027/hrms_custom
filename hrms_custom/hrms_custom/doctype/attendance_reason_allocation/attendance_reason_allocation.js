frappe.ui.form.on("Attendance Reason Allocation", {
    refresh(frm) {
        toggle_allocation_fields(frm);
    },

    onload(frm) {
        toggle_allocation_fields(frm);
    },

    applies_to(frm) {
        clear_irrelevant_fields(frm);
        toggle_allocation_fields(frm);
    },

    employee(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value("Employee", frm.doc.employee, "employee_name")
                .then(r => {
                    frm.set_value("employee_name", r.message.employee_name || "");
                });
        } else {
            frm.set_value("employee_name", "");
        }
    }
});

function toggle_allocation_fields(frm) {
    const applies_to = frm.doc.applies_to;

    const show_employee = applies_to === "Employee";
    const show_department = applies_to === "Department";

    frm.set_df_property("employee", "hidden", !show_employee);
    frm.set_df_property("employee_name", "hidden", !show_employee);
    frm.set_df_property("department", "hidden", !show_department);

    frm.set_df_property("employee", "reqd", show_employee);
    frm.set_df_property("department", "reqd", show_department);

    ["employee", "employee_name", "department"].forEach(fieldname => {
        if (frm.fields_dict[fieldname]) {
            frm.fields_dict[fieldname].refresh();
        }
    });
}

function clear_irrelevant_fields(frm) {
    if (frm.doc.applies_to === "Employee") {
        frm.set_value("department", "");
    }

    if (frm.doc.applies_to === "Department") {
        frm.set_value("employee", "");
        frm.set_value("employee_name", "");
    }

    if (frm.doc.applies_to === "Company") {
        frm.set_value("employee", "");
        frm.set_value("employee_name", "");
        frm.set_value("department", "");
    }
}
