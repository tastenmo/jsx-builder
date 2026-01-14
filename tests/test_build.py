"""Test the base html template and config."""

import json

COMMON_CONF_OVERRIDES = dict(
    navigation_with_keys=False,
    surface_warnings=True,
)


def test_build_html(sphinx_build_factory: any, file_regression: any) -> None:
    """Test building the base html template and config."""
    sphinx_build = sphinx_build_factory("base")

    # Basic build with defaults
    sphinx_build.build()
    assert (sphinx_build.outdir / "index.html").exists(), sphinx_build.outdir.glob("*")


def test_jsx(sphinx_build_factory: any) -> None:
    """Test that jjson build passes without error."""
    sphinx_build = sphinx_build_factory("base", buildername="jjson")

    # Basic build with defaults
    sphinx_build.build()

    assert (sphinx_build.outdir / "index.fjson").exists(), list(sphinx_build.outdir.glob("*"))


def test_tutorial_build(sphinx_build_factory: any) -> None:
    """Test building the tutorial site."""
    sphinx_build = sphinx_build_factory("tutorial")

    # Build with defaults
    sphinx_build.build()
    assert (sphinx_build.outdir / "index.html").exists()


def test_tutorial_jjson_jsx_body(sphinx_build_factory: any) -> None:
    """Test that jjson builder generates fjson files with injected JSX in body."""
    sphinx_build = sphinx_build_factory("tutorial", buildername="jjson")

    # Build with jjson builder
    sphinx_build.build()
    
    # Check that fjson output exists
    assert (sphinx_build.outdir / "index.fjson").exists()
    
    # Load and verify the fjson file contains JSX elements in body
    fjson_file = sphinx_build.outdir / "index.fjson"
    with open(fjson_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Verify body exists and contains JSX Section components
    assert 'body' in data, "No 'body' field in fjson output"
    body = data['body']
    assert isinstance(body, str), "Body should be a string"
    assert len(body) > 0, "Body should not be empty"
    
    # Check for JSX Section elements in the body
    assert '<SectionRef' in body, "No SectionRef elements found in body"
