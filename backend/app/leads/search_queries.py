from __future__ import annotations


def generate_search_queries(niche: str, location: str | None = None) -> list[str]:
    """Generate deterministic, free-first search queries.

    This intentionally does not call an AI model or search provider. Users can
    run the queries in their preferred search engine and paste visible results
    back into the application.
    """
    niche = " ".join(niche.split()).strip()
    location = " ".join((location or "").split()).strip()
    place = f' "{location}"' if location else ""

    queries = [
        f'"{niche}"{place} "gmail.com"',
        f'"{niche}"{place} "email"',
        f'"{niche}"{place} "contact"',
        f'"{niche}"{place} "owner" "email"',
        f'site:instagram.com "{niche}"{place} "gmail.com"',
        f'site:facebook.com "{niche}"{place} "gmail.com"',
        f'site:linkedin.com/company "{niche}"{place}',
        f'"{niche}"{place} "website"',
    ]

    # Preserve order while preventing accidental duplicate queries.
    return list(dict.fromkeys(query.strip() for query in queries))
