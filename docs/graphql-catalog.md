
# Steam Дома — GraphQL Game Catalog API

## 1. Endpoint

Local development:

`http://localhost:8000/graphql`

HTTP method: `POST`

Content-Type: `application/json`

The API is implemented with FastAPI, Strawberry GraphQL,
and MongoDB using PyMongo Async.

## 2. Available queries

| Query | Description |
| --- | --- |
| `ping` | Check GraphQL availability |
| `games` | Paginated game catalog |
| `game(id: ID!)` | Full details of one game |
| `catalogFilters` | Available genres, categories, platforms |

## 3. Get games

```graphql
query GetGames(
  $page: Int!
  $pageSize: Int!
  $filters: GameFiltersInput
  $sortBy: GameSortField!
  $sortDirection: GameSortOrder!
) {
  games(
    page: $page
    pageSize: $pageSize
    filters: $filters
    sortBy: $sortBy
    sortDirection: $sortDirection
  ) {
    totalCount
    page
    pageSize
    items {
      id
      steamAppid
      name
      isFree
      priceMinor
      originalCurrency
      discountPercent
      headerImage
      releaseDate
      recommendationsTotal
      genres {
        id
        name
      }
      platforms {
        windows
        mac
        linux
      }
    }
  }
}
```

Example variables:

```json
{
  "page": 1,
  "pageSize": 12,
  "filters": {
    "search": "dark",
    "genreIds": ["1"],
    "platforms": ["windows"],
    "minPriceMinor": 1000,
    "maxPriceMinor": 5000,
    "discountedOnly": false
  },
  "sortBy": "RELEASE_DATE",
  "sortDirection": "DESC"
}
```

### Pagination

- `page` defaults to `1`.
- `pageSize` defaults to `20`.
- Valid page size: `1` to `100`.
- `totalCount` is the total number of matching games.
- `items` contains only games from the requested page.

### Filters

| Input field | Type | Description |
| --- | --- | --- |
| `search` | String | Case-insensitive name substring |
| `genreIds` | [String!] | Steam genre IDs |
| `categoryIds` | [Int!] | Steam category IDs |
| `platforms` | [String!] | windows, mac, linux |
| `minPriceMinor` | Int | Minimum price, inclusive |
| `maxPriceMinor` | Int | Maximum price, inclusive |
| `freeOnly` | Boolean | Only free games |
| `discountedOnly` | Boolean | Only discounted games |

Different filter groups use AND.

Multiple values within one genre, category, or platform
filter use OR.

Price values are non-negative integers in minor units:
`999` represents a displayed price of `$9.99`.

Current project convention: all source currencies are
treated as 1:1 for catalog pricing. No live conversion.

A confirmed free game has an effective price of zero.

A game with unknown price is NOT automatically free.

### Sorting

`sortBy` supports:

- `NAME`
- `PRICE`
- `DISCOUNT`
- `RECOMMENDATIONS`
- `RELEASE_DATE`

`sortDirection` supports:

- `ASC`
- `DESC`

Defaults: `NAME` and `ASC`.

Games without a known value for the selected sort field
are placed last, except for name sorting.

The `RECOMMENDATIONS` field means the number of Steam
recommendations, not a positive-review percentage.

Release dates are based on imported Steam data.
They are not automatically refreshed from Steam.

## 4. Get game details

First obtain an `id` from the `games` query.

This is the MongoDB document ID, not `steamAppid`.

```graphql
query GetGame($id: ID!) {
  game(id: $id) {
    id
    steamAppid
    name
    isFree
    priceMinor
    originalCurrency
    discountPercent

    releaseDate
    releaseDateText
    comingSoon

    shortDescription
    detailedDescription
    aboutTheGame

    developers
    publishers
    supportedLanguages
    controllerSupport
    requiredAge
    website

    genres {
      id
      name
    }

    categories {
      id
      name
    }

    platforms {
      windows
      mac
      linux
    }

    screenshots {
      id
      thumbnailUrl
      fullUrl
    }

    trailers {
      id
      name
      thumbnailUrl
      mp4Url
      webmUrl
    }

    pcRequirements {
      minimum
      recommended
    }

    macRequirements {
      minimum
      recommended
    }

    linuxRequirements {
      minimum
      recommended
    }

    recommendationsTotal
    metacriticScore
  }
}
```

Example variables:

```json
{
  "id": "507f1f77bcf86cd799439011"
}
```

Replace the example ID with an ID returned by your catalog.

If a game is missing or the ID is invalid,
`game` returns `null`.

Optional metadata can also be `null`.

Descriptions and system requirements may contain HTML
from Steam. Sanitize this HTML before rendering in React.

## 5. Get available filters

```graphql
query GetCatalogFilters {
  catalogFilters {
    genres {
      id
      name
    }
    categories {
      id
      name
    }
    platforms {
      id
      name
    }
  }
}
```

Genre IDs are strings, e.g. `"1"`.

Category IDs are integers, e.g. `2`.

Platform IDs:

- `windows`
- `mac`
- `linux`

Use returned IDs when creating `GameFiltersInput`.

## 6. Errors

GraphQL responses can contain an `errors` array.

Example of an invalid page:

```graphql
query {
  games(page: 0) {
    totalCount
  }
}
```

Possible response:

```json
{
  "data": null,
  "errors": [
    {
      "message": "Page must be at least 1"
    }
  ]
}
```

Actual error responses may include additional fields
such as locations and execution paths.

Always inspect `errors`, even if the HTTP request itself
was successful.

## 7. React integration

For local Vite development, configure the GraphQL URL:

```env
VITE_GRAPHQL_URL=http://localhost:8000/graphql
```

Example browser request:

```ts
const response = await fetch(
  import.meta.env.VITE_GRAPHQL_URL,
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: `
        query {
          games(page: 1, pageSize: 5) {
            totalCount
            items {
              id
              name
              priceMinor
              headerImage
            }
          }
        }
      `,
    }),
  }
);

if (!response.ok) {
  throw new Error(`HTTP ${response.status}`);
}

const result = await response.json();

if (result.errors?.length) {
  throw new Error(
    result.errors.map((error: { message: string }) =>
      error.message
    ).join("; ")
  );
}

console.log(result.data);
```

The Vite development origin must be permitted by
the Backend CORS configuration.

## 8. Data limitations

- Steam data was initially collected in August 2025.
- Prices and release statuses may be outdated.
- No live currency conversion is implemented.
- Missing prices are different from free games.
- Steam recommendation counts are available only for
  some games.
- Metacritic scores are critic scores, not user ratings.
- Admin changes must not be overwritten by initial
  seeding.

## 9. Local verification

Start the Backend:

```bash
uv run uvicorn steam_doma.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

Open:

`http://localhost:8000/graphql`

Run the Backend tests:

```bash
uv run python -m pytest -v
```
