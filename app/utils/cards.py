from typing import Dict, List, Any


def build_card(card_type: str, title: str, city: str, details: str, link: str) -> str:
    return "\n".join(
        [
            "[CARD]",
            f"type: {card_type}",
            f"title: {title}",
            f"city: {city}",
            f"details: {details}",
            f"link: {link}",
            "[/CARD]",
        ]
    )


def cards_from_places(card_type: str, fallback_city: str, places: List[Dict[str, Any]]) -> str:
    blocks: List[str] = []
    for place in places:
        details_bits = []
        rating = place.get("rating")
        if rating:
            details_bits.append(f"⭐ {rating}")
        price = place.get("price_level")
        if price:
            details_bits.append(str(price))
        address = place.get("address")
        if address:
            details_bits.append(address)
        details = ", ".join(details_bits) or "Popular local recommendation"
        city_value = place.get("city") or fallback_city
        blocks.append(
            build_card(
                card_type,
                place.get("name", "Unnamed"),
                city_value or "",
                details,
                place.get("maps_url", "https://maps.google.com"),
            )
        )
    return "\n".join(blocks)
