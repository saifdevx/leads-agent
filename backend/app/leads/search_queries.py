from __future__ import annotations


def generate_search_queries(niche: str, location: str | None = None) -> list[str]:
    """Generate high-signal prospecting queries based on the user's proven workflow."""
    niche = " ".join(niche.split()).strip()
    location = " ".join((location or "").split()).strip()
    place = f' "{location}"' if location else ""

    queries = [
        f'site:instagram.com "{niche}"{place} "gmail.com"',
        f'site:instagram.com "{niche}"{place} "email"',
        f'site:facebook.com "{niche}"{place} "gmail.com"',
        f'"{niche}"{place} "gmail.com"',
        f'"{niche}"{place} "email"',
        f'"{niche}"{place} "contact"',
        f'"{niche}"{place} "owner" "email"',
        f'"{niche}"{place} "founder" "email"',
        f'"{niche}"{place} "contact us"',
        f'"{niche}"{place} "website"',
        f'site:linkedin.com/company "{niche}"{place}',
    ]
    return list(dict.fromkeys(query.strip() for query in queries))
