import anchorpoint as ap
import apsync as aps
import os
import subprocess

ctx = ap.get_context()
ui = ap.UI()

def sync_action(dialog):
    source_path = dialog.get_value("binary_source")
    include_editor_binaries = dialog.get_value("include_editor_binaries")
    
    # Store the selected path in settings
    settings = aps.Settings()
    settings.set("last_binary_source", source_path)
    settings.store()
    
    # Get commit IDs from the Git repository
    try:
        commit_ids = subprocess.check_output(
            ['git', 'rev-list', 'HEAD'],
            cwd=source_path,
            text=True
        ).splitlines()
    except subprocess.CalledProcessError:
        ui.show_error("Git Error", "Failed to retrieve commit IDs.")
        dialog.close()
        return
    
    # Iterate through commit IDs and check for matching zip files
    for commit_id in commit_ids:
        zip_file_name = f"{commit_id}.zip"
        if zip_file_name in os.listdir(source_path):
            # TODO: Implement further sync logic with the found zip file
            dialog.close()
            return
    
    # If no matching zip file is found
    ui.show_error("No binaries found", "Check your binaries source folder")
    dialog.close()

def show_dialog():
    settings = aps.Settings()
    last_binary_source = settings.get("last_binary_source", "")

    dialog = ap.Dialog()
    dialog.title = "Sync Binaries"
    
    if ctx.icon:
        dialog.icon = ctx.icon
    
    dialog.add_text("Binary source").add_input(
        placeholder="Select folder containing binaries...",
        browse=ap.BrowseType.Folder,
        var="binary_source",
        default=last_binary_source
    )
    
    dialog.add_checkbox(
        text="Include Editor Binaries",
        var="include_editor_binaries"
    )
    
    dialog.add_button("Sync", callback=sync_action)
    dialog.show()

if __name__ == "__main__":
    show_dialog()