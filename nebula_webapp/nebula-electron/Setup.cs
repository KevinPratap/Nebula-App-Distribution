using System;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Reflection;
using System.Windows.Forms;
using System.Runtime.InteropServices;

// Professional Assembly Metadata
[assembly: AssemblyTitle("Nebula Interview AI Setup")]
[assembly: AssemblyDescription("Installer for the Nebula Interview AI Desktop Assistant")]
[assembly: AssemblyCompany("Nebula AI")]
[assembly: AssemblyProduct("Nebula Interview AI")]
[assembly: AssemblyCopyright("Copyright © 2026 Nebula AI")]
[assembly: AssemblyVersion("1.1.0.0")]
[assembly: AssemblyFileVersion("1.1.0.0")]
[assembly: ComVisible(false)]

namespace NebulaInstaller
{
    class Program
    {
        [STAThread]
        static void Main()
        {
            string appName = "Nebula Interview AI";
            string installPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "NebulaInterviewAI");
            string exeName = "nebula-electron.exe";

            try
            {
                // Simple GUI check
                DialogResult dr = MessageBox.Show(string.Format("Install {0} to your computer?", appName), "Nebula Setup", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                if (dr == DialogResult.No) return;

                if (Directory.Exists(installPath)) {
                    try { 
                        // Try to kill any running instances first
                        foreach (var process in Process.GetProcessesByName("nebula-electron")) {
                            process.Kill();
                        }
                        Directory.Delete(installPath, true); 
                    } catch {}
                }
                Directory.CreateDirectory(installPath);

                Console.WriteLine("Extracting Nebula...");
                
                // Get the embedded zip resource
                var assembly = Assembly.GetExecutingAssembly();
                using (Stream stream = assembly.GetManifestResourceStream("Nebula_Bundle.zip"))
                {
                    if (stream == null)
                    {
                        MessageBox.Show("Bundle not found inside installer!", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        return;
                    }

                    using (ZipArchive archive = new ZipArchive(stream))
                    {
                        foreach (ZipArchiveEntry entry in archive.Entries)
                        {
                            string completeFileName = Path.Combine(installPath, entry.FullName);
                            string directory = Path.GetDirectoryName(completeFileName);

                            if (!Directory.Exists(directory)) Directory.CreateDirectory(directory);
                            if (entry.Name != "") entry.ExtractToFile(completeFileName, true);
                        }
                    }
                }

                // Create Desktop Shortcut
                CreateShortcut(appName, installPath, exeName);

                MessageBox.Show(string.Format("{0} has been installed successfully!\n\nLaunching now...", appName), "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);

                Process.Start(Path.Combine(installPath, exeName));
            }
            catch (Exception ex)
            {
                MessageBox.Show("Installation failed: " + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        static void CreateShortcut(string name, string installPath, string exe)
        {
            try {
                string desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
                string shortcutPath = Path.Combine(desktopPath, name + ".lnk");
                
                string vbsPath = Path.Combine(Path.GetTempPath(), "shortcut.vbs");
                string script = string.Format(@"
Set oWS = WScript.CreateObject(""WScript.Shell"")
sLinkFile = ""{0}""
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = ""{1}""
oLink.WorkingDirectory = ""{2}""
oLink.Description = ""{3}""
oLink.Save
", shortcutPath, Path.Combine(installPath, exe), installPath, name);
                File.WriteAllText(vbsPath, script);
                Process.Start("wscript.exe", vbsPath).WaitForExit();
                File.Delete(vbsPath);
            } catch {}
        }
    }
}
