using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading;

public static class NiceSaveMgrWorker
{
    private const string NiceBase = @"C:\Program Files (x86)\NICE Systems\NICE Player Release 6";
    private static bool resolverInstalled;
    private static bool assembliesLoaded;
    private static Assembly playMgrAssembly;

    public static int Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;
        Console.InputEncoding = Encoding.UTF8;

        try
        {
            EnsureNiceReady();
            if (args.Length == 2)
            {
                Convert(args[0], args[1]);
                Console.WriteLine("OK");
                return 0;
            }

            if (args.Length == 1 && args[0] == "--worker")
            {
                Console.WriteLine("READY");
                RunWorkerLoop();
                return 0;
            }

            Console.Error.WriteLine("Usage: NiceSaveMgrWorker.exe <input.nmf> <output.wav> | --worker");
            return 2;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(FlattenException(ex));
            return 1;
        }
    }

    private static void RunWorkerLoop()
    {
        string line;
        while ((line = Console.ReadLine()) != null)
        {
            Stopwatch stopwatch = Stopwatch.StartNew();
            try
            {
                string[] parts = line.Split('\t');
                if (parts.Length != 3 || parts[0] != "CONVERT")
                {
                    throw new InvalidOperationException("Unsupported worker command");
                }

                string inputNmf = Decode(parts[1]);
                string outputWav = Decode(parts[2]);
                Convert(inputNmf, outputWav);
                stopwatch.Stop();
                Console.WriteLine("OK\t" + stopwatch.Elapsed.TotalMilliseconds.ToString("0.0") + "\t" + Encode(outputWav));
            }
            catch (Exception ex)
            {
                stopwatch.Stop();
                Console.WriteLine("ERR\t" + stopwatch.Elapsed.TotalMilliseconds.ToString("0.0") + "\t" + Encode(FlattenException(ex)));
            }
            Console.Out.Flush();
        }
    }

    private static void EnsureNiceReady()
    {
        if (!Environment.Is64BitProcess)
        {
            // OK: NICE Player Release 6 is 32-bit.
        }
        else
        {
            throw new InvalidOperationException("NiceSaveMgrWorker must be compiled/run as x86.");
        }

        if (!resolverInstalled)
        {
            AppDomain.CurrentDomain.AssemblyResolve += ResolveNiceAssembly;
            resolverInstalled = true;
        }

        if (!assembliesLoaded)
        {
            Directory.SetCurrentDirectory(NiceBase);
            LoadNiceAssembly("ERS.Common.dll");
            LoadNiceAssembly("NiceApplications.Playback.Utils.dll");
            LoadNiceAssembly("NiceApplications.Playback.InternalCommon.dll");
            LoadNiceAssembly("NiceApplications.Playback.Streaming.Common.dll");
            LoadNiceAssembly("Nice.Storage.CommonProjects.NMFClasses.dll");
            LoadNiceAssembly("NiceApplications.Playback.FileTypes.dll");
            LoadNiceAssembly("NiceApplications.Playback.PlayList.Logic.dll");
            LoadNiceAssembly("NiceApplications.Playback.MediaServices.Logic.dll");
            playMgrAssembly = LoadNiceAssembly("NiceApplications.Playback.PlayMgr.dll");
            assembliesLoaded = true;
        }
    }

    private static Assembly ResolveNiceAssembly(object sender, ResolveEventArgs args)
    {
        string simpleName = args.Name.Split(',')[0];
        foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            if (assembly.GetName().Name == simpleName)
            {
                return assembly;
            }
        }

        string path = Path.Combine(NiceBase, simpleName + ".dll");
        return File.Exists(path) ? Assembly.LoadFrom(path) : null;
    }

    private static Assembly LoadNiceAssembly(string name)
    {
        return Assembly.LoadFrom(Path.Combine(NiceBase, name));
    }

    private static object GetIndexedProperty(object target, int index)
    {
        foreach (string propertyName in new[] { "ItemIndexer", "MediaIndexer", "Item" })
        {
            PropertyInfo property = target.GetType().GetProperty(
                propertyName,
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance
            );
            if (property != null)
            {
                return property.GetValue(target, new object[] { index });
            }
        }

        foreach (string methodName in new[] { "get_ItemIndexer", "get_MediaIndexer", "get_Item" })
        {
            MethodInfo method = target.GetType().GetMethod(
                methodName,
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance,
                null,
                new Type[] { typeof(int) },
                null
            );
            if (method != null)
            {
                return method.Invoke(target, new object[] { index });
            }
        }

        throw new MissingMemberException(target.GetType().FullName, "ItemIndexer/MediaIndexer");
    }

    public static void Convert(string inputNmf, string outputWav)
    {
        EnsureNiceReady();

        inputNmf = Path.GetFullPath(inputNmf);
        outputWav = Path.GetFullPath(outputWav);
        Directory.CreateDirectory(Path.GetDirectoryName(outputWav));
        Directory.SetCurrentDirectory(NiceBase);

        Type playlistType = playMgrAssembly.GetType("NiceApplications.Playback.PlayMgr.LocalPlaylist", true);
        object playlist = Activator.CreateInstance(playlistType);
        MethodInfo load = playlistType.GetMethod("Load", new Type[] { typeof(string), typeof(bool), typeof(bool) });
        MethodInfo getItemCount = playlistType.GetMethod("GetItemCount", Type.EmptyTypes);
        PropertyInfo lastError = playlistType.GetProperty("LastErrorString", BindingFlags.Public | BindingFlags.Instance);

        if (load == null || getItemCount == null)
        {
            throw new MissingMethodException(playlistType.FullName, "Load/GetItemCount");
        }

        load.Invoke(playlist, new object[] { inputNmf, true, false });
        DateTime deadline = DateTime.UtcNow.AddSeconds(30);
        int itemCount = 0;
        while (DateTime.UtcNow < deadline)
        {
            itemCount = (int)getItemCount.Invoke(playlist, null);
            string error = lastError == null ? null : System.Convert.ToString(lastError.GetValue(playlist, null));
            if (itemCount > 0)
            {
                break;
            }
            if (!string.IsNullOrEmpty(error))
            {
                throw new InvalidOperationException(error);
            }
            Thread.Sleep(50);
        }
        if (itemCount <= 0)
        {
            throw new TimeoutException("LocalPlaylist did not load any media from the NMF file");
        }

        object item = GetIndexedProperty(playlist, 0);
        PropertyInfo mediaCountProperty = item.GetType().GetProperty("MediaCount", BindingFlags.Public | BindingFlags.Instance);
        int mediaCount = mediaCountProperty == null ? 0 : (int)mediaCountProperty.GetValue(item, null);
        if (mediaCount <= 0)
        {
            throw new InvalidOperationException("LocalPlaylist did not expose any media streams");
        }

        PropertyInfo outputFileName = item.GetType().GetProperty(
            "OutputFileName",
            BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance
        );
        if (outputFileName == null || !outputFileName.CanWrite)
        {
            throw new MissingMemberException(item.GetType().FullName, "OutputFileName");
        }
        outputFileName.SetValue(item, outputWav, null);

        Type waveControllerType = playMgrAssembly.GetType("NiceApplications.Playback.PlayMgr.WaveController", true);
        Type saveMediaType = playMgrAssembly.GetType("NiceApplications.Playback.PlayMgr.SaveMediaType", true);
        object allTypes = Enum.Parse(saveMediaType, "AllTypes");
        object controller = Activator.CreateInstance(waveControllerType);

        MethodInfo init = null;
        foreach (MethodInfo method in waveControllerType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
        {
            ParameterInfo[] parameters = method.GetParameters();
            if (method.Name == "Init" && parameters.Length == 3)
            {
                init = method;
                break;
            }
        }
        MethodInfo save = waveControllerType.GetMethod("Save", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
        if (init == null || save == null)
        {
            throw new MissingMethodException(waveControllerType.FullName, "Init/Save");
        }

        init.Invoke(controller, new object[] { item, -1, allTypes });
        save.Invoke(controller, new object[] { null });

        FileInfo output = new FileInfo(outputWav);
        if (!output.Exists || output.Length == 0)
        {
            throw new InvalidOperationException("WaveController produced an empty WAV");
        }
    }

    private static string Encode(string value)
    {
        return System.Convert.ToBase64String(Encoding.UTF8.GetBytes(value ?? ""));
    }

    private static string Decode(string value)
    {
        return Encoding.UTF8.GetString(System.Convert.FromBase64String(value));
    }

    private static string FlattenException(Exception ex)
    {
        while (ex is TargetInvocationException && ex.InnerException != null)
        {
            ex = ex.InnerException;
        }
        return ex.GetType().Name + ": " + ex.Message;
    }
}
