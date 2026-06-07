from aicommit.llm.ollama import OllamaBackend


def test_generate_replay(cassette):
    cas = cassette("commit_simple")
    backend = OllamaBackend(url="http://test", model="m", temperature=0.0)
    out = backend.generate("anything")
    assert "feat(parser)" in out
    assert cas.idx == 1
    assert cas.requests[0]["stream"] is False
    assert cas.requests[0]["model"] == "m"


def test_stream_yields_chunks(cassette):
    cas = cassette("commit_simple")
    backend = OllamaBackend(url="http://test", model="m", temperature=0.0)
    chunks = list(backend.stream("anything"))
    assert len(chunks) >= 1
    assert "feat(parser)" in "".join(chunks)
    assert cas.requests[0]["stream"] is True


def test_regenerate_uses_different_temperature(cassette):
    cas = cassette("commit_regenerate")
    backend = OllamaBackend(url="http://test", model="m", temperature=0.2)
    backend.generate("p", temperature=0.2)
    backend.generate("p", temperature=0.5)
    assert cas.requests[0]["options"]["temperature"] == 0.2
    assert cas.requests[1]["options"]["temperature"] == 0.5
