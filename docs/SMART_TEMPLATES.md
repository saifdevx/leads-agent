# Lead Gen — Smart Templates

This update fixes two production issues:

1. human-style placeholders such as `{{Business Name}}` are now supported;
2. HTML template bodies are sent as real HTML instead of literal `<br>` / `<strong>` text.

## Recommended variables

- `{{greeting}}` — safest greeting. Uses first name when available, otherwise the inferred company name, otherwise `Hi there,`.
- `{{company_name}}` — uses the saved company name, then falls back to domain / website / email / social evidence, then `your company`.
- `{{first_name}}`
- `{{last_name}}`
- `{{contact_name}}`
- `{{job_title}}`
- `{{niche}}` — inherited from the lead list/search niche
- `{{email}}`
- `{{phone}}`
- `{{website}}`
- `{{domain}}`
- `{{location}}` — uses lead city/region/country, then the lead-list location
- `{{linkedin_url}}`
- `{{instagram_url}}`
- `{{facebook_url}}`
- `{{sender_name}}`
- `{{sender_email}}`

Legacy aliases such as `{{Business Name}}`, `{{Company Name}}`, `{{business_name}}`, `{{First Name}}`, and `{{Job Title}}` are normalized automatically.

## Smart company-name fallback

Lead Gen does not invent a company name. It tries, in order:

1. extracted company name;
2. business domain / website;
3. non-public business email domain;
4. public email username when it looks business-specific;
5. Instagram / LinkedIn / Facebook handle;
6. natural copy fallback: `your company`.

Example:

`saadremodeling@gmail.com` -> `Saad Remodeling`

If the evidence is only `info@gmail.com`, Lead Gen will use `your company` rather than hallucinating a brand.

## HTML email support

Safe email HTML is supported for:

- `<br>`
- `<p>`
- `<strong>` / `<b>`
- `<em>` / `<i>`
- `<u>`
- `<a href="...">`
- lists / blockquotes / spans

Dangerous tags/attributes are removed. A plain-text fallback is generated automatically for mail clients that do not render HTML.

## Important after deployment

Campaign email bodies are rendered when the campaign draft is created. Existing campaigns created before this update keep their already-rendered message bodies.

After deploying this fix:

1. keep or edit the saved template;
2. delete/recreate any old test campaign;
3. preview the new campaign before approving it.
