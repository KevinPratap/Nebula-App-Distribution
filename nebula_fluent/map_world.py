import ctypes
import os
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def get_process_name(pid):
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return f"Unknown (Error {kernel32.GetLastError()})"
    
    buf = ctypes.create_unicode_buffer(512)
    size = wintypes.DWORD(512)
    kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
    kernel32.CloseHandle(handle)
    return os.path.basename(buf.value)

def map_world():
    print("\n--- NUCLEAR GLOBAL WINDOW MAP ---")
    my_pid = os.getpid()
    print(f"My PID (Python): {my_pid}")
    
    targets = []
    
    def enum_all(hwnd, lp):
        if user32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, 512)
            cls = ctypes.create_unicode_buffer(512)
            user32.GetClassNameW(hwnd, cls, 512)
            
            pname = get_process_name(pid.value)
            
            if "python" in pname.lower() or "flet" in pname.lower() or "nebula" in title.value.lower():
                targets.append({
                    "hwnd": hwnd,
                    "pid": pid.value,
                    "pname": pname,
                    "title": title.value,
                    "class": cls.value
                })
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_all), 0)
    
    for t in targets:
        print(f"\n[{t['pname']}] PID: {t['pid']} | HWND: {t['hwnd']}")
        print(f"  Title: '{t['title']}'")
        print(f"  Class: {t['class']}")
        
        # Test Affinity (0x11)
        res = user32.SetWindowDisplayAffinity(t['hwnd'], 0x11)
        err = kernel32.GetLastError()
        print(f"  Test Affinity (0x11): {'SUCCESS' if res != 0 else f'FAILED (Err {err})'}")
        
        # Revert
        if res != 0:
            user32.SetWindowDisplayAffinity(t['hwnd'], 0)
            
        parent = user32.GetAncestor(t['hwnd'], 1) # GA_PARENT
        owner = user32.GetWindow(t['hwnd'], 4) # GW_OWNER
        root = user32.GetAncestor(t['hwnd'], 3) # GA_ROOTOWNER
        
        if parent: print(f"  Parent: {parent}")
        if owner: print(f"  Owner: {owner}")
        if root: print(f"  RootOwner: {root}")

if __name__ == "__main__":
    map_world()
