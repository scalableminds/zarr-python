import os
from collections.abc import Iterable
from unittest import mock
from unittest.mock import Mock

import numpy as np
import pytest

from zarr import Array, zeros
from zarr.abc.codec import CodecInput, CodecOutput, CodecPipeline
from zarr.abc.store import ByteSetter
from zarr.array_spec import ArraySpec
from zarr.buffer import NDBuffer
from zarr.codecs import BatchedCodecPipeline, BloscCodec, BytesCodec, Crc32cCodec, ShardingCodec
from zarr.config import BadConfigError, config
from zarr.indexing import SelectorTuple
from zarr.registry import (
    get_buffer_class,
    get_codec_class,
    get_ndbuffer_class,
    get_pipeline_class,
    register_buffer,
    register_codec,
    register_ndbuffer,
    register_pipeline,
)
from zarr.testing.buffer import MyBuffer, MyNDArrayLike, MyNDBuffer, StoreExpectingMyBuffer


@pytest.fixture()
def reset_config():
    config.reset()
    yield
    config.reset()


def test_config_defaults_set():
    # regression test for available defaults
    assert config.defaults == [
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
    ]
    assert config.get("array.order") == "C"


def test_config_defaults_can_be_overridden():
    assert config.get("array.order") == "C"
    with config.set({"array.order": "F"}):
        assert config.get("array.order") == "F"


@pytest.mark.parametrize("store", ("local", "memory"), indirect=["store"])
def test_config_codec_pipeline_class(store):
    # has default value
    assert get_pipeline_class().__name__ != ""

    config.set({"codec_pipeline.name": "BatchedCodecPipeline"})
    assert get_pipeline_class() == BatchedCodecPipeline

    _mock = Mock()

    class MockCodecPipeline(BatchedCodecPipeline):
        async def write(
            self,
            batch_info: Iterable[tuple[ByteSetter, ArraySpec, SelectorTuple, SelectorTuple]],
            value: NDBuffer,
            drop_axes: tuple[int, ...] = (),
        ) -> None:
            _mock.call()

    register_pipeline(MockCodecPipeline)
    config.set({"codec_pipeline.name": "MockCodecPipeline"})
    assert get_pipeline_class() == MockCodecPipeline

    # test if codec is used
    arr = Array.create(
        store=store,
        shape=(100,),
        chunks=(10,),
        zarr_format=3,
        dtype="i4",
    )
    arr[:] = range(100)

    _mock.call.assert_called()

    with pytest.raises(BadConfigError):
        config.set({"codec_pipeline.name": "wrong_name"})
        get_pipeline_class()

    class MockEnvCodecPipeline(CodecPipeline):
        pass

    register_pipeline(MockEnvCodecPipeline)

    with mock.patch.dict(os.environ, {"ZARR_PYTHON_CODEC_PIPELINE__NAME": "MockEnvCodecPipeline"}):
        assert get_pipeline_class(reload_config=True) == MockEnvCodecPipeline


@pytest.mark.parametrize("store", ("local", "memory"), indirect=["store"])
def test_config_codec_implementation(store):
    # has default value
    assert get_codec_class("blosc").__name__ == config.defaults[0]["codecs"]["blosc"]["name"]

    _mock = Mock()

    class MockBloscCodec(BloscCodec):
        async def _encode_single(
            self, chunk_data: CodecInput, chunk_spec: ArraySpec
        ) -> CodecOutput | None:
            _mock.call()

    config.set({"codecs.blosc.name": "MockBloscCodec"})
    register_codec("blosc", MockBloscCodec)
    assert get_codec_class("blosc") == MockBloscCodec

    # test if codec is used
    arr = Array.create(
        store=store,
        shape=(100,),
        chunks=(10,),
        zarr_format=3,
        dtype="i4",
        codecs=[BytesCodec(), {"name": "blosc", "configuration": {}}],
    )
    arr[:] = range(100)
    _mock.call.assert_called()

    with mock.patch.dict(os.environ, {"ZARR_PYTHON_CODECS__BLOSC__NAME": "BloscCodec"}):
        assert get_codec_class("blosc", reload_config=True) == BloscCodec


@pytest.mark.parametrize("store", ("local", "memory"), indirect=["store"])
def test_config_ndbuffer_implementation(store):
    # has default value
    assert get_ndbuffer_class().__name__ == config.defaults[0]["ndbuffer"]["name"]

    # set custom ndbuffer with MyNDArrayLike implementation
    register_ndbuffer(MyNDBuffer)
    config.set({"ndbuffer.name": "MyNDBuffer"})
    assert get_ndbuffer_class() == MyNDBuffer
    arr = Array.create(
        store=store,
        shape=(100,),
        chunks=(10,),
        zarr_format=3,
        dtype="i4",
    )
    got = arr[:]
    print(type(got))
    assert isinstance(got, MyNDArrayLike)


def test_config_buffer_implementation():
    # has default value
    assert get_buffer_class().__name__ == config.defaults[0]["buffer"]["name"]

    arr = zeros(shape=(100), store=StoreExpectingMyBuffer(mode="w"))

    # AssertionError of StoreExpectingMyBuffer when not using my buffer
    with pytest.raises(AssertionError):
        arr[:] = np.arange(100)

    register_buffer(MyBuffer)
    config.set({"buffer.name": "MyBuffer"})
    assert get_buffer_class() == MyBuffer

    # no error using MyBuffer
    arr[:] = np.arange(100)

    arr_sharding = zeros(
        shape=(100, 10),
        store=StoreExpectingMyBuffer(mode="w"),
        codecs=[ShardingCodec(chunk_shape=(10, 10))],
    )
    arr_sharding[:] = np.arange(1000).reshape(100, 10)

    arr_Crc32c = zeros(
        shape=(100, 10),
        store=StoreExpectingMyBuffer(mode="w"),
        codecs=[BytesCodec(), Crc32cCodec()],
    )
    arr_Crc32c[:] = np.arange(1000).reshape(100, 10)


pass
