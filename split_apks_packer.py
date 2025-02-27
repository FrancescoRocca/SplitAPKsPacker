import subprocess
import argparse
import pathlib
import shutil
import xml.etree.ElementTree as ET
import time
import glob


class Colors:
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    RESET = "\033[m"
    BOLD = "\033[1m"
    WHITE = "\033[37m"


def check_uber_jar():
    print(
        Colors.BOLD
        + Colors.GREEN
        + "Checking uber-apk-signer.jar in the same directory...",
        end="",
    )
    uber = glob.glob("uber-apk-signer*.jar")[0]
    if uber:
        print(Colors.GREEN + " ✅" + Colors.RESET)
        return uber
    else:
        print_error("\nPlease put uber-apk-signer.jar in the same directory!")
        return None


def check_apktool() -> bool:
    print(Colors.BOLD + Colors.GREEN + "Checking apktool..." + Colors.RESET, end="")
    ret = subprocess.Popen(
        ["apktool"],
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    ret.wait()
    if ret.returncode != 0:
        print_error("\nPlease install apktool!")
        return False
    print(Colors.GREEN + " ✅" + Colors.RESET)
    return True


def check_directory(directory) -> bool:
    print(
        Colors.BOLD + Colors.GREEN + f"Checking {directory}..." + Colors.RESET, end=""
    )
    dir_path = pathlib.Path(directory).resolve()
    if dir_path.is_dir():
        print(Colors.GREEN + " ✅" + Colors.RESET)
        return True
    else:
        print_error("\nPlease provide a directory!")
        return False


def move_files(source, dest):
    source = pathlib.Path(source)
    apktool_yml_path = dest / "apktool.yml"
    apktool_yml = open(apktool_yml_path, "a", encoding="utf-8")

    for item in source.rglob("*"):
        relative_path = item.relative_to(source)
        dest_path = dest / relative_path

        if item.is_file() and not dest_path.exists():
            print(
                Colors.GREEN
                + "\t> "
                + Colors.RESET
                + f"Adding {relative_path.as_posix()}..."
                + Colors.RESET
            )
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(item, dest_path)
            apktool_yml.write(f"- {relative_path.as_posix()}\n")

    apktool_yml.close()


def decompile_split_apks(base_apk_folder, split_apks_folder, output_folder) -> int:
    folder_path = pathlib.Path(split_apks_folder)
    apks = list(folder_path.glob("*.apk"))

    for apk in apks:
        cmd = ["apktool", "d", str(apk)]
        if output_folder:
            out_folder = str(output_folder) + "/" + apk.name
            cmd.extend(["-o", out_folder])

        print_blue(f"Decompiling {apk.name}...")
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait()
        if proc.returncode != 0:
            print_error(f"Unable to decompile {apk.name}")
            return -1

        move_files(out_folder, base_apk_folder)

    return 0


def rebuild(base_apk_folder) -> int:
    print_blue("Rebuilding everything...")
    proc = subprocess.Popen(
        ["apktool", "b", str(base_apk_folder)],
        shell=True,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    proc.wait()
    if proc.returncode != 0:
        return -1

    print(
        Colors.BOLD
        + Colors.GREEN
        + f"Output APK: {base_apk_folder / 'dist'} ✅"
        + Colors.RESET
    )


def edit_manifest(base_apk_folder):
    print_blue("Editing manifest...")
    manifest_path = base_apk_folder / "AndroidManifest.xml"
    tree = ET.parse(manifest_path)
    root = tree.getroot()

    ns = "{http://schemas.android.com/apk/res/android}"

    keys = list(root.attrib.keys())
    if f"{ns}requiredSplitTypes" in keys:
        root.attrib.pop(f"{ns}requiredSplitTypes")
    if f"{ns}splitTypes" in root.attrib:
        root.attrib.pop(f"{ns}splitTypes")

    tags = ["com.android.vending.splits.required", "com.android.vending.splits"]

    for elem in root.findall("application/meta-data"):
        name = elem.attrib.get(f"{ns}name")
        if name in tags:
            root.find("application").remove(elem)

    for elem in root.iter("meta-data"):
        if elem.attrib.get(f"{ns}name") == "com.android.stamp.type":
            elem.attrib[f"{ns}value"] = "STAMP_TYPE_STANDALONE_APK"
        if elem.attrib.get(f"{ns}name") == "com.android.vending.derived.apk.id":
            elem.attrib[f"{ns}value"] = "1"

    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)


def sign_apk(base_apk_folder, uber_jar):
    print_blue("Signing APK...")
    apk_folder = base_apk_folder / "dist"
    apk_file = glob.glob(str(apk_folder) + "/*.apk")[0]
    proc = subprocess.Popen(
        ["java", "-jar", uber_jar, "-a", apk_file],
        shell=False,
        stdin=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    proc.wait()
    if proc.returncode != 0:
        print_error("Failed to sign APK!")
        return -1


def print_error(text):
    print(Colors.BOLD + Colors.RED + text + Colors.RESET)


def print_blue(text):
    print(Colors.BOLD + Colors.BLUE + text + Colors.RESET)


def print_white(text):
    print(Colors.WHITE + text + Colors.RESET)


def run_sap(args: argparse.Namespace):
    base_apk_folder = pathlib.Path(args.base_apk_dir).resolve()
    split_apks_folder = pathlib.Path(args.split_apks_folder).resolve()
    output_folder = pathlib.Path(args.output).resolve() if args.output else "out_folder"
    sign = args.sign

    if not all(
        [
            check_directory(args.base_apk_dir),
            check_directory(args.split_apks_folder),
            check_apktool(),
        ]
    ):
        return -1

    uber_jar = check_uber_jar()
    if uber_jar is None:
        exit()

    ret = decompile_split_apks(base_apk_folder, split_apks_folder, output_folder)
    if ret == -1:
        exit()

    edit_manifest(base_apk_folder)

    ret = rebuild(base_apk_folder)
    if ret == -1:
        exit()

    if sign:
        sign_apk(base_apk_folder, uber_jar)


if __name__ == "__main__":
    print_blue("[Split APKs Packer]")

    parser = argparse.ArgumentParser(prog="Split Apks Packer")

    parser.add_argument(
        "-s", "--sign", action="store_true", help="Sign the APK using uber-apk-signer"
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output path where the build files will be stored",
        type=str,
    )
    parser.add_argument("base_apk_dir", help="Base APK folder", type=str)
    parser.add_argument(
        "split_apks_folder", help="Folder of the splitted APKs", type=str
    )

    args = parser.parse_args()

    start_time = time.time()
    run_sap(args)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(
        Colors.BOLD
        + Colors.GREEN
        + f"Finished in {elapsed_time:.1f} seconds"
        + Colors.RESET
    )
