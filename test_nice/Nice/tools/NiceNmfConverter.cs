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
            string name = args.Name.Split(',')[0] + ".dll";
            string path = Path.Combine(NiceBase, name);
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        }

        private static int Main(string[] args)
        {
            if (args.Length < 2 || args.Length > 3)
            {
                Console.Error.WriteLine("Usage: NiceNmfConverter.exe <input.nmf> <output.alaw> [PCM_A_LAW]");
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

                Type compressionType = utils.GetType("NiceApplications.Playback.Utils.CompressionType", true);
                object compressionValue = Enum.Parse(compressionType, compression);

                Type converterType = logic.GetType("NiceApplications.Playback.MediaServices.Logic.MediaFileConverter", true);
                MethodInfo method = converterType.GetMethod(
                    "NmfToVox",
                    BindingFlags.Public | BindingFlags.Static
                );
                if (method == null)
                {
                    throw new MissingMethodException(converterType.FullName, "NmfToVox");
                }

                method.Invoke(null, new object[] { inputNmf, outputFile, compressionValue });
                FileInfo item = new FileInfo(outputFile);
                if (!item.Exists || item.Length == 0)
                {
                    throw new InvalidOperationException("NICE converter produced an empty output file");
                }

                Console.WriteLine("Output={0}", item.FullName);
                Console.WriteLine("Length={0}", item.Length);
                Console.WriteLine("Compression={0}", compression);
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
    }
}
