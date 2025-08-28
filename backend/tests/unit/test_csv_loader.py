from app.utils.csv_loader import parse_hr_csv

def test_parse_hr_csv_ok():
    data = "hr_user_id,first_name,last_name,email,department,title,location,employment_type,status\n1,A,B,a@b.com,Eng,SE,US,FT,Active\n"
    rows = parse_hr_csv(data)
    assert rows[0]["email"] == "a@b.com"
