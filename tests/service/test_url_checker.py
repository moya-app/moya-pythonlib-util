import pytest

from moya.service.url_checker import check_forbidden_url


async def test_check_forbidden_url() -> None:
    # Test some things that should work
    await check_forbidden_url("http://google.com/foo.jpg")  # Valid URL
    await check_forbidden_url("http://oesrucdoau/foo.jpg")  # Invalid URL

    for non_http_url in ("foo.jpg", "file:///foo.jpg", "ftp://foo.jpg"):
        with pytest.raises(ValueError, match="Only HTTP and HTTPS URLs are supported"):
            await check_forbidden_url(non_http_url)

    # Bad port
    with pytest.raises(ValueError, match="Forbidden URL"):
        await check_forbidden_url("http://google.com:22/foo.jpg")

    # Via simple matching
    with pytest.raises(ValueError, match="Invalid Hostname"):
        await check_forbidden_url("http://test.local/foo.jpg")

    with pytest.raises(ValueError, match="Invalid Hostname"):
        await check_forbidden_url("http://localhost:8080/foo.jpg")

    # Via DNS lookup
    with pytest.raises(ValueError, match="Forbidden URL"):
        await check_forbidden_url("http://localtest.me/foo.jpg")
