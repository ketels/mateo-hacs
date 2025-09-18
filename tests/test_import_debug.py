def test_import_debug():
    import importlib, sys, pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    assert str(root) in sys.path
    mod = importlib.import_module("custom_components.mateo_meals")
    assert mod is not None
