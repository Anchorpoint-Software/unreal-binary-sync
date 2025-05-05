import anchorpoint as ap
import apsync as aps
import os

class UnrealProjectSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()

        if ctx.project_id is None or ctx.project_id == "":
            raise Exception(
                "Unreal Binary settings can only be used in the context of a project"
            )

        no_project_label = "No Project"

        uproject_files = self.find_uproject_files(ctx.project_path)
        uproject_display_names = [os.path.splitext(os.path.basename(uproject_file))[0] for uproject_file in uproject_files]
        uproject_display_names.append(no_project_label)

        self.ctx = ctx        
        project_path = ctx.project_path

        settings = aps.Settings()
        binary_source = settings.get(project_path+"_binary_source", "")
        sync_dependencies = settings.get(project_path+"_sync_dependencies", True)
        launch_project_display_name = settings.get(project_path+"_launch_project_display_name", no_project_label) 

        self.dialog = ap.Dialog()

        self.dialog.add_text("ZIP Location").add_input(
            placeholder="Select folder containing binaries...",
            browse=ap.BrowseType.Folder,
            var="binary_source",
            default=binary_source,
            callback = self.store_local_settings
        )
        
        self.dialog.add_checkbox(
            text="Sync Setup Dependencies",
            var="sync_dependencies",
            default=sync_dependencies,
            callback = self.store_local_settings
        )
        self.dialog.add_info("Note that you have to accept a Windows Control Popup for UE Prerequisites")  

        if launch_project_display_name != "":
            self.dialog.add_text("Launch Project").add_dropdown(
            default=launch_project_display_name,
            values=uproject_display_names,
            var="launch_project_display_name",
            callback = self.store_local_settings
        )  

    def get_dialog(self):
        return self.dialog
    
    def find_uproject_files(self,project_path):
    
        uproject_files = []
        depth = 3
        
        # Get all directories at the specified depth (currently set to depth levels)
        for root, dirs, files in os.walk(project_path, topdown=True):
            # Skip Engine and Templates folders
            if 'Engine' in dirs:
                dirs.remove('Engine')
            if 'Templates' in dirs:
                dirs.remove('Templates')
                
            # Only process up to depth levels deep
            rel_path = os.path.relpath(root, project_path)
            if rel_path == '.' or rel_path.count(os.sep) <= depth:
                # Look for .uproject files in current directory
                for file in files:
                    if file.endswith('.uproject'):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, project_path)
                        uproject_files.append(rel_path)
            
            # Stop walking deeper than depth levels
            if rel_path.count(os.sep) >= depth:
                dirs.clear()
        
        return uproject_files

    def store_local_settings(self,dialog,value):

        ctx = ap.get_context()
        project_path = ctx.project_path

        source_path = dialog.get_value("binary_source")
        sync_dependencies = dialog.get_value("sync_dependencies")
        launch_project_display_name = dialog.get_value("launch_project_display_name")    
        
        # Store the settings for next time
        settings = aps.Settings()
        settings.set(project_path+"_binary_source", source_path)
        settings.set(project_path+"_sync_dependencies", sync_dependencies)
        settings.set(project_path+"_launch_project_display_name", launch_project_display_name)
        settings.store()
        return

def on_show_project_preferences(settings_list, ctx: ap.Context):
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if not project:
        return

    unrealSettings = UnrealProjectSettings(ctx)
    unrealSettings.name = "Unreal"
    unrealSettings.priority = 90
    unrealSettings.icon = ":/icons/organizations-and-products/unrealEngine.svg"
    settings_list.add(unrealSettings)
    