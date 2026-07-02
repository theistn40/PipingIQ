import pandas as pd
from database import DatabaseManager, QueryResult, EngineeringSpecification, size_matches


def test_size_matches():
    assert size_matches("", 3.0)
    assert size_matches("ALL", 4.5)
    assert size_matches("<=2", 2.0)
    assert size_matches("<=2", 1.5)
    assert not size_matches("<=2", 2.5)
    assert size_matches(">2", 3.0)
    assert not size_matches(">2", 2.0)
    assert size_matches("2", 2.0)
    assert not size_matches("2", 2.5)


def test_query_by_service_and_size(tmp_path):
    df = pd.DataFrame([
        {"Spec": "S1", "Service": "Steam Low Pressure", "Service_Abbv": "STM LP", "Size": "<=2", "Pipe": "A"},
        {"Spec": "S2", "Service": "Steam Low Pressure", "Service_Abbv": "STM LP", "Size": ">2", "Pipe": "B"},
    ])
    csv_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(csv_path, index=False)

    manager = DatabaseManager(path=csv_path, autoload=True)
    result = manager.query(service="STM LP", size=1.5)
    assert result.success
    assert result.specifications[0].spec == "S1"
    assert result.specifications[0].get("Pipe") == "A"

    result = manager.query(service="STM LP", size=3.0)
    assert result.success
    assert result.specifications[0].spec == "S2"


def test_query_by_spec_returns_error_for_missing_spec(tmp_path):
    df = pd.DataFrame([
        {"Spec": "S1", "Service": "Steam Low Pressure", "Service_Abbv": "STM LP", "Size": "<=2", "Pipe": "A"},
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = manager.query(spec="S2", size=1.5)
    assert not result.success
    assert "Specification not found" in result.message
