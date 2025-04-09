import apsync as aps
import anchorpoint as ap
import sys
import json
import re
import os

def main():
    # Get and fix the JSON string
    arguments = sys.argv[1]
    fixed_args = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', arguments)
    fixed_args = re.sub(r':\s*([^"\d{][^,}\s]*)([,\s}])', r': "\1"\2', fixed_args)
    
    # Parse the JSON
    data = json.loads(fixed_args)
    
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
    database.attributes.set_attribute_value(task,"Date", commit_date)
    database.attributes.set_attribute_value(task,"Commit ID", commit_id)
    #database.attributes.set_attribute_value(task,"Commit Type", commit_type)
    
    sys.__stdout__.write("Binary added to list\n")

if __name__ == "__main__":
    main()


