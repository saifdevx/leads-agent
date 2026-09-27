from app.outreach.rendering import render_template


def test_render_template_uses_known_variables_and_removes_unknown():
    lead = {"first_name": "Sam", "company_name": "Acme Solar", "region": "Texas", "website": "https://acme.test"}
    sender = {"display_name": "Alex", "email": "alex@example.com"}
    value = render_template("Hi {{ first_name }} at {{company_name}} / {{unknown}} / {{location}} / {{sender_name}}", lead, sender)
    assert value == "Hi Sam at Acme Solar /  / Texas / Alex"


def test_business_name_alias_and_gmail_local_fallback():
    lead = {"email": "saadremodeling@gmail.com"}
    sender = {"display_name": "Verxas", "email": "hello@verxas.com"}
    assert render_template("Hi {{Business Name}} team,", lead, sender) == "Hi Saad Remodeling team,"
    assert render_template("{{greeting}}", lead, sender) == "Hi Saad Remodeling team,"


def test_company_name_prefers_custom_domain_before_public_email_local():
    lead = {
        "email": "info@gmail.com",
        "website": "https://stxpressurepros.com/contact",
    }
    sender = {"display_name": "Verxas", "email": "hello@verxas.com"}
    assert render_template("{{company_name}}", lead, sender) == "STX Pressure Pros"


def test_company_name_has_natural_fallback_when_no_business_evidence_exists():
    lead = {"email": "info@gmail.com"}
    sender = {"display_name": "Verxas", "email": "hello@verxas.com"}
    assert render_template("I came across {{company_name}}.", lead, sender) == "I came across your company."
    assert render_template("{{greeting}}", lead, sender) == "Hi there,"


def test_html_content_is_sanitized_and_plain_text_fallback_is_generated():
    from app.outreach.rendering import prepare_email_content

    plain, rich = prepare_email_content(
        'Hi<br><br><strong>Free sample</strong><script>alert(1)</script>'
        '<br><a href="https://verxas.com" target="_blank" onclick="bad()">Verxas</a>'
    )
    assert "Hi\n\nFree sample" in plain
    assert "script" not in (rich or "").lower()
    assert "onclick" not in (rich or "").lower()
    assert 'href="https://verxas.com"' in (rich or "")


def test_unsupported_tokens_are_reported_but_business_name_alias_is_supported():
    from app.outreach.rendering import unsupported_tokens

    assert unsupported_tokens("Hello {{Business Name}}") == []
    assert unsupported_tokens("Hello {{Business Name}} {{Magic Field}}") == ["Magic Field"]
