from mineru.cli.api_protocol import CompatContentResponse
from mineru.cli.router import RouterSettings, create_app


def build_router_openapi() -> dict:
    app = create_app(
        RouterSettings(
            local_gpus="none",
            upstream_urls=("http://127.0.0.1:9999",),
        )
    )
    return app.openapi()


def test_every_router_operation_has_summary_and_description():
    schema = build_router_openapi()

    operations = [
        operation
        for path_item in schema["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]

    assert operations
    assert all(operation.get("summary") for operation in operations)
    assert all(operation.get("description") for operation in operations)


def test_router_upload_endpoints_document_multipart_fields():
    schema = build_router_openapi()

    for path in ("/tasks", "/file_parse", "/file_parse_router"):
        form_schema = schema["paths"][path]["post"]["requestBody"]["content"][
            "multipart/form-data"
        ]["schema"]
        assert "files" in form_schema["required"]
        assert form_schema["properties"]["files"]["items"] == {
            "type": "string",
            "format": "binary",
        }

    task_fields = schema["paths"]["/tasks"]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]["schema"]["properties"]
    assert {"backend", "parse_method", "return_md", "response_format_zip"} <= set(
        task_fields
    )

    compat_fields = schema["paths"]["/file_parse_router"]["post"]["requestBody"][
        "content"
    ]["multipart/form-data"]["schema"]["properties"]
    assert {"files", "ocr_id", "ocr_ids"} == set(compat_fields)


def test_content_response_schema_and_states_are_documented():
    schema = build_router_openapi()
    operation = schema["paths"]["/content_router"]["get"]

    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/CompatContentResponse"}

    response_schema = schema["components"]["schemas"]["CompatContentResponse"]
    assert set(response_schema["properties"]) == {"status", "content"}
    assert response_schema["properties"]["status"]["enum"] == [
        "PENDING",
        "RUNNING",
        "FINISHED",
        "FAIL",
    ]
    assert response_schema["examples"][0]["status"] == "FINISHED"


def test_content_response_model_accepts_each_payload_shape():
    for status in ("PENDING", "RUNNING"):
        response = CompatContentResponse.model_validate(
            {"status": status, "content": None}
        )
        assert response.content is None

    finished = CompatContentResponse.model_validate(
        {
            "status": "FINISHED",
            "content": {
                "backend": "vlm-auto-engine",
                "version": "3.1.14",
                "results": {
                    "example.pdf": {
                        "md_content": "# Example",
                        "chunk": [],
                        "images": {},
                    }
                },
            },
        }
    )
    assert finished.content is not None

    failed = CompatContentResponse.model_validate(
        {"status": "FAIL", "content": {"error": "parse failed"}}
    )
    assert failed.content is not None


def test_worker_content_endpoint_uses_the_shared_response_schema():
    from mineru.cli.fast_api import app as worker_app

    operation = worker_app.openapi()["paths"]["/content"]["get"]

    assert operation["summary"] == "Poll legacy parsing content"
    assert operation["parameters"][0]["name"] == "ocr_id"
    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/CompatContentResponse"}
