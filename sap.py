from pathlib import Path
import time
import sys
import json
from zipfile import ZipFile


class AndroidManifest:
    def edit_manifest(base_apk_folder):
        pass


class SAP:
    def __init__(self, xapk: Path):
        self.xapk = xapk

    def unzip_file(self, file: Path):
        with ZipFile(file) as zip:
            zip.extractall(file.stem)

    def parse_manifest_json(self):
        manifest = json.loads(self.manifest_json.read_text())
        self.split_apks = manifest["split_apks"]

    def run(self):
        print(f"Merging {self.xapk}...")

        print(f"=> Unzipping {self.xapk}")
        self.unzip_file(self.xapk)
        self.zip_folder = self.xapk.parent.absolute() / self.xapk.stem
        self.manifest_json = self.zip_folder / "manifest.json"

        print("=> Parsing manifest.json")
        self.parse_manifest_json()

        for x in self.split_apks:
            file = x["file"]
            id = x["id"]
            if id == "base":
                self.base = file

            file_path = Path(self.zip_folder / file)
            self.unzip_file(file_path)
            print(f"=> Unzipping {file_path.stem}")


if __name__ == "__main__":
    print("[Split APKs Packer]")
    len = len(sys.argv)
    if len < 2:
        print("Usage:")
        print(f"\t$ {sys.argv[0]} file.xapk")
        exit()

    file = Path(sys.argv[1])
    if not file.is_file() or file.suffix != ".xapk":
        print("Please provide a file!")
        exit()

    sap = SAP(file)

    start_time = time.time()
    sap.run()
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Finished in {elapsed_time:.1f} seconds")
