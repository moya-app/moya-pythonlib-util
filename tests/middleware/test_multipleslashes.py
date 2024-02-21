import httpx
from fastapi import FastAPI

from moya.middleware.multipleslashes import MultipleSlashesMiddleware


async def test_if_modified_middleware() -> None:
    def setup_app() -> tuple[FastAPI, httpx.AsyncClient]:
        app = FastAPI()
        client = httpx.AsyncClient(app=app)

        @app.get("/test")
        @app.get("/test/{name}")
        async def read_item() -> str:
            return "test"

        return app, client

    BAD_URLS = ("http://test//test", "http://test/test////foo", "http://test/////test//foo.htm")

    app, client = setup_app()
    for bad_urls in BAD_URLS:
        response = await client.get(bad_urls)
        assert response.status_code == 404, "Before middleware, URL should not work"

    # Adding middleware requires app to be recreated unfortunately
    app, client = setup_app()
    app.add_middleware(MultipleSlashesMiddleware)
    for bad_urls in BAD_URLS:
        response = await client.get(bad_urls)
        assert response.status_code == 200, "Now with the middleware the url should work"
        assert response.json() == "test"
