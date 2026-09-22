"""End-to-end integration test for source ingestion."""

import json
from pathlib import Path
from program_graph.analysis.ingestion import Language, ProjectIngestor


def test_project_ingestor_with_compilation_db(tmp_path: Path):
    src = tmp_path / "src" / "algorithm.cpp"
    src.parent.mkdir(parents=True)
    src.write_text("int compute() { return 42; }")

    db_path = tmp_path / "compile_commands.json"
    db_path.write_text(
        json.dumps(
            [
                {
                    "directory": str(tmp_path),
                    "command": f"g++ -O3 -Iinclude -std=c++17 -c {src} -o algo.o",
                    "file": str(src),
                }
            ]
        )
    )

    ingestor = ProjectIngestor(project_root=tmp_path)
    source = ingestor.ingest(src)

    assert source.path == src.resolve()
    assert source.language == Language.CPP
    assert "-O3" in source.compiler_flags
    assert "-Iinclude" in source.compiler_flags
    assert "-std=c++17" in source.compiler_flags


def test_project_ingestor_standalone_fallback(tmp_path: Path):
    src = tmp_path / "standalone.c"
    src.write_text("int main() { return 0; }")

    ingestor = ProjectIngestor(project_root=tmp_path)
    source = ingestor.ingest(src, fallback_flags=["-g"])

    assert source.path == src.resolve()
    assert source.language == Language.C
    assert source.compiler_flags == ["-g"]