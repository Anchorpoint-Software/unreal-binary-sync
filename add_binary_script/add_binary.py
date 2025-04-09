import apsync as aps
import anchorpoint as ap
import sys
import json
import re
import os
from datetime import datetime

def parse_arguments(json_str):
    try:
        # Clean up the input string
        if json_str.startswith("'") and json_str.endswith("'"):
            json_str = json_str[1:-1]
        json_str = json_str.strip()
        
        # Fix the JSON string by adding quotes around keys and values
        fixed_args = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)
        fixed_args = re.sub(r':\s*([^"\d{][^,}\s]*)([,\s}])', r': "\1"\2', fixed_args)
        fixed_args = re.sub(r':\s*(\d{4}-\d{2}-\d{2})([,\s}])', r': "\1"\2', fixed_args)
        
        # Parse the JSON
        return json.loads(fixed_args)
    except Exception as e:
        # Fallback to manual parsing
        result = {}
        pairs = json_str.strip('{} ').split(',')
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                key = key.strip().strip('"\'')
                value = value.strip().strip('"\'')
                result[key] = value
        return result

def main():
    # Get and fix the JSON string
    if len(sys.argv) < 2:
        raise ValueError("No arguments provided")
        
    arguments = sys.argv[1]
    data = parse_arguments(arguments)
    
    # Get values with defaults
    commit_msg = data.get("commitMsg", "")
    commit_id = data.get("commitId", "")
    commit_author = data.get("commitAuthor", "")
    commit_date = data.get("commitDate", "")
    commit_type = data.get("commitType", "")
    
    # Initialize Anchorpoint
    database = ap.get_api()
    task_list_name = "Binaries"
    
    # Get project and task list
    project = aps.get_project(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    task_list = database.tasks.get_task_list(project.path, task_list_name)
    
    # Check if the task_list is empty and create a new one if necessary
    if not task_list:
        task_list = database.tasks.create_task_list(project.path, task_list_name)

    # Create task and set properties
    task = database.tasks.create_task(task_list, commit_msg)
    database.tasks.set_task_icon(task, aps.Icon(icon_path=":/icons/organizations-and-products/unrealEngine.svg",color=""))   

    # Set task attributes
    database.attributes.set_attribute_value(task,"Author", commit_author)
    database.attributes.set_attribute_value(task, "Date", datetime.strptime(commit_date, "%Y-%m-%d"))
    database.attributes.set_attribute_value(task,"Commit ID", commit_id)
    #database.attributes.set_attribute_value(task,"Commit Type", commit_type)
    sys.__stdout__.write(commit_date)
    sys.__stdout__.write("Binary added to list\n")

if __name__ == "__main__":
    main()


