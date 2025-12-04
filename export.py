#!/usr/bin/env python3

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys

from pathlib import Path
from threading import Thread
from typing import Dict, List, Tuple, Optional
from zipfile import ZIP_DEFLATED, ZipFile

EXTERNAL_RESOURCE_PATTERN: str = (
    r'\[ext_resource\s+type="([^"]+)"(?:\s+uid="([^"]+)")?\s+path="([^"]+)"\s+id="([^"]+)"\]'
)

I18N_PATTERN: str = r'\[sub_resource\s+type="I18N"[^\]]*\][\s\S]*?(?=\n\s*\n|\n\[|\Z)'
LOCALE_PATTERN: str = r'(\w+)\s*=\s*"(.*)"'

TEXTURE_LAYER_PATTERN: str = (
    r'\[sub_resource\s+type="ColorTextureLayer"\s+id="([^"]+)"\]([\s\S]*?(?=\n\s*\n|\n\[|\Z))'
)
TEXTURE_LAYER_COLOR_PATTERN: str = r"color\s*=\s*(\d+)"
TEXTURE_LAYER_TEXTURE_PATTERN: str = r'texture\s*=\s*ExtResource\("([^"]+)"\)'

TEXTURE_GROUP_PATTERN: str = (
    r'\[sub_resource\s+type="ColorTextureGroup"[^\]]*\][\s\S]*?(?=\n\s*\n|\n\[|\Z)'
)
TEXTURE_GROUP_LAYER_PATTERN: str = (
    r"layers\s*=\s*Array\[ColorTextureLayer\]\(\s*\[([^\]]+)\]\s*\)"
)
TEXTURE_GROUP_LAYER_ID_PATTERN: str = r'SubResource\("([^"]+)"\)'

TAG_PATTERN: str = r"tags\s*=\s*(\d+)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Miniverse package")
    parser.add_argument("--output", "-o", type=str, help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    output_path: Optional[Path] = Path(args.output) if args.output else None
    try:
        _export_package(output_path)
        sys.exit(0)
    except Exception as e:
        logging.error(e)
        sys.exit(1)


def _export_package(output_path: Optional[Path]) -> None:
    project_path: Path = Path(__file__).parent
    project_name: str = project_path.name

    if not (project_path / "project.godot").exists():
        raise Exception(f"'{project_name}' is not a valid Godot project.")

    try:
        with open(project_path / f"{project_name}/{project_name}.tres", "r", encoding="utf-8") as file:
            info: str = file.read()
    except FileNotFoundError:
        raise Exception(f"Project info file '{project_name}/{project_name}.tres' not found.")
    except Exception as e:
        raise Exception(
            f"Failed to load project info file '{project_name}/{project_name}.tres' - {str(e)}"
        )

    external_resources: Dict[str, Path] = _get_external_resources(project_path, info)
    locales: Dict[str, str] = _get_locales(info)
    texture_layers, texture_group = _get_textures(external_resources, info)
    tags: int = _get_tags(info)

    temp_path: Path = _create_temp_directory(project_path)
    _save_pck(project_path, temp_path)
    _save_textures(project_path, temp_path, texture_layers)
    _save_json(project_path, temp_path, locales, texture_layers, texture_group, tags)
    _zip_package(project_path, temp_path, output_path)
    shutil.rmtree(temp_path)


def _get_external_resources(project_path: Path, info: str) -> Dict[str, Path]:
    logging.debug("Loading external resources...")

    external_resources: Dict[str, Path] = {}
    resource_matches: List[Tuple[str, str, str, str]] = re.findall(
        EXTERNAL_RESOURCE_PATTERN, info
    )
    for _, _, path, resource_id in resource_matches:
        if path.startswith("res://"):
            path = path[6:]
        external_resources[resource_id] = project_path / path

    logging.info(f"{len(external_resources)} external resources loaded")
    return external_resources


def _get_locales(info: str) -> Dict[str, str]:
    logging.debug("Loading locales...")

    i18n_matches: List[str] = re.findall(I18N_PATTERN, info)
    if i18n_matches.__len__() != 1:
        return {}

    locales: Dict[str, str] = {}
    i18n: str = i18n_matches[0].split("\n", 1)[1]
    locale_matches: List[Tuple[str, str]] = re.findall(LOCALE_PATTERN, i18n)
    for locale_name, translation in locale_matches:
        locales[locale_name] = translation

    logging.info(f"{len(locales)} locales loaded")
    return locales


def _get_textures(
    external_resources: Dict[str, Path], info: str
) -> Tuple[Dict[str, Tuple[Path, int]], List[Path]]:
    logging.debug("Loading texture layers...")

    layer_matches = re.findall(TEXTURE_LAYER_PATTERN, info)
    layers: Dict[str, Tuple[Path, int]] = {}
    for layer_id, layer_match in layer_matches:
        texture_match: Optional[re.Match] = re.search(
            TEXTURE_LAYER_TEXTURE_PATTERN, layer_match
        )
        if not texture_match:
            continue
        texture_id: str = texture_match.group(1)
        texture_path: str = external_resources[texture_id]
        color_match: Optional[re.Match] = re.search(
            TEXTURE_LAYER_COLOR_PATTERN, layer_match
        )
        color: int = int(color_match.group(1)) if color_match else 0
        layers[layer_id] = (texture_path, color)

    logging.info(f"{len(layers)} texture layers loaded")

    logging.debug("Loading texture group...")

    group_match: Optional[re.Match] = re.search(TEXTURE_GROUP_PATTERN, info)
    group_layers: Optional[List[str]] = None
    if group_match:
        group_layers: List[str] = []
        group_content: str = group_match.group(0)
        layers_match: Optional[re.Match] = re.search(
            TEXTURE_GROUP_LAYER_PATTERN, group_content
        )
        if layers_match:
            layers_content: str = layers_match.group(1)
            layer_ids: List[str] = re.findall(
                TEXTURE_GROUP_LAYER_ID_PATTERN, layers_content
            )
            for layer_id in layer_ids:
                if layer_id in layers:
                    group_layers.append(layer_id)

    logging.info("Texture group loaded" if group_layers else "No texture group found")
    return layers, group_layers


def _get_tags(info: str) -> int:
    logging.debug("Loading tags...")

    tag_match: Optional[re.Match] = re.search(TAG_PATTERN, info)
    tags: int = int(tag_match.group(1)) if tag_match else 0

    logging.info(f"Tags loaded - {tags}")
    return tags


def _create_temp_directory(project_path: Path) -> Path:
    temp_path: Path = project_path / "builds" / ".miniverse"
    if temp_path.exists():
        shutil.rmtree(temp_path)

    temp_path.mkdir(parents=True, exist_ok=True)
    return temp_path


def _save_pck(project_path: Path, temp_path: Path) -> None:
    try:
        logging.info("Exporting project...")

        process = subprocess.Popen(
            [
                "godot",
                "--headless",
                "--path",
                str(project_path),
                "--export-pack",
                "Windows",
                str(temp_path / f"{project_path.name}.pck"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        stdout_thread: Thread = Thread(
            target=_read_stream, args=(process.stdout, "    ")
        )
        stderr_thread: Thread = Thread(
            target=_read_stream, args=(process.stderr, "    ")
        )
        stdout_thread.start()
        stderr_thread.start()

        return_code: int = process.wait()
        stdout_thread.join()
        stderr_thread.join()
        if return_code != 0:
            raise Exception(
                f"Failed exporting project '{project_path.name}' - {return_code}"
            )
        else:
            logging.info(f"Project exported")

    except FileNotFoundError:
        raise Exception("Godot executable not found in PATH")
    except Exception as e:
        raise Exception(f"Failed exporting project '{project_path.name}' - {str(e)}")


def _save_json(
    project_path: Path,
    temp_path: Path,
    locales: Dict[str, str],
    texture_layers: Dict[str, Tuple[Path, int]],
    texture_group: Optional[List[str]],
    tags: int,
) -> None:
    logging.debug("Exporting JSON...")

    project_name: str = project_path.name
    info: json = {
        "id": project_name,
        "name": locales,
        "texture_layers": [
            {
                "id": layer_id,
                "path": str(texture_path.relative_to(project_path)).replace("\\", "/"),
                "color": color,
            }
            for layer_id, (texture_path, color) in texture_layers.items()
        ],
        "tags": tags,
    }

    if texture_group:
        info["texture_group"] = [str(path).replace("\\", "/") for path in texture_group]

    with open(temp_path / f"{project_name}.json", "w", encoding="utf-8") as file:
        json.dump(info, file, indent=4, ensure_ascii=False)

    logging.info("JSON exported")


def _save_textures(
    project_path: Path, temp_path: Path, texture_layers: Dict[str, Tuple[Path, int]]
) -> None:
    logging.debug("Exporting textures...")

    for _, (texture_path, _) in texture_layers.items():
        relative_path: Path = texture_path.relative_to(project_path)
        copy_path: Path = temp_path / relative_path
        if not copy_path.parent.exists():
            copy_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy(texture_path, copy_path)
        except Exception as e:
            raise Exception(
                f"Failed copying texture '{texture_path.name}' to '{copy_path.name}' - {str(e)}"
            )

    logging.info(f"{len(texture_layers)} textures exported")


def _zip_package(
    project_path: Path, temp_path: Path, output_path: Optional[Path]
) -> None:
    logging.debug("Zipping package...")

    zip_filename = f"{project_path.name}.zip"
    zip_filepath = temp_path / zip_filename

    with ZipFile(zip_filepath, "w", ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(temp_path):
            if Path(root) == temp_path and zip_filename in files:
                files.remove(zip_filename)

            for file in files:
                file_path = os.path.join(root, file)
                if file_path == str(zip_filepath):
                    continue
                arc = os.path.relpath(os.path.join(root, file), temp_path)
                zip_file.write(file_path, arc)

    if not output_path:
        output_path = project_path / "builds"
    output_path.mkdir(exist_ok=True)

    output_path = output_path / f"{project_path.name}.mnv"
    shutil.move(str(zip_filepath), output_path)

    logging.info(f"Package zipped to {output_path}")


def _read_stream(stream, prefix: str) -> None:
    for line in stream:
        print(f"{prefix}{line}", end="")


def _print_success(message: str) -> None:
    print(f"\033[92mSuccess: {message}\033[0m")


def _print_error(message: str) -> None:
    print(f"\033[91mError: {message}\033[0m")


if __name__ == "__main__":
    main()
