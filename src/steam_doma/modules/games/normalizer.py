def normalize_game(record: object) -> dict | None:
    """Convert a Steam API record into a MongoDB game document."""
    if not isinstance(record, dict):
        return None

    details = record.get("app_details")
    if not isinstance(details, dict) or details.get("success") is not True:
        return None

    data = details.get("data")
    if not isinstance(data, dict) or data.get("type") != "game":
        return None

    appid = record.get("appid")
    if type(appid) is not int or appid <= 0:
        return None

    if data.get("steam_appid", appid) != appid:
        return None

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return None

    price = data.get("price_overview")
    if not isinstance(price, dict) or type(price.get("final")) is not int:
        price = None

    is_free = data.get("is_free")
    if not isinstance(is_free, bool):
        is_free = None

    return {
        "steam_appid": appid,
        "source": "steam",
        "name": name.strip(),
        "type": "game",
        "is_free": is_free,
        "price": price,
        "genres": data.get("genres") if isinstance(data.get("genres"), list) else [],
        "categories": data.get("categories") if isinstance(data.get("categories"), list) else [],
        "platforms": data.get("platforms") if isinstance(data.get("platforms"), dict) else {},
        "steam_data": data,
    }
