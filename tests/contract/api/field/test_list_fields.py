import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.presentation.api.main import app

ITEM_KEYS = ["id", "name", "area_ha", "crop", "owner"]


def _marker(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _boundary_at(lat_offset: float) -> dict[str, object]:
    base_lat = -60.0 + lat_offset
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-170.0, base_lat],
                [-169.999, base_lat],
                [-169.999, base_lat + 0.001],
                [-170.0, base_lat + 0.001],
                [-170.0, base_lat],
            ]
        ],
    }


def _sized_boundary(lat_offset: float, side_deg: float) -> dict[str, object]:
    base_lat = -60.0 + lat_offset
    base_lon = -170.0
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [base_lon, base_lat],
                [base_lon + side_deg, base_lat],
                [base_lon + side_deg, base_lat + side_deg],
                [base_lon, base_lat + side_deg],
                [base_lon, base_lat],
            ]
        ],
    }


async def _create_field(
    name: str,
    lat_offset: float,
    crop: str = "wheat",
    owner: str = "Pagination Test Owner",
    geometry: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "owner": owner,
        "crop": crop,
        "geometry": geometry if geometry is not None else _boundary_at(lat_offset),
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/fields", json=payload)
    assert response.status_code == 201, response.text
    result: dict[str, object] = response.json()
    return result


async def _list(**params: object) -> tuple[int, dict[str, object]]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/fields", params=params)
    return response.status_code, response.json()


def _fields(body: dict[str, object]) -> list[dict[str, object]]:
    fields = body["fields"]
    assert isinstance(fields, list)
    return fields


def _names(body: dict[str, object]) -> list[object]:
    return [item["name"] for item in _fields(body)]


async def _seed(count: int, crop: str) -> None:
    for i in range(count):
        await _create_field(f"Seed-{i:02d}", i * 0.001, crop=crop)


# --- response shape --------------------------------------------------------


async def test_list_fields_response_has_exact_shape() -> None:
    crop = _marker("shape")
    created = await _create_field("ShapeField", 0.0, crop=crop, owner="Іванов І.І.")

    status_code, body = await _list(crop=crop)
    assert status_code == 200
    assert list(body.keys()) == ["total", "fields"]
    assert body["total"] == 1
    items = _fields(body)
    assert len(items) == 1
    item = items[0]
    assert list(item.keys()) == ITEM_KEYS
    assert item["id"] == created["id"]
    assert item["name"] == "ShapeField"
    assert item["crop"] == crop
    assert item["owner"] == "Іванов І.І."
    assert isinstance(item["area_ha"], float)
    assert item["area_ha"] == created["area_ha"]


async def test_list_fields_items_have_no_geometry_or_created_at_by_default() -> None:
    status_code, body = await _list()
    assert status_code == 200
    assert isinstance(body["total"], int)
    for item in _fields(body):
        assert list(item.keys()) == ITEM_KEYS


# --- limit / offset --------------------------------------------------------


async def test_list_fields_default_limit_is_20() -> None:
    crop = _marker("deflimit")
    await _seed(25, crop)

    status_code, body = await _list(crop=crop)
    assert status_code == 200
    assert body["total"] == 25
    assert len(_fields(body)) == 20


async def test_list_fields_limit_offset_slices_are_disjoint_and_ordered() -> None:
    crop = _marker("slice")
    await _seed(25, crop)

    _, everything = await _list(crop=crop, limit=100)
    all_ids = [item["id"] for item in _fields(everything)]
    assert _names(everything) == [f"Seed-{i:02d}" for i in range(25)]

    status_code, first = await _list(crop=crop, limit=10, offset=0)
    assert status_code == 200
    status_code, second = await _list(crop=crop, limit=10, offset=10)
    assert status_code == 200
    status_code, third = await _list(crop=crop, limit=10, offset=20)
    assert status_code == 200

    for body in (first, second, third):
        assert body["total"] == 25

    ids_first = [item["id"] for item in _fields(first)]
    ids_second = [item["id"] for item in _fields(second)]
    ids_third = [item["id"] for item in _fields(third)]
    assert len(ids_first) == 10
    assert len(ids_second) == 10
    assert len(ids_third) == 5
    assert set(ids_first).isdisjoint(ids_second)
    assert set(ids_second).isdisjoint(ids_third)
    assert ids_first + ids_second + ids_third == all_ids


async def test_list_fields_offset_not_aligned_to_limit() -> None:
    crop = _marker("unaligned")
    await _seed(10, crop)

    status_code, body = await _list(crop=crop, limit=3, offset=4)
    assert status_code == 200
    assert body["total"] == 10
    assert _names(body) == ["Seed-04", "Seed-05", "Seed-06"]


async def test_list_fields_offset_past_end_returns_empty_with_total() -> None:
    crop = _marker("pastend")
    await _seed(3, crop)

    status_code, body = await _list(crop=crop, limit=20, offset=50)
    assert status_code == 200
    assert body == {"total": 3, "fields": []}


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"limit": 0}, "Limit must be between 1 and 100"),
        ({"limit": 101}, "Limit must be between 1 and 100"),
        ({"offset": -1}, "Offset must be 0 or greater"),
    ],
)
async def test_list_fields_invalid_pagination_returns_422(
    params: dict[str, int], message: str
) -> None:
    status_code, body = await _list(**params)
    assert status_code == 422
    assert isinstance(body["detail"], str)
    assert message in body["detail"]


async def test_list_fields_legacy_page_params_are_ignored() -> None:
    crop = _marker("legacy")
    await _seed(3, crop)

    status_code, body = await _list(crop=crop, page=2, page_size=1)
    assert status_code == 200
    assert list(body.keys()) == ["total", "fields"]
    assert len(_fields(body)) == 3


# --- filters ---------------------------------------------------------------


async def test_list_fields_filter_by_crop_returns_only_matching() -> None:
    marker_crop = _marker("crop")
    await _create_field("CropMatch", 0.0, crop=marker_crop)
    await _create_field("CropNoMatch", 0.1, crop=_marker("other"))

    status_code, body = await _list(crop=marker_crop)
    assert status_code == 200
    assert body["total"] == 1
    assert _names(body) == ["CropMatch"]


async def test_list_fields_filter_by_crop_is_exact_and_case_insensitive() -> None:
    marker_crop = _marker("Crop")
    await _create_field("CropCaseMatch", 0.2, crop=marker_crop)

    _, upper = await _list(crop=marker_crop.upper())
    assert _names(upper) == ["CropCaseMatch"]

    _, partial = await _list(crop=marker_crop[:-1])
    assert partial == {"total": 0, "fields": []}


async def test_list_fields_filter_by_owner_substring_case_insensitive() -> None:
    marker_owner = _marker("Owner")
    await _create_field("OwnerMatch", 0.3, owner=f"Mr {marker_owner} Jr")

    status_code, body = await _list(owner=marker_owner.lower())
    assert status_code == 200
    assert body["total"] == 1
    assert _names(body) == ["OwnerMatch"]


async def test_list_fields_filter_by_crop_and_owner_combined() -> None:
    marker_crop = _marker("crop")
    marker_owner = _marker("owner")
    await _create_field("BothMatch", 0.4, crop=marker_crop, owner=marker_owner)
    await _create_field("CropOnlyMatch", 0.5, crop=marker_crop, owner="Someone Else")

    status_code, body = await _list(crop=marker_crop, owner=marker_owner)
    assert status_code == 200
    assert body["total"] == 1
    assert _names(body) == ["BothMatch"]


async def test_list_fields_filter_with_no_match_returns_empty_not_error() -> None:
    status_code, body = await _list(crop=_marker("no-such-crop"))
    assert status_code == 200
    assert body == {"total": 0, "fields": []}


async def _seed_area_range_fields(marker_crop: str) -> None:
    # At latitude ~-60, side_deg=0.001 -> ~0.6ha, 0.002 -> ~2.5ha, 0.003 -> ~5.5ha.
    await _create_field(
        "SmallArea", 1.0, crop=marker_crop, geometry=_sized_boundary(1.0, 0.001)
    )
    await _create_field(
        "MediumArea", 1.5, crop=marker_crop, geometry=_sized_boundary(1.5, 0.002)
    )
    await _create_field(
        "LargeArea", 2.0, crop=marker_crop, geometry=_sized_boundary(2.0, 0.003)
    )


async def test_list_fields_filter_by_min_area_only() -> None:
    marker_crop = _marker("crop")
    await _seed_area_range_fields(marker_crop)

    status_code, body = await _list(crop=marker_crop, min_area=2.0)
    assert status_code == 200
    assert body["total"] == 2
    assert set(_names(body)) == {"MediumArea", "LargeArea"}


async def test_list_fields_filter_by_max_area_only() -> None:
    marker_crop = _marker("crop")
    await _seed_area_range_fields(marker_crop)

    status_code, body = await _list(crop=marker_crop, max_area=1.0)
    assert status_code == 200
    assert body["total"] == 1
    assert _names(body) == ["SmallArea"]


async def test_list_fields_filter_by_area_range() -> None:
    marker_crop = _marker("crop")
    await _seed_area_range_fields(marker_crop)

    status_code, body = await _list(crop=marker_crop, min_area=1.0, max_area=3.0)
    assert status_code == 200
    assert _names(body) == ["MediumArea"]


async def test_list_fields_area_bounds_are_inclusive() -> None:
    marker_crop = _marker("crop")
    await _seed_area_range_fields(marker_crop)
    _, everything = await _list(crop=marker_crop)
    medium = next(i for i in _fields(everything) if i["name"] == "MediumArea")
    exact = medium["area_ha"]

    status_code, body = await _list(crop=marker_crop, min_area=exact, max_area=exact)
    assert status_code == 200
    assert _names(body) == ["MediumArea"]


async def test_list_fields_inverted_area_range_returns_422() -> None:
    status_code, body = await _list(min_area=5.0, max_area=1.0)
    assert status_code == 422
    assert "greater than maximum" in body["detail"]


async def test_list_fields_area_filter_combined_with_crop_owner_and_paging() -> None:
    marker_crop = _marker("crop")
    marker_owner = _marker("owner")
    for i, name in enumerate(["Combined-A", "Combined-B", "Combined-C"]):
        await _create_field(
            name,
            3.0 + i * 0.01,
            crop=marker_crop,
            owner=marker_owner,
            geometry=_sized_boundary(3.0 + i * 0.01, 0.002),
        )
    await _create_field(
        "WrongOwner",
        3.5,
        crop=marker_crop,
        owner="Someone Else",
        geometry=_sized_boundary(3.5, 0.002),
    )
    await _create_field(
        "TooSmall",
        3.6,
        crop=marker_crop,
        owner=marker_owner,
        geometry=_sized_boundary(3.6, 0.001),
    )

    status_code, body = await _list(
        crop=marker_crop,
        owner=marker_owner,
        min_area=1.0,
        max_area=3.0,
        limit=2,
        offset=1,
    )
    assert status_code == 200
    assert body["total"] == 3
    assert _names(body) == ["Combined-B", "Combined-C"]
