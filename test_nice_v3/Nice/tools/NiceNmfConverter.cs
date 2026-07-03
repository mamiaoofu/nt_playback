using System;
using System.IO;
using System.Reflection;

namespace NiceNmfConverter
{
    internal static class Program
    {
        private const string NiceBase = @"C:\Program Files (x86)\NICE Systems\NICE Player Release 6";

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

            string name = simpleName + ".dll";
            string path = Path.Combine(NiceBase, name);
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        }

        private static int Main(string[] args)
        {
            if (args.Length < 2 || args.Length > 3)
            {
                Console.Error.WriteLine("Usage: NiceNmfConverter.exe <input.nmf> <output> [PCM_A_LAW|PLAYER_WAV]");
                return 2;
            }

            string inputNmf = Path.GetFullPath(args[0]);
            string outputFile = Path.GetFullPath(args[1]);
            string compression = args.Length == 3 ? args[2] : "PCM_A_LAW";

            try
            {
                if (!File.Exists(inputNmf))
                {
                    throw new FileNotFoundException("Input NMF was not found", inputNmf);
                }

                Directory.CreateDirectory(Path.GetDirectoryName(outputFile));
                AppDomain.CurrentDomain.AssemblyResolve += ResolveNiceAssembly;
                Directory.SetCurrentDirectory(NiceBase);

                Assembly utils = Assembly.LoadFrom(Path.Combine(NiceBase, "NiceApplications.Playback.Utils.dll"));
                Assembly logic = Assembly.LoadFrom(Path.Combine(NiceBase, "NiceApplications.Playback.MediaServices.Logic.dll"));

                Type converterType = logic.GetType("NiceApplications.Playback.MediaServices.Logic.MediaFileConverter", true);

                if (compression.Equals("PLAYER_WAV", StringComparison.OrdinalIgnoreCase) ||
                    compression.Equals("WAVE_CONTROLLER", StringComparison.OrdinalIgnoreCase))
                {
                    ConvertWithPlayerWaveController(inputNmf, outputFile);
                    compression = "PLAYER_WAV";
                }
                else
                {
                    Type compressionType = utils.GetType("NiceApplications.Playback.Utils.CompressionType", true);
                    MethodInfo method = converterType.GetMethod(
                        "NmfToVox",
                        BindingFlags.Public | BindingFlags.Static
                    );
                    if (method == null)
                    {
                        throw new MissingMethodException(converterType.FullName, "NmfToVox");
                    }

                    object compressionValue = Enum.Parse(compressionType, compression);
                    method.Invoke(null, new object[] { inputNmf, outputFile, compressionValue });
                }

                FileInfo item = new FileInfo(outputFile);
                if (!item.Exists || item.Length == 0)
                {
                    throw new InvalidOperationException("NICE converter produced an empty output file");
                }

                Console.WriteLine("Output={0}", item.FullName);
                Console.WriteLine("Length={0}", item.Length);
                Console.WriteLine("Compression={0}", compression);
                double? mediaDuration = TryGetMediaDurationSeconds(inputNmf, converterType);
                if (mediaDuration.HasValue)
                {
                    Console.WriteLine("MediaDurationSeconds={0:0.000}", mediaDuration.Value);
                }
                return 0;
            }
            catch (TargetInvocationException ex)
            {
                Console.Error.WriteLine((ex.InnerException ?? ex).Message);
                return 1;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine(ex.Message);
                return 1;
            }
        }

        private static Assembly LoadNiceAssembly(string name)
        {
            return Assembly.LoadFrom(Path.Combine(NiceBase, name));
        }

        private static object GetIndexedProperty(object target, int index)
        {
            PropertyInfo property = target.GetType().GetProperty(
                "ItemIndexer",
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance
            );
            if (property != null)
            {
                return property.GetValue(target, new object[] { index });
            }

            property = target.GetType().GetProperty(
                "Item",
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance
            );
            if (property != null)
            {
                return property.GetValue(target, new object[] { index });
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

            throw new MissingMemberException(target.GetType().FullName, "ItemIndexer");
        }

        private static void ConvertWithPlayerWaveController(string inputNmf, string outputWav)
        {
            LoadNiceAssembly("ERS.Common.dll");
            LoadNiceAssembly("NiceApplications.Playback.Utils.dll");
            LoadNiceAssembly("NiceApplications.Playback.InternalCommon.dll");
            LoadNiceAssembly("NiceApplications.Playback.Streaming.Common.dll");
            LoadNiceAssembly("Nice.Storage.CommonProjects.NMFClasses.dll");
            LoadNiceAssembly("NiceApplications.Playback.FileTypes.dll");
            LoadNiceAssembly("NiceApplications.Playback.PlayList.Logic.dll");
            LoadNiceAssembly("NiceApplications.Playback.MediaServices.Logic.dll");
            Assembly playMgr = LoadNiceAssembly("NiceApplications.Playback.PlayMgr.dll");

            Type playlistType = playMgr.GetType("NiceApplications.Playback.PlayMgr.LocalPlaylist", true);
            object playlist = Activator.CreateInstance(playlistType);
            MethodInfo load = playlistType.GetMethod("Load", new Type[] { typeof(string), typeof(bool), typeof(bool) });
            MethodInfo getItemCount = playlistType.GetMethod("GetItemCount", Type.EmptyTypes);
            PropertyInfo lastError = playlistType.GetProperty("LastErrorString", BindingFlags.Public | BindingFlags.Instance);
            if (load == null || getItemCount == null)
            {
                throw new MissingMethodException(playlistType.FullName, "Load/GetItemCount");
            }

            load.Invoke(playlist, new object[] { inputNmf, false, false });
            DateTime deadline = DateTime.UtcNow.AddSeconds(30);
            int itemCount = 0;
            while (DateTime.UtcNow < deadline)
            {
                itemCount = (int)getItemCount.Invoke(playlist, null);
                string error = lastError == null ? null : (string)lastError.GetValue(playlist, null);
                if (itemCount > 0)
                {
                    break;
                }
                if (!string.IsNullOrEmpty(error))
                {
                    throw new InvalidOperationException(error);
                }
                System.Threading.Thread.Sleep(50);
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

            object media = null;
            for (int index = 0; index < mediaCount; index++)
            {
                object candidate = GetIndexedProperty(item, index);
                PropertyInfo mediaTypeProperty = candidate.GetType().GetProperty("MediaType", BindingFlags.Public | BindingFlags.Instance);
                string mediaType = mediaTypeProperty == null ? "" : System.Convert.ToString(mediaTypeProperty.GetValue(candidate, null));
                if (mediaType.Equals("VOICE", StringComparison.OrdinalIgnoreCase))
                {
                    media = candidate;
                    break;
                }
            }
            if (media == null)
            {
                media = GetIndexedProperty(item, 0);
            }

            PropertyInfo outputFileName = media.GetType().GetProperty(
                "OutputFileName",
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance
            );
            if (outputFileName == null || !outputFileName.CanWrite)
            {
                throw new MissingMemberException(media.GetType().FullName, "OutputFileName");
            }
            outputFileName.SetValue(media, outputWav, null);

            Type waveControllerType = playMgr.GetType("NiceApplications.Playback.PlayMgr.WaveController", true);
            Type saveMediaType = playMgr.GetType("NiceApplications.Playback.PlayMgr.SaveMediaType", true);
            object allTypes = Enum.Parse(saveMediaType, "AllTypes");
            object controller = Activator.CreateInstance(waveControllerType);

            MethodInfo init = null;
            foreach (MethodInfo method in waveControllerType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                ParameterInfo[] parameters = method.GetParameters();
                if (method.Name == "Init" && parameters.Length == 2)
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

            init.Invoke(controller, new object[] { media, allTypes });
            save.Invoke(controller, new object[] { null });
        }

        private static double? TryGetMediaDurationSeconds(string inputNmf, Type converterType)
        {
            try
            {
                MethodInfo getMedia = null;
                foreach (MethodInfo method in converterType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static))
                {
                    if (method.Name == "GetNmfVoiceMedia")
                    {
                        getMedia = method;
                        break;
                    }
                }
                if (getMedia == null)
                {
                    return null;
                }

                object media = getMedia.Invoke(null, new object[] { inputNmf });
                if (media == null)
                {
                    return null;
                }

                Type mediaType = media.GetType();
                PropertyInfo startProp = mediaType.GetProperty("DisplayStartTime", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                PropertyInfo stopProp = mediaType.GetProperty("DisplayStopTime", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (startProp == null || stopProp == null)
                {
                    return null;
                }

                object startValue = startProp.GetValue(media, null);
                object stopValue = stopProp.GetValue(media, null);
                if (!(startValue is DateTime) || !(stopValue is DateTime))
                {
                    return null;
                }

                double seconds = ((DateTime)stopValue - (DateTime)startValue).TotalSeconds;
                return seconds > 0 ? (double?)seconds : null;
            }
            catch
            {
                return null;
            }
        }
    }
}
