# Copyright (c) Opendatalab. All rights reserved.
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


API_PROTOCOL_VERSION = 1
DEFAULT_MAX_CONCURRENT_REQUESTS = 3
DEFAULT_PROCESSING_WINDOW_SIZE = 64


class CompatContentChunk(BaseModel):
    """A page-level Markdown chunk returned by the legacy content API."""

    model_config = ConfigDict(extra="allow")

    chunk_id: int = Field(description="Zero-based chunk number within the file.")
    page_idx: int = Field(description="Zero-based source page number.")
    page_size: Any = Field(description="Source page size as emitted by the parser.")
    bbox: list[float] = Field(
        default_factory=list,
        description="Chunk bounding box in source-page coordinates.",
    )
    markdown: str = Field(description="Markdown representation of this chunk.")
    content_type: str | None = Field(
        default=None,
        description="MinerU block type, for example text, title, table, or image.",
    )


class CompatFileContent(BaseModel):
    """Parsing outputs for one uploaded file."""

    model_config = ConfigDict(extra="allow")

    md_content: str | None = Field(
        default=None,
        description="Complete Markdown output for the file.",
    )
    chunk: list[CompatContentChunk] | None = Field(
        default=None,
        description=(
            "Page-level content chunks. Present in results rebuilt by mineru-api."
        ),
    )
    middle_json: Any | None = Field(
        default=None,
        description=(
            "MinerU intermediate JSON. Present when mineru-router rebuilds a "
            "persisted result directly."
        ),
    )
    images: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Extracted images keyed by filename. Each value is a data URL such as "
            "data:image/png;base64,..."
        ),
    )


class CompatContentResult(BaseModel):
    """Successful content payload."""

    model_config = ConfigDict(extra="allow")

    backend: str = Field(description="Backend that parsed the document.")
    version: str = Field(description="MinerU version that produced the result.")
    results: dict[str, CompatFileContent] = Field(
        description="Parsing outputs keyed by the original uploaded filename."
    )


class CompatContentError(BaseModel):
    """Failure information stored as the content payload."""

    model_config = ConfigDict(extra="allow")

    error: str = Field(description="Task failure or persisted-result error message.")


class CompatContentResponse(BaseModel):
    """Response returned by /content and /content_router."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "FINISHED",
                    "content": {
                        "backend": "vlm-auto-engine",
                        "version": "3.x.x",
                        "results": {
                            "example.pdf": {
                                "md_content": "# Example\n\nParsed text.",
                                "middle_json": {"pdf_info": []},
                                "images": {
                                    "image_0.png": "data:image/png;base64,iVBORw0KGgo..."
                                },
                            }
                        },
                    },
                },
                {
                    "status": "FINISHED",
                    "content": {
                        "backend": "vlm-auto-engine",
                        "version": "3.x.x",
                        "results": {
                            "example.pdf": {
                                "md_content": "# Example\n\nParsed text.",
                                "chunk": [
                                    {
                                        "chunk_id": 0,
                                        "page_idx": 0,
                                        "page_size": [595.0, 842.0],
                                        "bbox": [72.0, 72.0, 523.0, 120.0],
                                        "markdown": "# Example",
                                        "content_type": "title",
                                    }
                                ],
                                "images": {
                                    "image_0.png": "data:image/png;base64,iVBORw0KGgo..."
                                },
                            }
                        },
                    },
                },
                {"status": "RUNNING", "content": None},
                {"status": "FAIL", "content": {"error": "Parsing failed"}},
            ]
        }
    )

    status: Literal["PENDING", "RUNNING", "FINISHED", "FAIL"] = Field(
        description=(
            "Legacy task state: PENDING (queued), RUNNING (parsing), FINISHED "
            "(successful), or FAIL (failed)."
        )
    )
    content: CompatContentResult | CompatContentError | None = Field(
        description=(
            "null while the task is pending/running; a result object when FINISHED; "
            "or an error object when FAIL."
        )
    )
