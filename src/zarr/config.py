from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from donfig import Config as DConfig

if TYPE_CHECKING:
    from zarr.abc.codec import CodecPipeline


class BadConfigError(ValueError):
    _msg = "bad Config: %r"


class Config(DConfig):  # type: ignore[misc]
    """Will collect configuration from config files and environment variables

    Example environment variables:
    Grabs environment variables of the form "DASK_FOO__BAR_BAZ=123" and
    turns these into config variables of the form ``{"foo": {"bar-baz": 123}}``
    It transforms the key and value in the following way:

    -  Lower-cases the key text
    -  Treats ``__`` (double-underscore) as nested access
    -  Calls ``ast.literal_eval`` on the value

    """
    @property
    def codec_pipeline_class(self) -> type[CodecPipeline]:
        from zarr.abc.codec import CodecPipeline

        name = self.get("codec_pipeline.name")
        name_camel_case = camel_case(name)
        selected_pipelines = [
            p for p in CodecPipeline.__subclasses__() if p.__name__ in (name, name_camel_case)
        ]

        if not selected_pipelines:
            raise BadConfigError(
                f'No subclass of CodecPipeline with name "{name}" or "{name_camel_case}" found.'
            )
        if len(selected_pipelines) > 1:
            raise BadConfigError(
                f'Multiple subclasses of CodecPipeline with name "{name}" or '
                f'"{name_camel_case}" found: {selected_pipelines}.'
            )
        return selected_pipelines[0]


config = Config(
    "zarr_python",
    defaults=[
        {
            "array": {"order": "C"},
            "async": {"concurrency": None, "timeout": None},
            "codec_pipeline": {"name": "BatchedCodecPipeline", "batch_size": 1},
            "codecs": {
                "blosc": {"name": "BloscCodec"},
                "gzip": {"name": "GzipCodec"},
                "zstd": {"name": "ZstdCodec"},
                "bytes": {"name": "BytesCodec"},
                "endian": {"name": "BytesCodec"},  # compatibility with earlier versions of ZEP1
                "crc32c": {"name": "Crc32cCodec"},
                "sharding_indexed": {"name": "ShardingCodec"},
                "transpose": {"name": "TransposeCodec"},
            },
        }
    ],
)


def parse_indexing_order(data: Any) -> Literal["C", "F"]:
    if data in ("C", "F"):
        return cast(Literal["C", "F"], data)
    msg = f"Expected one of ('C', 'F'), got {data} instead."
    raise ValueError(msg)

def camel_case(string: str) -> str:
    return string.replace("_", " ").title().replace(" ", "")