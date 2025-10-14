from app.models import Example

def test_example_model():
    e = Example(name="Test", description="Desc")
    assert e.name == "Test"
    assert e.description == "Desc"
