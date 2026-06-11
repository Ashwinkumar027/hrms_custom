frappe.ui.form.on("Employee Allowed Shift Location", {
    onload(frm) {
        set_default_applies_to(frm);
        toggle_location_fields(frm);
    },

    refresh(frm) {
        set_default_applies_to(frm);
        toggle_location_fields(frm);
    },

    applies_to(frm) {
        clear_irrelevant_fields(frm);
        toggle_location_fields(frm);
    },
});

function set_default_applies_to(frm) {
    if (!frm.doc.applies_to) {
        frm.set_value("applies_to", "Employee");
    }
}

function toggle_location_fields(frm) {
    const show_employee = frm.doc.applies_to === "Employee";
    const show_company = frm.doc.applies_to === "Company";

    frm.set_df_property("employee", "hidden", !show_employee);
    frm.set_df_property("employee_name", "hidden", !show_employee);
    frm.set_df_property("company", "hidden", !show_company);
    frm.set_df_property("shift_location", "hidden", true);

    frm.set_df_property("employee", "reqd", show_employee);
    frm.set_df_property("company", "reqd", show_company);

    ["employee", "employee_name", "company", "shift_location", "locations"].forEach((fieldname) => {
        if (frm.fields_dict[fieldname]) {
            frm.fields_dict[fieldname].refresh();
        }
    });
}

function clear_irrelevant_fields(frm) {
    if (frm.doc.applies_to === "Employee") {
        frm.set_value("company", "");
    }

    if (frm.doc.applies_to === "Company") {
        frm.set_value("employee", "");
        frm.set_value("employee_name", "");
    }
}
