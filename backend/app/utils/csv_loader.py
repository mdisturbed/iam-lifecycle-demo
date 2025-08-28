import csv
import re
from io import StringIO
from typing import List, Dict

REQUIRED = [
    "hr_user_id","first_name","last_name","email","department","department_code","title","job_code","location","employment_type","status"
]

# Input validation patterns
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
NAME_PATTERN = re.compile(r'^[a-zA-Z\s\-\']{1,50}$')
DEPT_PATTERN = re.compile(r'^[a-zA-Z\s&]{1,50}$')
DEPT_CODE_PATTERN = re.compile(r'^[0-9]{4}$')  # Exactly 4 digits
JOB_CODE_PATTERN = re.compile(r'^[0-9]{5}$')  # Exactly 5 digits
STATUS_PATTERN = re.compile(r'^(Active|Terminated|Inactive)$')

def validate_user_data(user: Dict[str, str]) -> Dict[str, str]:
    """Validate and sanitize user data"""
    errors = []
    
    # Email validation
    if not EMAIL_PATTERN.match(user.get('email', '')):
        errors.append(f"Invalid email: {user.get('email')}")
    
    # Name validation
    for field in ['first_name', 'last_name']:
        if not NAME_PATTERN.match(user.get(field, '')):
            errors.append(f"Invalid {field}: {user.get(field)}")
    
    # Department validation  
    if not DEPT_PATTERN.match(user.get('department', '')):
        errors.append(f"Invalid department: {user.get('department')}")
    
    # Department code validation (4 digits)
    if not DEPT_CODE_PATTERN.match(user.get('department_code', '')):
        errors.append(f"Invalid department_code (must be 4 digits): {user.get('department_code')}")
    
    # Job code validation (5 digits)
    if not JOB_CODE_PATTERN.match(user.get('job_code', '')):
        errors.append(f"Invalid job_code (must be 5 digits): {user.get('job_code')}")
    
    # Status validation
    if not STATUS_PATTERN.match(user.get('status', '')):
        errors.append(f"Invalid status: {user.get('status')}")
    
    # HR User ID should be alphanumeric
    hr_id = user.get('hr_user_id', '')
    if not hr_id.isalnum() or len(hr_id) > 20:
        errors.append(f"Invalid hr_user_id: {hr_id}")
    
    if errors:
        raise ValueError(f"Validation errors for user {user.get('email', 'unknown')}: {'; '.join(errors)}")
    
    return user

def parse_hr_csv(content: str) -> List[Dict[str, str]]:
    """Parse and validate HR CSV content"""
    # Size limit (1MB)
    if len(content) > 1024 * 1024:
        raise ValueError("CSV file too large (max 1MB)")
    
    reader = csv.DictReader(StringIO(content))
    
    # Check required columns
    if not reader.fieldnames:
        raise ValueError("Empty CSV file")
        
    for r in REQUIRED:
        if r not in reader.fieldnames:
            raise ValueError(f"Missing column: {r}")
    
    users: List[Dict[str, str]] = []
    row_count = 0
    
    for row in reader:
        row_count += 1
        
        # Limit number of rows
        if row_count > 1000:
            raise ValueError("Too many rows (max 1000)")
        
        # Sanitize and validate
        user = {k: (row.get(k) or "").strip()[:100] for k in REQUIRED}  # Truncate long values
        user = validate_user_data(user)
        users.append(user)
    
    return users
