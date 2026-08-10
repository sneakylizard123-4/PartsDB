from urllib.parse import urlsplit

import httpx

TIMEOUT = httpx.Timeout(20.0)
MAX_DATASHEET_BYTES = 50 * 1024 * 1024  # 50 MB
USER_AGENT = "PartsDB/1.0 (datasheet fetcher)"


class DatasheetFetchError(Exception):
    pass


def _validate_url(url: str) -> None:
    scheme = urlsplit(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise DatasheetFetchError("Only http(s) datasheet URLs are supported")


def fetch_datasheet(url: str) -> tuple[bytes, str]:
    """Download a datasheet. Returns (content, content_type).

    Raises DatasheetFetchError on network errors, non-2xx status, or when
    the response exceeds the size limit.
    """
    _validate_url(url)
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(
            timeout=TIMEOUT, follow_redirects=True, headers=headers
        ) as client:
            with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise DatasheetFetchError(
                        f"Supplier returned HTTP {response.status_code}"
                    )
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_DATASHEET_BYTES:
                    raise DatasheetFetchError(
                        "Datasheet exceeds the 50 MB size limit"
                    )
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > MAX_DATASHEET_BYTES:
                        raise DatasheetFetchError(
                            "Datasheet exceeds the 50 MB size limit"
                        )
                    chunks.append(chunk)
                return b"".join(chunks), (response.headers.get("content-type") or "")
    except DatasheetFetchError:
        raise
    except httpx.TimeoutException as exc:
        raise DatasheetFetchError("Datasheet download timed out") from exc
    except httpx.HTTPError as exc:
        raise DatasheetFetchError(f"Datasheet download failed: {exc}") from exc


def datasheet_filename(url: str, fallback: str | None = None) -> str:
    """Derive a filename from a datasheet URL."""
    name = urlsplit(url).path.rsplit("/", 1)[-1]
    if name and "." in name and len(name) <= 256:
        return name
    return f"{fallback or 'datasheet'}.pdf"
