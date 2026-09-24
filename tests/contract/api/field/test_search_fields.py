import uuid

from httpx import ASGITransport, AsyncClient

from src.presentation.api.main import app


def _square(min_lon: float, min_lat: float, side: float) -> dict[str, object]:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [min_lon + side, min_lat],
                [min_lon + side, min_lat + side],
                [min_lon, min_lat + side],
                [min_lon, min_lat],
            ]
        ],
    }


async def _create_field(name: str, geometry: dict[str, object]) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/fields",
            json={
                "name": name,
                "owner": "Іванов І.І.",
                "crop": "Пшениця",
                "geometry": geometry,
            },
        )
    field_id: str = response.json()["id"]
    return field_id


async def _find(lat: object, lon: object) -> tuple[int, dict[str, object]]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/fields/find-by-point", params={"lat": lat, "lon": lon}
        )
    return response.status_code, response.json()


async def test_find_by_point_returns_documented_shape() -> None:
    name = f"Поле {uuid.uuid4().hex[:8]}"
    field_id = await _create_field(name, _square(-120.0, 40.0, 0.01))

    status_code, body = await _find(lat=40.002, lon=-119.998)

    assert status_code == 200
    assert list(body) == ["query_point", "fields", "query_time_ms"]
    assert body["query_point"] == {"lon": -119.998, "lat": 40.002}
    assert isinstance(body["query_time_ms"], float)
    assert body["query_time_ms"] >= 0

    [match] = [f for f in body["fields"] if f["id"] == field_id]
    assert list(match) == [
        "id",
        "name",
        "area_ha",
        "crop",
        "owner",
        "distance_to_center_m",
    ]
    assert match["name"] == name
    assert match["crop"] == "Пшениця"
    assert match["owner"] == "Іванов І.І."
    # Point is 0.003 deg from the square's center on each axis -> a few hundred meters.
    assert 200 < match["distance_to_center_m"] < 600


async def test_find_by_point_returns_all_overlapping_fields_nearest_first() -> None:
    outer_id = await _create_field("Outer", _square(-121.0, 41.0, 0.02))
    inner_id = await _create_field("Inner", _square(-120.995, 41.005, 0.004))

    status_code, body = await _find(lat=41.007, lon=-120.993)

    assert status_code == 200
    ids = [f["id"] for f in body["fields"]]
    assert inner_id in ids and outer_id in ids
    assert ids.index(inner_id) < ids.index(outer_id)
    distances = [f["distance_to_center_m"] for f in body["fields"]]
    assert distances == sorted(distances)


async def test_find_by_point_outside_all_fields_returns_empty_list() -> None:
    status_code, body = await _find(lat=-89.0, lon=179.0)
    assert status_code == 200
    assert body["fields"] == []
    assert body["query_point"] == {"lon": 179.0, "lat": -89.0}


async def test_find_by_point_with_out_of_range_latitude_returns_422() -> None:
    status_code, body = await _find(lat=999.0, lon=30.5)
    assert status_code == 422
    assert "Latitude" in body["detail"]


async def test_find_by_point_with_missing_lon_returns_422() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/fields/find-by-point", params={"lat": 1.0})
    assert response.status_code == 422


async def test_find_by_point_with_non_numeric_lat_returns_422() -> None:
    status_code, _body = await _find(lat="abc", lon=30.5)
    assert status_code == 422
