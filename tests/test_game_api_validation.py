from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from steam_doma.main import app


@pytest.fixture
def api_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    database_name = f"steam_doma_validation_test_{uuid4().hex}"

    monkeypatch.setenv("MONGO_DB_NAME", database_name)

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    ("query", "expected_message"),
    [
        (
            "{ games(page: 0) { totalCount } }",
            "Page must be at least 1",
        ),
        (
            "{ games(pageSize: 0) { totalCount } }",
            "Page size must be between 1 and 100",
        ),
        (
            "{ games(pageSize: 101) { totalCount } }",
            "Page size must be between 1 and 100",
        ),
        (
            """
            {
              games(filters: {minPriceMinor: -1}) {
                totalCount
              }
            }
            """,
            "Price must be a non-negative integer",
        ),
        (
            """
            {
              games(
                filters: {
                  minPriceMinor: 5000
                  maxPriceMinor: 1000
                }
              ) {
                totalCount
              }
            }
            """,
            "Minimum price cannot exceed maximum price",
        ),
        (
            """
            {
              games(filters: {platforms: ["android"]}) {
                totalCount
              }
            }
            """,
            "Unsupported platform",
        ),
        (
            '{ games(filters: {search: "' + "x" * 101 + '"}) {totalCount} }',
            "Search term is too long",
        ),
    ],
)
def test_invalid_catalog_parameters(
    api_client: TestClient,
    query: str,
    expected_message: str,
) -> None:
    response = api_client.post(
        "/graphql",
        json={"query": query},
    )

    body = response.json()

    assert body.get("errors") is not None
    assert body["errors"][0]["message"] == expected_message


def test_unknown_sort_enum_is_rejected(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
                {
                  games(sortBy: UNKNOWN) {
                    totalCount
                  }
                }
            """,
        },
    )

    body = response.json()

    assert body.get("errors") is not None
    assert "UNKNOWN" in body["errors"][0]["message"]


def test_invalid_graphql_argument_type(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
                {
                  games(page: "first") {
                    totalCount
                  }
                }
            """,
        },
    )

    body = response.json()

    assert body.get("errors") is not None


def test_invalid_game_id_returns_null(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
                {
                  game(id: "not-an-object-id") {
                    id
                    name
                  }
                }
            """,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "data": {"game": None},
    }


def test_empty_catalog_uses_default_pagination(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
                {
                  games {
                    totalCount
                    page
                    pageSize
                    items {
                      id
                    }
                  }
                }
            """,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "games": {
                "totalCount": 0,
                "page": 1,
                "pageSize": 20,
                "items": [],
            }
        }
    }


def test_graphql_schema_has_catalog_fields(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/graphql",
        json={
            "query": """
                query InspectSchema {
                  queryType: __type(name: "Query") {
                    fields {
                      name
                    }
                  }

                  sortType: __type(
                    name: "GameSortField"
                  ) {
                    enumValues {
                      name
                    }
                  }

                  filtersType: __type(
                    name: "GameFiltersInput"
                  ) {
                    inputFields {
                      name
                    }
                  }
                }
            """,
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert "errors" not in body

    data = body["data"]

    query_fields = {field["name"] for field in data["queryType"]["fields"]}

    assert {
        "ping",
        "games",
        "game",
        "catalogFilters",
    } <= query_fields

    sort_fields = {value["name"] for value in data["sortType"]["enumValues"]}

    assert sort_fields == {
        "NAME",
        "PRICE",
        "DISCOUNT",
        "RECOMMENDATIONS",
        "RELEASE_DATE",
    }

    filter_fields = {field["name"] for field in data["filtersType"]["inputFields"]}

    assert {
        "search",
        "genreIds",
        "categoryIds",
        "platforms",
        "minPriceMinor",
        "maxPriceMinor",
        "freeOnly",
        "discountedOnly",
    } <= filter_fields
