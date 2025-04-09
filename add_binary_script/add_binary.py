import apsync as aps
import anchorpoint as ap
import sys
import json
import os

def main():
    arguments = sys.argv[1] 
    arguments = arguments.replace("\\", "\\\\")
    database = ap.get_api()
    commit_msg = ""
    commit_id = ""
    commit_author = ""
    commit_date = ""
    commit_type = ""
    task_list_name = "Binaries"
    
    sys.__stdout__.write(arguments)
    # Parse the JSON string
    try:
        parsed_arguments = json.loads(arguments)
        if "commitMsg" in parsed_arguments:
            commit_msg = parsed_arguments["commitMsg"]
        if "commitId" in parsed_arguments:
            commit_id = parsed_arguments["commitId"]
        if "commitAuthor" in parsed_arguments:
            commit_author = parsed_arguments["commitAuthor"]
        if "commitDate" in parsed_arguments:
            commit_date = parsed_arguments["commitDate"]
        if "commitType" in parsed_arguments:
            commit_type = parsed_arguments["commitType"]
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON.")


    
    # project = aps.get_project(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # task_list = database.tasks.get_task_list(project.path, task_list_name)
    
    # # Check if the task_list is empty and create a new one if necessary
    # if not task_list:
    #     task_list = database.tasks.create_task_list(project.path, task_list_name)

    # task = database.tasks.create_task(task_list, commit_msg)
    # database.tasks.set_task_icon(task, aps.Icon(icon_path=":/icons/organizations-and-products/unrealEngine.svg",color=""))   

    # database.attributes.set_attribute_value(task,"Author", commit_author)
    # database.attributes.set_attribute_value(task,"Date", commit_date)
    # database.attributes.set_attribute_value(task,"Commit ID", commit_id)
    # #database.attributes.set_attribute_value(task,"Commit Type", commit_type)
    
    sys.__stdout__.write("Binary added to list")

if __name__ == "__main__":
    main()


