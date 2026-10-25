"""Build the single-owner Space runtime archive without local secrets or outputs."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import zipfile


REQUIRED = (
    "app.py", "Dockerfile", ".dockerignore", "requirements.txt", "constraints.txt",
    ".streamlit/config.toml", "README.md", "docs/HUGGING_FACE.md", "docs/DEPLOYMENT.md",
)
SPACE_HEADER = """---
title: Axiom Research
emoji: "\U0001f4ca"
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

"""


def build_archive(root: Path, destination: Path) -> int:
    root = root.resolve()
    sources = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "src"],
        cwd=root,
    ).decode("utf-8").split("\0")
    paths = sorted(set(REQUIRED) | {name for name in sources if name})
    for name in paths:
        path = root / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Missing or unsupported runtime file: {name}")
        if any(part.startswith(".env") or part in {"__pycache__", "secrets.toml"}
               for part in path.relative_to(root).parts) or path.suffix.lower() in {
                   ".pyc", ".pyo", ".pem", ".key", ".log",
               }:
            raise ValueError(f"Private or generated file is not a runtime input: {name}")
    destination = destination.resolve()
    if destination.is_relative_to(root / "src") or destination in [root / p for p in paths]:
        raise ValueError("Archive destination must not overwrite runtime source.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".zip", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in paths:
                if name == "README.md":
                    archive.writestr(name, SPACE_HEADER + (root / name).read_text(encoding="utf-8"))
                else:
                    archive.write(root / name, name)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("Runtime archive failed its integrity check.")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return len(paths)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("exports/axiom-huggingface-runtime.zip"))
    args = parser.parse_args()
    count = build_archive(Path(__file__).resolve().parents[1], args.output)
    print(f"Created {args.output} ({count} runtime files; no deployment performed).")
