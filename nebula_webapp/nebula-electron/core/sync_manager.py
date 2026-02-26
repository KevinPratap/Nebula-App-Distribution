import os
import json
import shutil
import time

class SyncManager:
    """Handles simulated cloud synchronization for user data."""
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sync_dir = os.path.join(self.base_dir, "cloud_sync")
        if not os.path.exists(self.sync_dir):
            os.makedirs(self.sync_dir)

    def sync_file(self, source_path):
        """Simulate syncing a file to 'cloud' storage."""
        if not os.path.exists(source_path):
            return False, "Source file not found"
        
        filename = os.path.basename(source_path)
        dest_path = os.path.join(self.sync_dir, filename)
        
        try:
            # Simulate network latency
            # time.sleep(0.5) 
            shutil.copy2(source_path, dest_path)
            # Create a sync manifest
            manifest = {
                "last_sync": time.time(),
                "status": "Success",
                "filename": filename
            }
            with open(os.path.join(self.sync_dir, "manifest.json"), "w") as f:
                json.dump(manifest, f)
            return True, "Synced"
        except Exception as e:
            return False, str(e)

    def get_sync_status(self):
        manifest_path = os.path.join(self.sync_dir, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    data = json.load(f)
                    return f"Last synced: {time.strftime('%H:%M:%S', time.localtime(data['last_sync']))}"
            except: pass
        return "Never synced"
