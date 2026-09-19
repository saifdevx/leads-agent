from app.outreach.rendering import render_template


def test_render_template_uses_known_variables_and_removes_unknown():
    lead = {"first_name": "Sam", "company_name": "Acme Solar", "region": "Texas", "website": "https://acme.test"}
    sender = {"display_name": "Alex", "email": "alex@example.com"}
    value = render_template("Hi {{ first_name }} at {{company_name}} / {{unknown}} / {{location}} / {{sender_name}}", lead, sender)
    assert value == "Hi Sam at Acme Solar /  / Texas / Alex"
