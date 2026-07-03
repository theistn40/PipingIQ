import pandas as pd
from database import DatabaseManager, QueryResult, EngineeringSpecification, size_matches
from knowledge_router import route_query
from parser import parse_question
from search_engine import search


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


def test_search_matches_service_name_for_spec_request(tmp_path):
    df = pd.DataFrame([
        {"Spec": "FO-1", "Service": "Fuel Oil", "Service_Abbv": "FO", "Size": "ALL", "Pipe": "Copper"},
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = search(manager, "WHAT PIPE SPEC FOR FUEL OIL")

    assert result["success"]
    assert result["spec"] == "FO-1"
    assert result["service"] == "Fuel Oil"


def test_search_does_not_treat_pipe_spec_as_pipe_field_request(tmp_path):
    df = pd.DataFrame([
        {"Spec": "FO-1", "Service": "Fuel Oil", "Service_Abbv": "FO", "Size": "ALL", "Pipe": "Copper"},
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = search(manager, "pipe spec for fuel oil")

    assert result["success"]
    assert result["field"] is None
    assert result["value"] is None
    assert result["spec"] == "FO-1"


def test_search_matches_spaced_abbreviation_and_fraction_size(tmp_path):
    df = pd.DataFrame([
        {"Spec": "S1", "Service": "Steam, Low Pressure", "Service_Abbv": "STM LP", "Size": "<=2", "Flange": "Class 150"},
        {"Spec": "S2", "Service": "Steam, Low Pressure", "Service_Abbv": "STM LP", "Size": ">2", "Flange": "Class 300"},
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = search(manager, "STM LP flange for 1 1/2")

    assert result["success"]
    assert result["field"] == "Flange"
    assert result["value"] == "Class 150"
    assert result["spec"] == "S1"


def test_parse_question_accepts_inch_variants():
    assert parse_question('fuel oil 2 inch')["size"] == 2.0
    assert parse_question('fuel oil 2"')["size"] == 2.0
    assert parse_question('fuel oil 1 1/2 inch')["size"] == 1.5


def test_search_uses_all_dataframe_headers_for_field_detection(tmp_path):
    df = pd.DataFrame([
        {
            "Spec": "A1",
            "Service": "Fuel Oil",
            "Service_Abbv": "FO",
            "Size": "ALL",
            "MAXIMUM PRESSURE (PSI)": "150 psig",
        }
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = search(manager, "what is the maximum pressure for fuel oil 2 inch")

    assert result["success"]
    assert result["field"] == "MAXIMUM PRESSURE (PSI)"
    assert result["value"] == "150 psig"


def test_search_uses_all_services_from_service_column(tmp_path):
    df = pd.DataFrame([
        {
            "Spec": "A2",
            "Service": "Argon",
            "Service_Abbv": "",
            "Size": "ALL",
            "Test Pressure": "200 psig",
        }
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = search(manager, "argon test pressure")

    assert result["success"]
    assert result["service"] == "Argon"
    assert result["field"] == "Test Pressure"
    assert result["value"] == "200 psig"


def test_spec_search_returns_all_matching_service_rows(tmp_path):
    df = pd.DataFrame([
        {"Spec": "FO-1", "Service": "Fuel Oil", "Service_Abbv": "FO", "Size": "<=2", "Pipe": "Copper"},
        {"Spec": "FO-2", "Service": "Fuel Oil", "Service_Abbv": "FO", "Size": ">2", "Pipe": "Steel"},
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = search(manager, "what spec for fo")

    assert result["success"]
    assert len(result["results"]) == 2
    assert {row["spec"] for row in result["results"]} == {"FO-1", "FO-2"}


def test_plural_spec_queries_return_all_matching_service_rows(tmp_path):
    df = pd.DataFrame([
        {"Spec": "FO-1", "Service": "Fuel Oil", "Service_Abbv": "FO", "Size": "<=2", "Pipe": "Copper"},
        {"Spec": "FO-2", "Service": "Fuel Oil", "Service_Abbv": "FO", "Size": ">2", "Pipe": "Steel"},
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = search(manager, "specs for fo")

    assert result["success"]
    assert len(result["results"]) == 2
    assert {row["spec"] for row in result["results"]} == {"FO-1", "FO-2"}


def test_codes_and_standards_returns_pipe_values_for_service(tmp_path):
    df = pd.DataFrame([
        {"Spec": "FO-1", "Service": "Fuel Oil", "Service_Abbv": "FO", "Size": "<=2", "Pipe": "Copper"},
        {"Spec": "FO-2", "Service": "Fuel Oil", "Service_Abbv": "FO", "Size": ">2", "Pipe": "Steel"},
    ])
    file_path = tmp_path / "PipeSpec_Master.xlsx"
    df.to_excel(file_path, index=False)

    manager = DatabaseManager(path=file_path, autoload=True)
    result = route_query("fo", "Codes & Standards", manager)

    assert result["success"]
    assert len(result["results"]) == 2
    assert {row["value"] for row in result["results"]} == {"Copper", "Steel"}
