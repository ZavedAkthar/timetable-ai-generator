import mysql.connector
from mysql.connector import errorcode
from flask import render_template, request, redirect, url_for, flash
from utils.helpers import fetch_all, execute


def get_options(field):
    options = field.get("options", [])
    return options() if callable(options) else options


def build_fields(cfg):
    defaults = {"min": 1, "max": 1000}
    return [{**defaults, **f, "options": get_options(f)} for f in cfg["fields"]]


def read_form(cfg):
    values, errors = {}, []
    for f in build_fields(cfg):
        name, label = f["name"], f["label"]
        raw = request.form.get(name, "").strip()
        values[name] = raw
        if not raw:
            errors.append(f"{label} is required.")
        elif f["type"] == "number":
            try:
                number = int(raw)
            except ValueError:
                errors.append(f"{label} must be a whole number.")
                continue
            if not f["min"] <= number <= f["max"]:
                errors.append(f"{label} must be between {f['min']} and {f['max']}.")
            values[name] = number
        elif f["type"] == "select":
            if raw not in [str(v) for v, _ in f["options"]]:
                errors.append(f"Choose a valid {label}.")
    return values, errors


def db_message(err, cfg):
    if err.errno == errorcode.ER_DUP_ENTRY:
        return cfg["dup_message"]
    if err.errno == errorcode.ER_NO_REFERENCED_ROW_2:
        return "A selected item no longer exists."
    return "Database error. Please try again."


def register_crud(bp, cfg):
    cfg.setdefault("badges", [])
    cfg.setdefault("defaults", {})
    names = [f["name"] for f in cfg["fields"]]
    table = cfg["table"]
    list_url = f"{bp.name}.list_items"

    def form_page(form, errors, title):
        return render_template("crud_form.html", cfg=cfg, fields=build_fields(cfg),
                               form=form, errors=errors, title=title, list_url=list_url)

    @bp.route("", endpoint="list_items")
    def list_items():
        q = request.args.get("q", "").strip()
        params = [f"%{q}%"] * cfg["list_sql"].count("%s")
        try:
            rows = fetch_all(cfg["list_sql"], params)
        except mysql.connector.Error:
            flash("Could not load records.", "error")
            rows = []
        return render_template("crud_list.html", cfg=cfg, rows=rows, q=q)

    @bp.route("/add", methods=["GET", "POST"], endpoint="add_item")
    def add_item():
        form, errors = dict(cfg["defaults"]), []
        if request.method == "POST":
            form, errors = read_form(cfg)
            if not errors:
                cols = ", ".join(names)
                marks = ", ".join(["%s"] * len(names))
                try:
                    execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})",
                            [form[n] for n in names])
                    flash(f"{cfg['singular']} added.", "success")
                    return redirect(url_for(list_url))
                except mysql.connector.Error as err:
                    errors.append(db_message(err, cfg))
        return form_page(form, errors, f"Add {cfg['singular']}")

    @bp.route("/<int:item_id>/edit", methods=["GET", "POST"], endpoint="edit_item")
    def edit_item(item_id):
        rows = fetch_all(f"SELECT * FROM {table} WHERE id = %s", (item_id,))
        if not rows:
            flash(f"{cfg['singular']} not found.", "error")
            return redirect(url_for(list_url))
        form, errors = rows[0], []
        if request.method == "POST":
            form, errors = read_form(cfg)
            if not errors:
                sets = ", ".join(f"{n} = %s" for n in names)
                try:
                    execute(f"UPDATE {table} SET {sets} WHERE id = %s",
                            [form[n] for n in names] + [item_id])
                    flash(f"{cfg['singular']} updated.", "success")
                    return redirect(url_for(list_url))
                except mysql.connector.Error as err:
                    errors.append(db_message(err, cfg))
        return form_page(form, errors, f"Edit {cfg['singular']}")

    @bp.route("/<int:item_id>/delete", methods=["POST"], endpoint="delete_item")
    def delete_item(item_id):
        try:
            execute(f"DELETE FROM {table} WHERE id = %s", (item_id,))
            flash(f"{cfg['singular']} deleted.", "success")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ROW_IS_REFERENCED_2:
                flash(cfg.get("in_use_message", "Cannot delete: this record is in use."), "error")
            else:
                flash("Database error. Please try again.", "error")
        return redirect(url_for(list_url))