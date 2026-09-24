from httpx import ASGITransport, AsyncClient

from src.presentation.api.main import app

VALID_BOUNDARY = {
    "type": "Polygon",
    "coordinates": [
        [
            [30.5234, 50.4501],
            [30.5250, 50.4501],
            [30.5250, 50.4515],
            [30.5234, 50.4515],
            [30.5234, 50.4501],
        ]
    ],
}


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "North Forty",
        "owner": "Ivan Bondarenko",
        "crop": "wheat",
        "geometry": VALID_BOUNDARY,
    }
    payload.update(overrides)
    return payload


async def _post(payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/fields", json=payload)
    return response.status_code, response.json()


async def test_create_field_with_valid_polygon_returns_201() -> None:
    status_code, body = await _post(_valid_payload())
    assert status_code == 201
    assert body["area_ha"] >= 0.1
    assert body["name"] == "North Forty"


async def test_create_field_with_cyrillic_payload_returns_full_record() -> None:
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [30.5234, 50.4501],
                [30.5334, 50.4501],
                [30.5334, 50.4601],
                [30.5234, 50.4601],
                [30.5234, 50.4501],
            ]
        ],
    }
    status_code, body = await _post(
        {
            "name": "Поле No1 - Пшениця",
            "geometry": geometry,
            "crop": "Пшениця",
            "owner": "Іванов І.І.",
        }
    )
    assert status_code == 201
    assert list(body) == [
        "id",
        "name",
        "geometry",
        "area_ha",
        "crop",
        "owner",
        "created_at",
    ]
    assert body["name"] == "Поле No1 - Пшениця"
    assert body["crop"] == "Пшениця"
    assert body["owner"] == "Іванов І.І."
    assert body["geometry"] == geometry
    assert body["area_ha"] > 0.1


async def test_create_field_with_empty_coordinates_returns_422() -> None:
    status_code, _body = await _post(
        _valid_payload(geometry={"type": "Polygon", "coordinates": []})
    )
    assert status_code == 422


async def test_create_field_with_open_polygon_returns_422() -> None:
    open_boundary = {
        "type": "Polygon",
        "coordinates": [VALID_BOUNDARY["coordinates"][0][:-1]],
    }
    status_code, body = await _post(_valid_payload(geometry=open_boundary))
    assert status_code == 422
    assert "closed" in body["detail"].lower()


async def test_create_field_with_self_intersecting_polygon_returns_422() -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [
            [
                [30.5234, 50.4501],
                [30.5250, 50.4515],
                [30.5250, 50.4501],
                [30.5234, 50.4515],
                [30.5234, 50.4501],
            ]
        ],
    }
    status_code, body = await _post(_valid_payload(geometry=bowtie))
    assert status_code == 422
    assert "self-intersect" in body["detail"].lower()


async def test_create_field_below_minimum_area_returns_422() -> None:
    tiny = {
        "type": "Polygon",
        "coordinates": [
            [
                [30.5234, 50.4501],
                [30.52341, 50.4501],
                [30.52341, 50.45011],
                [30.5234, 50.45011],
                [30.5234, 50.4501],
            ]
        ],
    }
    status_code, body = await _post(_valid_payload(geometry=tiny))
    assert status_code == 422
    assert "0.1 ha" in body["detail"]


async def test_create_field_missing_attribute_returns_422() -> None:
    payload = _valid_payload()
    del payload["owner"]
    status_code, body = await _post(payload)
    assert status_code == 422
