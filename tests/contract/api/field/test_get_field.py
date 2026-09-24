import uuid

from httpx import ASGITransport, AsyncClient

from src.presentation.api.main import app

VALID_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [
        [
            [10.0, -10.0],
            [10.001, -10.0],
            [10.001, -9.999],
            [10.0, -9.999],
            [10.0, -10.0],
        ]
    ],
}


async def _create_field(
    name: str = "Detail Lookup Field",
    owner: str = "Ivan Bondarenko",
    crop: str = "wheat",
) -> dict[str, object]:
    payload = {
        "name": name,
        "owner": owner,
        "crop": crop,
        "geometry": VALID_GEOMETRY,
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/fields", json=payload)
    assert response.status_code == 201, response.text
    result: dict[str, object] = response.json()
    return result


async def _get(field_id: str) -> tuple[int, dict[str, object]]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/fields/{field_id}")
    return response.status_code, response.json()


async def test_get_existing_field_returns_full_details() -> None:
    created = await _create_field()
    status_code, body = await _get(str(created["id"]))
    assert status_code == 200
    assert body["id"] == created["id"]
    assert body["name"] == "Detail Lookup Field"
    assert body["owner"] == "Ivan Bondarenko"
    assert body["crop"] == "wheat"
    assert body["area_ha"] > 0


async def test_get_existing_field_body_equals_post_response() -> None:
    created = await _create_field()
    status_code, body = await _get(str(created["id"]))
    assert status_code == 200
    assert set(body) == {"id", "name", "geometry", "area_ha", "crop", "owner", "created_at"}
    assert body == created


async def test_get_returns_exactly_the_requested_field_among_several() -> None:
    first = await _create_field(name="First Field", crop="barley")
    second = await _create_field(name="Second Field", crop="rye")

    status_first, body_first = await _get(str(first["id"]))
    status_second, body_second = await _get(str(second["id"]))

    assert status_first == 200
    assert status_second == 200
    assert body_first == first
    assert body_second == second


async def test_get_field_round_trips_unicode_attributes() -> None:
    created = await _create_field(
        name="Поле Північне", owner="Іван Бондаренко", crop="пшениця озима"
    )
    status_code, body = await _get(str(created["id"]))
    assert status_code == 200
    assert body["name"] == "Поле Північне"
    assert body["owner"] == "Іван Бондаренко"
    assert body["crop"] == "пшениця озима"
    assert body == created


async def test_get_nonexistent_field_returns_404() -> None:
    missing_id = str(uuid.uuid4())
    status_code, body = await _get(missing_id)
    assert status_code == 404
    assert body == {"detail": f"No field found with id {missing_id}."}


async def test_get_malformed_field_id_returns_422() -> None:
    status_code, body = await _get("not-a-uuid")
    assert status_code == 422
    assert isinstance(body["detail"], list)
    assert body["detail"][0]["loc"] == ["path", "field_id"]
